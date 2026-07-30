<template>
  <div class="space-y-0">
    <!-- Hero Section -->
    <UPageHero
      headline=""
      description="Serving the community with excellence, transparency, and dedication to public service."
      :ui="{
        root: 'relative ',
        container: 'relative z-10 flex items-center py-8 sm:py-12 lg:py-16',
        title: 'text-foreground dark:text-gray-100 font-domine',
        headline: 'text-foreground dark:text-gray-100',
        description: 'text-muted-foreground dark:text-gray-400',
        links: 'relative z-20',
      }"
      :links="[
        {
          label: 'Online Services',
          color: 'primary',
          variant: 'solid',
          size: 'xl',
          icon: 'i-lucide-settings',
        },
        {
          label: 'Contact Us',
          color: 'secondary',
          variant: 'solid',
          size: 'xl',
          icon: 'i-lucide-phone',
        },
      ]"
    >
      <template #title>
        <div class="mt-8">
          <span
            class="font-bold tracking-tight leading-tight text-gray-900 dark:text-white sm:text-[3rem] lg:text-[4rem] font-domine"
          >
            Municipality
          </span>
        </div>
      </template>
      <!-- Image Carousel Section -->
      <div class="w-full">
        <div class="container mx-auto mb-8">
          <UCarousel
            v-slot="{ item }"
            arrows
            dots
            :items="carouselImages"
            class="w-full mx-auto"
          >
            <img
              :src="item"
              width="1800"
              height="500"
              class="rounded-lg w-full"
              loading="lazy"
            />
          </UCarousel>
        </div>
      </div>
    </UPageHero>
  </div>
</template>

<script setup lang="ts">
// Carousel images data
const carouselImages = [
  "https://picsum.photos/1200/500?random=1",
  "https://picsum.photos/1200/500?random=2",
  "https://picsum.photos/1200/500?random=3",
  "https://picsum.photos/1200/500?random=4",
  "https://picsum.photos/1200/500?random=5",
  "https://picsum.photos/1200/500?random=6",
];

// SEO Meta
useSeoMeta({
  title: "Municipality - Official Website",
  description:
    "Official website of the Municipality. Providing quality public service, transparency, and governance for all citizens.",
  ogTitle: "Municipality - Official Website",
  ogDescription:
    "Official website of the Municipality. Providing quality public service, transparency, and governance for all citizens.",
  ogImage: "/og-image.jpg",
  twitterCard: "summary_large_image",
});
</script>
