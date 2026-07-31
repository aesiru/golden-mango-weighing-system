import { PrismaClient } from '@prisma/client';
import bcrypt from 'bcryptjs';
import crypto from 'crypto';

const prisma = new PrismaClient();

function shortId(prefix: string): string {
  const hex = crypto.randomBytes(4).toString('hex').toUpperCase();
  return `${prefix}-${hex}`;
}

async function main() {
  console.log('Seeding database...');

  // Admin user
  const adminId = shortId('USR');
  const adminPassword = await bcrypt.hash('admin123', 10);
  await prisma.user.upsert({
    where: { username: 'admin' },
    update: {},
    create: {
      id: adminId,
      username: 'admin',
      email: 'admin@mango.local',
      full_name: 'System Admin',
      hashed_password: adminPassword,
      is_superuser: true,
    },
  });
  console.log('  Admin user created (admin / admin123)');

  // CrateClasses
  const classes = [
    { id: 'CC-SMALL', name: 'Small', min_weight: 150, max_weight: 250 },
    { id: 'CC-MEDIUM', name: 'Medium', min_weight: 250, max_weight: 350 },
    { id: 'CC-LARGE', name: 'Large', min_weight: 350, max_weight: 500 },
    { id: 'CC-JUMBO', name: 'Jumbo', min_weight: 500, max_weight: 800 },
  ];

  for (const cc of classes) {
    await prisma.crateClass.upsert({
      where: { id: cc.id },
      update: { name: cc.name, min_weight: cc.min_weight, max_weight: cc.max_weight },
      create: cc,
    });
  }
  console.log('  4 CrateClasses seeded');

  // Company
  const companyId = shortId('COMP');
  await prisma.company.upsert({
    where: { email: 'info@mangoexport.co' },
    update: {},
    create: {
      id: companyId,
      name: 'Mango Export Co.',
      contact_person: 'Juan Dela Cruz',
      email: 'info@mangoexport.co',
      phone: '+639123456789',
      address: '123 Mango St., Guimaras, Philippines',
      registration_date: new Date(),
      status: 'approved',
    },
  });
  console.log('  Mango Export Co. created');

  // Sample Order (Medium, 1000 mangoes)
  const existingOrder = await prisma.order.findFirst({
    where: { company_id: companyId, crate_class_id: 'CC-MEDIUM' },
  });
  if (!existingOrder) {
    await prisma.order.create({
      data: {
        id: shortId('ORD'),
        company_id: companyId,
        crate_class_id: 'CC-MEDIUM',
        total_amount: 1000,
        current_amount: 0,
        status: 'pending',
      },
    });
    console.log('  Sample Order created (1000 Medium mangoes)');
  }

  console.log('Seed complete.');
}

main()
  .catch((e) => {
    console.error('Seed failed:', e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
