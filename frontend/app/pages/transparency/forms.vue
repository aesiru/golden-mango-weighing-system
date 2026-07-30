<script setup lang="ts">
import { getPaginationRowModel } from "@tanstack/vue-table";
import { h } from "vue";
import { UBadge } from "#components";
import type { TableColumn } from "@nuxt/ui/runtime/components/Table.d.vue.js";

const table = useTemplateRef("table");

definePageMeta({
  title: "Downloadable Forms",
  layout: "transparency",
});

const availableCategories = ref([
  "All",
  "Business",
  "Clearance",
  "Tax",
  "Social Services",
  "Construction",
  "Civil Registry",
  "Health",
  "Education",
]);
const currentCategory = ref("All");
const searchQuery = ref("");

type Form = {
  id: number;
  title: string;
  category: string;
  description: string;
  fileUrl: string;
  fileSize: string;
  format: string;
  downloads: number;
};

const data = ref<Form[]>([
  {
    id: 1,
    title: "Business Permit Application Form",
    category: "Business",
    description: "Application form for new and renewal of business permits",
    fileUrl: "#",
    fileSize: "245 KB",
    format: "PDF",
    downloads: 1250,
  },
  {
    id: 2,
    title: "Barangay Clearance Request Form",
    category: "Clearance",
    description: "Request form for barangay clearance certificates",
    fileUrl: "#",
    fileSize: "180 KB",
    format: "PDF",
    downloads: 890,
  },
  {
    id: 3,
    title: "Real Property Tax Declaration Form",
    category: "Tax",
    description: "Declaration form for real property tax assessment",
    fileUrl: "#",
    fileSize: "320 KB",
    format: "PDF",
    downloads: 650,
  },
  {
    id: 4,
    title: "Senior Citizen ID Application",
    category: "Social Services",
    description: "Application form for senior citizen identification card",
    fileUrl: "#",
    fileSize: "150 KB",
    format: "PDF",
    downloads: 420,
  },
  {
    id: 5,
    title: "Building Permit Application",
    category: "Construction",
    description: "Application form for building and construction permits",
    fileUrl: "#",
    fileSize: "410 KB",
    format: "PDF",
    downloads: 310,
  },
  {
    id: 6,
    title: "Marriage License Application Form",
    category: "Civil Registry",
    description: "Application form for marriage license issuance",
    fileUrl: "#",
    fileSize: "220 KB",
    format: "PDF",
    downloads: 280,
  },
  {
    id: 7,
    title: "Health Certificate Request Form",
    category: "Health",
    description: "Request form for various health certificates",
    fileUrl: "#",
    fileSize: "190 KB",
    format: "PDF",
    downloads: 195,
  },
  {
    id: 8,
    title: "Scholarship Application Form",
    category: "Education",
    description: "Application form for municipal scholarship programs",
    fileUrl: "#",
    fileSize: "280 KB",
    format: "PDF",
    downloads: 175,
  },
]);

const filteredData = computed(() => {
  return data.value.filter((form) => {
    const matchesCategory =
      currentCategory.value === "All" ||
      form.category === currentCategory.value;
    const query = searchQuery.value.toLowerCase();
    const matchesSearch =
      !query ||
      [form.title, form.category, form.format, form.description].some((value) =>
        value.toLowerCase().includes(query),
      );

    return matchesCategory && matchesSearch;
  });
});

const getCategoryColor = (category: string) => {
  switch (category) {
    case "Business":
      return "blue";
    case "Clearance":
      return "green";
    case "Tax":
      return "orange";
    case "Social Services":
      return "purple";
    case "Construction":
      return "red";
    case "Civil Registry":
      return "teal";
    case "Health":
      return "emerald";
    case "Education":
      return "indigo";
    default:
      return "gray";
  }
};

const getFormatIcon = (format: string) => {
  switch (format) {
    case "PDF":
      return "i-lucide-file-text";
    case "DOC":
      return "i-lucide-file";
    case "XLS":
      return "i-lucide-sheet";
    default:
      return "i-lucide-file";
  }
};

const columns: TableColumn<Form>[] = [
  {
    accessorKey: "id",
    header: "#",
    cell: ({ row }: { row: any }) => `#${row.getValue("id")}`,
    meta: {
      class: {
        th: "w-16",
      },
    },
  },
  {
    accessorKey: "title",
    header: "Form Title",
    cell: ({ row }: { row: any }) => row.getValue("title"),
  },
  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }: { row: any }) =>
      h(
        UBadge,
        {
          color: getCategoryColor(row.getValue("category")),
          variant: "subtle",
        },
        () => row.getValue("category"),
      ),
  },
  {
    accessorKey: "format",
    header: "Format",
    cell: ({ row }: { row: any }) => {
      return h("div", { class: "flex items-center gap-2" }, [
        h("i", { class: `icon ${getFormatIcon(row.getValue("format"))}` }),
        row.getValue("format"),
      ]);
    },
  },
  {
    accessorKey: "fileSize",
    header: "Size",
    cell: ({ row }: { row: any }) => row.getValue("fileSize"),
  },
  {
    accessorKey: "downloads",
    header: "Downloads",
    meta: {
      class: {
        th: "text-right",
        td: "text-right font-medium",
      },
    },
    cell: ({ row }: { row: any }) => row.getValue("downloads"),
  },
];

const pagination = ref({
  pageIndex: 0,
  pageSize: 5,
});
</script>

<template>
  <UPageHeader
    title="Downloadable Forms"
    description="Download municipal forms and documents for different services and applications."
    headline="Transparency"
    :ui="{ root: 'pt-0' }"
  >
    <template #links>
      <USelect
        icon="i-lucide-list"
        v-model="currentCategory"
        :items="availableCategories"
        variant="subtle"
        size="md"
      />
      <UInput
        v-model="searchQuery"
        placeholder="Search forms..."
        icon="i-lucide-search"
        size="md"
        class="w-64"
      />
    </template>
  </UPageHeader>

  <div>
    <div class="mb-4 flex items-center gap-2">
      <h2 class="text-xl font-semibold">Available Forms</h2>
      <UBadge color="primary" size="sm">{{ filteredData.length }}</UBadge>
    </div>

    <UTable
      ref="table"
      v-model:pagination="pagination"
      :columns="columns"
      :data="filteredData"
      class="flex-1"
      :pagination-options="{
        getPaginationRowModel: getPaginationRowModel(),
      }"
      :ui="{ root: 'border rounded-lg border-accented' }"
    />

    <div class="flex justify-end pt-4">
      <UPagination
        :page="(pagination.pageIndex || 0) + 1"
        :items-per-page="pagination.pageSize"
        :total="filteredData.length"
        @update:page="(p) => (pagination.pageIndex = p - 1)"
      />
    </div>
  </div>
</template>
