<template>
  <footer class="bg-gray-900 text-gray-50 dark:bg-gray-950 py-12">
    <div class="container mx-auto px-4">
      <div class="grid lg:grid-cols-4 gap-8">
        <div>
          <h3
            class="font-semibold text-lg mb-4 text-gray-50 dark:text-gray-100"
          >
            Municipal Government
          </h3>
          <ul class="space-y-2 text-gray-400 dark:text-gray-500">
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >About the Municipality</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Municipal Officials</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Organizational Chart</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Municipal Ordinances</NuxtLink
              >
            </li>
          </ul>
        </div>

        <div>
          <h3
            class="font-semibold text-lg mb-4 text-gray-50 dark:text-gray-100"
          >
            Services
          </h3>
          <ul class="space-y-2 text-gray-400 dark:text-gray-500">
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Business Permit</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Real Property Tax</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Civil Registry</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Health Services</NuxtLink
              >
            </li>
          </ul>
        </div>

        <div>
          <h3
            class="font-semibold text-lg mb-4 text-gray-50 dark:text-gray-100"
          >
            Transparency
          </h3>
          <ul class="space-y-2 text-gray-400 dark:text-gray-500">
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Full Disclosure Policy</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Bids and Awards</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Annual Budget</NuxtLink
              >
            </li>
            <li>
              <NuxtLink
                to="#"
                class="hover:text-gray-50 dark:hover:text-gray-100 transition-colors"
                >Citizen's Charter</NuxtLink
              >
            </li>
          </ul>
        </div>

        <div>
          <h3
            class="font-semibold text-lg mb-4 text-gray-50 dark:text-gray-100"
          >
            Connect With Us
          </h3>
          <div class="flex space-x-4 mb-4">
            <UButton
              color="neutral"
              variant="ghost"
              size="sm"
              icon="i-simple-icons-facebook"
            />
            <UButton
              color="neutral"
              variant="ghost"
              size="sm"
              icon="i-simple-icons-twitter"
            />
            <UButton
              color="neutral"
              variant="ghost"
              size="sm"
              icon="i-simple-icons-instagram"
            />
            <UButton
              color="neutral"
              variant="ghost"
              size="sm"
              icon="i-simple-icons-youtube"
            />
          </div>
          <p class="text-gray-400 dark:text-gray-500 text-sm">
            Follow us on social media for real-time updates.
          </p>
        </div>
      </div>

      <USeparator class="my-8 border-gray-800 dark:border-gray-700" />

      <div class="text-center text-gray-400 dark:text-gray-500">
        <p>
          &copy; 2024 Municipality. All rights reserved.
        </p>
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
// Component setup can be added here if needed
</script>
