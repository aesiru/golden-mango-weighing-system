<script setup lang="ts">
const api = useModelEditorApi();
const toast = useToast();
const router = useRouter();

const migrationStatus = ref<{
  current_revision: string | null;
  migrations: any[];
  needs_migration: boolean | null;
} | null>(null);
const loading = ref(true);
const applying = ref(false);
const rolling = ref(false);

const loadStatus = async () => {
  loading.value = true;
  try {
    const response = await api.getMigrationStatus();
    if (response.status === "success") {
      migrationStatus.value = response.data;
    } else {
      toast.add({
        title: "Error",
        description: "Failed to load migration status",
        color: "error",
      });
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to load migration status",
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const applyMigrations = async () => {
  applying.value = true;
  try {
    const response = await api.applyMigrations("head");
    if (response.status === "success") {
      toast.add({
        title: "Success",
        description: "Migrations applied successfully",
        color: "success",
      });
      await loadStatus();
    } else {
      toast.add({
        title: "Error",
        description: response.message || "Failed to apply migrations",
        color: "error",
      });
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to apply migrations",
      color: "error",
    });
  } finally {
    applying.value = false;
  }
};

const rollbackMigration = async () => {
  rolling.value = true;
  try {
    const response = await api.rollbackMigrations(1);
    if (response.status === "success") {
      toast.add({
        title: "Success",
        description: "Migration rolled back",
        color: "success",
      });
      await loadStatus();
    } else {
      toast.add({
        title: "Error",
        description: response.message || "Failed to rollback",
        color: "error",
      });
    }
  } catch (error: any) {
    toast.add({
      title: "Error",
      description: error.message || "Failed to rollback",
      color: "error",
    });
  } finally {
    rolling.value = false;
  }
};

onMounted(() => {
  loadStatus();
});

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-4">
        <UButton
          icon="i-lucide-arrow-left"
          variant="ghost"
          @click="router.push('/model-editor')"
        />
        <div>
          <h2 class="text-xl font-bold text-foreground">Database Migrations</h2>
          <p class="text-muted-foreground text-sm">
            Manage database schema migrations
          </p>
        </div>
      </div>
      <div class="flex gap-2">
        <UButton
          icon="i-lucide-refresh-cw"
          variant="outline"
          @click="loadStatus"
        >
          Refresh
        </UButton>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex justify-center py-12">
      <UIcon
        name="i-lucide-loader-2"
        class="h-8 w-8 animate-spin text-primary"
      />
    </div>

    <!-- Content -->
    <div v-else-if="migrationStatus" class="space-y-6">
      <!-- Status Cards -->
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <UCard>
          <div class="text-center">
            <div class="text-sm text-muted-foreground">Current Revision</div>
            <div class="text-lg font-mono mt-1">
              {{ migrationStatus.current_revision || "None" }}
            </div>
          </div>
        </UCard>

        <UCard>
          <div class="text-center">
            <div class="text-sm text-muted-foreground">Migration Status</div>
            <div class="mt-1">
              <UBadge
                :color="migrationStatus.needs_migration ? 'warning' : 'success'"
                size="lg"
              >
                {{
                  migrationStatus.needs_migration
                    ? "Changes Pending"
                    : "Up to Date"
                }}
              </UBadge>
            </div>
          </div>
        </UCard>

        <UCard>
          <div class="text-center">
            <div class="text-sm text-muted-foreground">Total Migrations</div>
            <div class="text-lg font-semibold mt-1">
              {{ migrationStatus.migrations?.length || 0 }}
            </div>
          </div>
        </UCard>
      </div>

      <!-- Actions -->
      <UCard>
        <template #header>
          <h3 class="font-semibold">Migration Actions</h3>
        </template>

        <div class="flex flex-wrap gap-4">
          <UButton
            icon="i-lucide-play"
            :loading="applying"
            :disabled="!migrationStatus.needs_migration"
            @click="applyMigrations"
          >
            Apply Pending Migrations
          </UButton>

          <UButton
            icon="i-lucide-undo"
            variant="outline"
            color="warning"
            :loading="rolling"
            @click="rollbackMigration"
          >
            Rollback Last Migration
          </UButton>
        </div>

        <div
          v-if="migrationStatus.needs_migration"
          class="mt-4 p-3 bg-yellow-50 dark:bg-yellow-950 rounded border border-yellow-200 dark:border-yellow-800"
        >
          <div
            class="flex items-center gap-2 text-yellow-700 dark:text-yellow-300"
          >
            <UIcon name="i-lucide-alert-triangle" />
            <span class="font-medium">Pending Changes</span>
          </div>
          <p class="text-sm mt-1 text-yellow-600 dark:text-yellow-400">
            There are model changes that need to be migrated to the database.
            Review the changes and apply migrations when ready.
          </p>
        </div>
      </UCard>

      <!-- Migration History -->
      <UCard>
        <template #header>
          <h3 class="font-semibold">Migration History</h3>
        </template>

        <div v-if="migrationStatus.migrations?.length" class="space-y-2">
          <div
            v-for="(migration, index) in migrationStatus.migrations"
            :key="index"
            class="flex items-center justify-between p-3 border rounded"
            :class="{
              'bg-primary/5 border-primary': migration.is_current,
            }"
          >
            <div class="flex items-center gap-3">
              <UIcon
                :name="
                  migration.is_current
                    ? 'i-lucide-check-circle'
                    : migration.is_pending
                      ? 'i-lucide-clock'
                      : 'i-lucide-circle'
                "
                :class="{
                  'text-green-500': migration.is_current,
                  'text-yellow-500': migration.is_pending,
                  'text-gray-400':
                    !migration.is_current && !migration.is_pending,
                }"
              />
              <div>
                <div class="font-mono text-sm">{{ migration.revision }}</div>
                <div class="text-xs text-muted-foreground">
                  {{ migration.message }}
                </div>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <UBadge v-if="migration.is_current" color="success" size="sm">
                Current
              </UBadge>
              <UBadge v-if="migration.is_pending" color="warning" size="sm">
                Pending
              </UBadge>
            </div>
          </div>
        </div>

        <div v-else class="text-center py-8 text-muted-foreground">
          No migration history available
        </div>
      </UCard>
    </div>
  </div>
</template>
