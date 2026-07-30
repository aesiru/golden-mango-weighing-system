<template>
  <UPageSection
    title="Latest News & Announcements"
    description="Stay informed with the latest news, updates, and announcements from the municipal government."
    :ui="{
      root: 'bg-primary-50',
      container: 'relative z-10 flex items-center py-8 sm:py-12 lg:py-16',
      headline: 'text-center mb-8',
    }"
  >
    <template #headline>
      <UBadge size="xl" color="secondary">Updates</UBadge>
    </template>
    <div>
      <UBlogPosts orientation="horizontal" :posts="newsPosts" />
    </div>
    <div class="flex justify-center">
      <UButton
        label="View All News"
        color="secondary"
        variant="solid"
        size="lg"
        trailing-icon="i-lucide-arrow-right"
      />
    </div>
  </UPageSection>
</template>

<script setup lang="ts">
// News posts data
const newsPosts = [
  {
    title: "New Infrastructure Projects Launched",
    description:
      "Mayor announces major infrastructure development projects to improve municipal roads and public facilities for better public service delivery.",
    date: "2 days ago",
    badge: "Municipal Development",
    badgeColor: "primary",
    image: "https://picsum.photos/seed/news1/200/150.jpg",
    alt: "Infrastructure projects announcement",
    to: "#news-1",
  },
  {
    title: "Free Medical Mission Schedule Released",
    description:
      "Municipal Health Office announces schedule for free medical missions in various barangays this month.",
    date: "3 days ago",
    badge: "Health Services",
    badgeColor: "secondary",
    image: "https://picsum.photos/seed/news2/200/150.jpg",
    alt: "Medical mission schedule announcement",
    to: "#news-2",
  },
  {
    title: "Scholarship Program Now Open",
    description:
      "Applications for the 2024 Municipal Scholarship Program are now being accepted for qualified students.",
    date: "1 week ago",
    badge: "Education",
    badgeColor: "success",
    image: "https://picsum.photos/seed/news3/200/150.jpg",
    alt: "Scholarship program announcement",
    to: "#news-3",
  },
];
</script>
