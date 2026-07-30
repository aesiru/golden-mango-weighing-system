<script setup lang="ts">
import { getPaginationRowModel } from "@tanstack/vue-table";
import { h } from "vue";
import { UBadge } from "#components";
import type { TableColumn } from "@nuxt/ui/runtime/components/Table.d.vue.js";

const table = useTemplateRef("table");

definePageMeta({
  title: "Full Disclosure Policy",
  layout: "transparency",
});

const availableYears = ref(["2026", "2025", "2024", "2023"]);
const currentYear = ref("2024");
const searchQuery = ref("");

type DisclosureDocument = {
  id: number;
  title: string;
  category: string;
  datePosted: string;
  fileUrl: string;
  fileSize: string;
  description: string;
};

const data = ref<DisclosureDocument[]>([
  {
    id: 1,
    title: "Annual Budget 2024",
    category: "Budget",
    datePosted: "2024-01-15",
    fileUrl: "#",
    fileSize: "2.5 MB",
    description: "Comprehensive annual budget for fiscal year 2024",
  },
  {
    id: 2,
    title: "Statement of Assets and Liabilities",
    category: "Financial Statements",
    datePosted: "2024-03-20",
    fileUrl: "#",
    fileSize: "1.8 MB",
    description: "Quarterly statement of assets and liabilities as of Q1 2024",
  },
  {
    id: 3,
    title: "Procurement Reports Q1 2024",
    category: "Procurement",
    datePosted: "2024-04-10",
    fileUrl: "#",
    fileSize: "3.2 MB",
    description: "First quarter procurement reports and bid awards",
  },
  {
    id: 4,
    title: "Special Education Fund Report",
    category: "Education",
    datePosted: "2024-02-28",
    fileUrl: "#",
    fileSize: "1.5 MB",
    description: "Special Education Fund utilization report for 2024",
  },
  {
    id: 5,
    title: "Local Revenue Collection Report",
    category: "Revenue",
    datePosted: "2024-03-31",
    fileUrl: "#",
    fileSize: "2.1 MB",
    description: "Monthly local revenue collection report for March 2024",
  },
]);

const filteredData = computed(() => {
  const year = currentYear.value;
  const query = searchQuery.value.toLowerCase();

  return data.value.filter((document) => {
    const matchesYear = document.datePosted.startsWith(year);
    const matchesSearch =
      !query ||
      [document.title, document.category, document.description].some((value) =>
        value.toLowerCase().includes(query),
      );
    return matchesYear && matchesSearch;
  });
});

const getCategoryColor = (category: string) => {
  switch (category) {
    case "Budget":
      return "blue";
    case "Financial Statements":
      return "green";
    case "Procurement":
      return "orange";
    case "Education":
      return "purple";
    case "Revenue":
      return "teal";
    default:
      return "gray";
  }
};

const columns: TableColumn<DisclosureDocument>[] = [
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
    header: "Document",
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
    accessorKey: "datePosted",
    header: "Date Posted",
    cell: ({ row }: { row: any }) => row.getValue("datePosted"),
  },
  {
    accessorKey: "fileSize",
    header: "Size",
    meta: {
      class: {
        th: "text-right",
        td: "text-right font-medium",
      },
    },
    cell: ({ row }: { row: any }) => row.getValue("fileSize"),
  },
];

const pagination = ref({
  pageIndex: 0,
  pageSize: 5,
});
</script>

<template>
  <UPageHeader
    title="Full Disclosure Policy"
    description="View mandated public records and financial disclosure documents for transparency."
    headline="Transparency"
    :ui="{ root: 'pt-0' }"
  >
    <template #links>
      <USelect
        icon="i-lucide-calendar"
        v-model="currentYear"
        :items="availableYears"
        variant="subtle"
        size="md"
      />
      <UInput
        v-model="searchQuery"
        placeholder="Search documents..."
        icon="i-lucide-search"
        size="md"
        class="w-64"
      />
    </template>
  </UPageHeader>

  <div>
    <div class="mb-4 flex items-center gap-2">
      <h2 class="text-xl font-semibold">Disclosure Documents</h2>
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

  <div class="mt-8 space-y-6">
    <UCard>
      <template #header>
        <h2 class="text-xl font-semibold">About Full Disclosure Policy</h2>
      </template>
      <div class="prose dark:prose-invert max-w-none">
        <h3 class="text-lg font-semibold mb-3">
          What is the Full Disclosure Policy?
        </h3>
        <p>
          The Full Disclosure Policy (FDP) is a government transparency
          initiative that mandates local government units to disclose financial
          and operational information to the public. This policy promotes
          accountability and good governance by making government transactions
          and documents accessible to citizens.
        </p>

        <h3 class="text-lg font-semibold mb-3 mt-6">Covered Documents</h3>
        <ul class="list-disc pl-6 space-y-2">
          <li>Annual and Quarterly Budgets</li>
          <li>Statement of Assets and Liabilities</li>
          <li>Procurement Reports and Bid Awards</li>
          <li>Special Education Fund Reports</li>
          <li>Local Revenue Collection Reports</li>
          <li>Trust Fund Utilization Reports</li>
          <li>20% Development Fund Reports</li>
        </ul>

        <h3 class="text-lg font-semibold mb-3 mt-6">How to Access Documents</h3>
        <ul class="list-disc pl-6 space-y-2">
          <li>Browse and download documents from this portal</li>
          <li>Visit the Municipal Hall during office hours</li>
          <li>Request specific documents through formal letter</li>
          <li>Contact the Records and Information Office</li>
        </ul>

        <h3 class="text-lg font-semibold mb-3 mt-6">Contact Information</h3>
        <p>For inquiries about the Full Disclosure Policy:</p>
        <ul class="list-disc pl-6 space-y-2">
          <li>Records and Information Office</li>
          <li>Phone: (032) 123-4567</li>
          <li>Email: records@municipality.gov.ph</li>
          <li>Office Hours: Monday - Friday, 8:00 AM - 5:00 PM</li>
        </ul>
      </div>
    </UCard>
  </div>
</template>
