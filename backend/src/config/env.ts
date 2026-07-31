import dotenv from 'dotenv';
dotenv.config();

export const env = {
  DATABASE_URL: process.env.DATABASE_URL || 'file:./dev.db',
  JWT_SECRET: process.env.JWT_SECRET || 'change-me-in-production',
  JWT_EXPIRES_IN: process.env.JWT_EXPIRES_IN || '12h',
  PORT: parseInt(process.env.PORT || '3000', 10),
  MQTT_URL: process.env.MQTT_URL || 'mqtt://localhost:1883',
  MQTT_TOPIC: process.env.MQTT_TOPIC || '+/value',
};
