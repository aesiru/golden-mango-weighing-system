/**
 * Patch NuGrid LookupEditor.vue to fix missing watchEffect import.
 * NuGrid v0.3.1 uses watchEffect without importing it from Vue.
 * Run via: node scripts/patch-nugrid.js (or as postinstall hook)
 */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const filePath = path.join(
  __dirname,
  '..',
  'node_modules',
  '@nu-grid',
  'nuxt',
  'dist',
  'runtime',
  'cell-types',
  'lookup',
  'LookupEditor.vue'
);

if (!fs.existsSync(filePath)) {
  console.log('[patch-nugrid] LookupEditor.vue not found, skipping patch.');
  process.exit(0);
}

let content = fs.readFileSync(filePath, 'utf-8');

if (content.includes('watchEffect')) {
  if (content.includes("import { computed, isRef, nextTick, onMounted, onUnmounted, ref, watch, watchEffect }")) {
    console.log('[patch-nugrid] Already patched.');
    process.exit(0);
  }
}

const original = 'import { computed, isRef, nextTick, onMounted, onUnmounted, ref, watch } from "vue";';
const patched = 'import { computed, isRef, nextTick, onMounted, onUnmounted, ref, watch, watchEffect } from "vue";';

if (content.includes(original)) {
  content = content.replace(original, patched);
  fs.writeFileSync(filePath, content, 'utf-8');
  console.log('[patch-nugrid] Patched LookupEditor.vue: added watchEffect import.');
} else {
  console.log('[patch-nugrid] Import line not found (may already be patched or changed).');
}
