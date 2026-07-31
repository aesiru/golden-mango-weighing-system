import mqtt from 'mqtt';
import { env } from '../config/env';
import { shortId } from '../lib/ids';
import prisma from '../lib/prisma';

export class MqttService {
  private client: mqtt.MqttClient | null = null;
  private queue: Promise<void> = Promise.resolve();

  start() {
    this.client = mqtt.connect(env.MQTT_URL);

    this.client.on('connect', () => {
      console.log(`MQTT connected to ${env.MQTT_URL}`);
      this.client!.subscribe(env.MQTT_TOPIC, (err) => {
        if (err) {
          console.error('MQTT subscribe error:', err);
        } else {
          console.log(`MQTT subscribed to ${env.MQTT_TOPIC}`);
        }
      });
    });

    this.client.on('message', (_topic, payload) => {
      const deviceId = _topic.split('/')[0];
      this.enqueue(deviceId, payload.toString());
    });

    this.client.on('error', (err) => {
      console.error('MQTT error:', err);
    });

    this.client.on('offline', () => {
      console.log('MQTT offline — reconnecting...');
    });

    this.client.on('reconnect', () => {
      console.log('MQTT reconnecting...');
    });
  }

  private enqueue(deviceId: string, payload: string) {
    this.queue = this.queue
      .then(() => this.handleWeight(deviceId, payload))
      .catch((err) => {
        console.error('MQTT pipeline error:', err);
      });
  }

  private async handleWeight(deviceId: string, payload: string) {
    const weightGrams = Number(payload);
    if (isNaN(weightGrams)) {
      this.publish(deviceId, `Error: invalid weight '${payload}'`);
      return;
    }

    // Match crate class — narrowest range wins
    const allClasses = await prisma.crateClass.findMany({
      where: {
        min_weight: { lte: weightGrams },
        max_weight: { gte: weightGrams },
      },
    });

    if (allClasses.length === 0) {
      this.publish(deviceId, `Unknown: no class for ${weightGrams}g`);
      return;
    }

    allClasses.sort((a, b) => (a.max_weight - a.min_weight) - (b.max_weight - b.min_weight));
    const matchedClass = allClasses[0];
    const valid =
      weightGrams >= matchedClass.min_weight &&
      weightGrams <= matchedClass.max_weight;

    try {
      await prisma.$transaction(async (tx) => {
        // Find or create device — id from topic, auto-generated name
        let device = await tx.device.findUnique({ where: { id: deviceId } });
        if (!device) {
          const count = await tx.device.count();
          device = await tx.device.create({
            data: { id: deviceId, name: `device_${count}` },
          });
        }

        // Find or create order (oldest pending/in-progress for this class)
        let order = await tx.order.findFirst({
          where: {
            crate_class_id: matchedClass.id,
            status: { in: ['pending', 'in-progress'] },
          },
          orderBy: { created_at: 'asc' },
        });

        if (!order) {
          order = await tx.order.create({
            data: {
              id: shortId('ORD'),
              crate_class_id: matchedClass.id,
              total_amount: 0,
              current_amount: 0,
              status: 'in-progress',
            },
          });
        } else if (order.status === 'pending') {
          order = await tx.order.update({
            where: { id: order.id },
            data: { status: 'in-progress' },
          });
        }

        // Find or create crate (first with spare capacity)
        const existingCrates = await tx.crate.findMany({
          where: { order_id: order.id },
          orderBy: { created_at: 'asc' },
        });
        let crate = existingCrates.find((c) => c.counted < c.target) || null;

        if (!crate) {
          const crateId = shortId('CRT');
          crate = await tx.crate.create({
            data: {
              id: crateId,
              code: crateId,
              order_id: order.id,
              crate_class_id: matchedClass.id,
              target: 50,
              counted: 0,
            },
          });
        }

        // Create reading
        await tx.reading.create({
          data: {
            id: shortId('RDG'),
            crate_id: crate.id,
            order_id: order.id,
            device_id: device.id,
            weight_grams: weightGrams,
            recorded_at: new Date(),
            valid,
          },
        });

        // Update counts
        await tx.crate.update({
          where: { id: crate.id },
          data: { counted: { increment: 1 } },
        });
        await tx.order.update({
          where: { id: order.id },
          data: { current_amount: { increment: weightGrams } },
        });

        // Respond
        const response = `${matchedClass.name}: ${order.id}/${crate.id}`;
        this.publish(deviceId, response);
      });
    } catch (err) {
      console.error('Transaction failed:', err);
    }
  }

  private publish(deviceId: string, message: string) {
    if (!this.client) return;
    const topic = `${deviceId}/display`;
    this.client.publish(topic, message, { qos: 1 }, (err) => {
      if (err) console.error('MQTT publish error:', err);
    });
  }

  async stop() {
    return new Promise<void>((resolve) => {
      if (this.client) {
        this.client.end(false, () => resolve());
      } else {
        resolve();
      }
    });
  }
}

export const mqttService = new MqttService();
