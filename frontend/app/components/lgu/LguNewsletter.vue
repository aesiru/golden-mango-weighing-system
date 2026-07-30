<template>
  <section class="py-16 bg-muted/50 dark:bg-gray-900/50">
    <div class="container mx-auto px-4">
      <UCard class="max-w-2xl mx-auto">
        <div class="text-center p-8">
          <Icon
            name="i-lucide-mail"
            class="w-12 h-12 text-primary-600 dark:text-primary-400 mx-auto mb-4"
          />
          <h2
            class="text-2xl font-bold mb-4 text-foreground dark:text-gray-100"
          >
            Stay Updated
          </h2>
          <p class="text-muted-foreground dark:text-gray-400 mb-6">
            Subscribe to our newsletter for latest news, announcements, and
            municipal updates.
          </p>
          <div class="flex flex-col sm:flex-row gap-4">
            <UInput
              v-model="email"
              placeholder="Enter your email address"
              size="lg"
              class="flex-1"
              icon="i-lucide-mail"
            />
            <UButton
              size="lg"
              color="primary"
              :loading="subscribing"
              @click="subscribe"
            >
              Subscribe
            </UButton>
          </div>
        </div>
      </UCard>
    </div>
  </section>
</template>

<script setup lang="ts">
// Reactive data
const email = ref("");
const subscribing = ref(false);

// Methods
const subscribe = async () => {
  if (!email.value) {
    return;
  }

  subscribing.value = true;

  // Simulate API call
  await new Promise((resolve) => setTimeout(resolve, 2000));

  subscribing.value = false;
  email.value = "";

  // Show success notification
  useToast().add({
    title: "Successfully subscribed!",
    description: "Thank you for subscribing to our newsletter.",
    color: "success",
  });
};
</script>
