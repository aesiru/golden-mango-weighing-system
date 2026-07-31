import { env } from './config/env';
import app from './app';
import prisma from './lib/prisma';
import { mqttService } from './services/mqtt.service';

async function main() {
  const server = app.listen(env.PORT, () => {
    console.log(`Server running on http://localhost:${env.PORT}`);
  });

  mqttService.start();

  const shutdown = async () => {
    console.log('\nShutting down...');
    await mqttService.stop();
    server.close();
    await prisma.$disconnect();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);
}

main().catch((err) => {
  console.error('Failed to start server:', err);
  process.exit(1);
});
