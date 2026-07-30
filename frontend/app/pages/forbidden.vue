<script setup lang="ts">
definePageMeta({
  layout: "default",
});

const router = useRouter();
const forbiddenMessage = ref("");

onMounted(() => {
  const msg = sessionStorage.getItem("forbidden_message");
  if (msg) {
    forbiddenMessage.value = msg;
    sessionStorage.removeItem("forbidden_message");
  }
});

const goBack = () => {
  if (window.history.length > 1) {
    router.back();
  } else {
    router.push("/");
  }
};
</script>

<template>
  <div
    class="flex flex-col items-center justify-center min-h-[70vh] gap-6 px-6"
  >
    <div
      class="flex items-center justify-center w-20 h-20 rounded-full bg-red-50 dark:bg-red-950"
    >
      <UIcon name="i-lucide-shield-x" class="h-10 w-10 text-red-500" />
    </div>
    <div class="text-center space-y-2">
      <h1 class="text-3xl font-bold">Access Denied</h1>
      <p class="text-muted text-lg max-w-md">
        {{
          forbiddenMessage || "You don't have permission to access this page."
        }}
        Contact your administrator if you believe this is an error.
      </p>
    </div>
    <div class="flex gap-3">
      <UButton variant="outline" icon="i-lucide-arrow-left" @click="goBack">
        Go Back
      </UButton>
      <UButton icon="i-lucide-home" @click="router.push('/')">
        Go Home
      </UButton>
    </div>
  </div>
</template>
