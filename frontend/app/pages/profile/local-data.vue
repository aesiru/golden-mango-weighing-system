<script setup lang="ts">
const toast = useToast();
const clearing = ref(false);

const clearAllCache = async () => {
  clearing.value = true;
  try {
    const keys = Object.keys(localStorage);
    let clearedCount = 0;

    keys.forEach((key) => {
      localStorage.removeItem(key);
      clearedCount++;
    });

    sessionStorage.clear();

    toast.add({
      title: "Cache Cleared",
      description: `Cleared ${clearedCount} items from localStorage and all sessionStorage`,
      color: "success",
    });

    setTimeout(() => {
      window.location.reload();
    }, 1000);
  } catch (error) {
    console.error("Failed to clear cache:", error);
    toast.add({
      title: "Error",
      description: "Failed to clear cache",
      color: "error",
    });
  } finally {
    clearing.value = false;
  }
};

const clearMetadataCache = () => {
  const keys = Object.keys(localStorage).filter(
    (k) =>
      k.startsWith("meta:") ||
      k.startsWith("entity:") ||
      k.startsWith("model-editor:") ||
      k.startsWith("eam_"),
  );

  keys.forEach((key) => localStorage.removeItem(key));

  toast.add({
    title: "Metadata Cache Cleared",
    description: `Cleared ${keys.length} metadata items`,
    color: "success",
  });

  setTimeout(() => {
    window.location.reload();
  }, 1000);
};

definePageMeta({ title: "Profile local data" });
</script>

<template>
  <div class="space-y-6">
    <UPageCard
      title="Local Data"
      description="Clear local caches and review how settings behave in this browser."
      variant="naked"
      class="mb-4"
    />

    <UCard variant="subtle">
      <div class="space-y-4">
        <div class="flex gap-4">
          <UButton
            color="primary"
            variant="outline"
            block
            :loading="clearing"
            @click="clearMetadataCache"
          >
            Clear Metadata Cache
          </UButton>

          <UButton
            color="error"
            variant="outline"
            block
            :loading="clearing"
            @click="clearAllCache"
          >
            Clear All Cache
          </UButton>
        </div>

        <UAlert
          color="neutral"
          title="Heads up!"
          description="Metadata Cache clears entity metadata, model
            editor data, and entity options.
            All Cache clears everything including session details."
          icon="i-lucide-terminal"
        />
      </div>
    </UCard>
  </div>
</template>
