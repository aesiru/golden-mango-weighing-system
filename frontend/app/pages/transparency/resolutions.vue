<script setup lang="ts">
import { getPaginationRowModel } from "@tanstack/vue-table";
import { h } from "vue";
import { UBadge } from "#components";
import type { TableColumn } from "@nuxt/ui/runtime/components/Table.d.vue.js";

const table = useTemplateRef("table");

definePageMeta({
  title: "Resolutions",
  layout: "transparency",
});

const availableYears = ref(["2026", "2025", "2024", "2023"]);
const currentYear = ref("2024");
const searchQuery = ref("");

type Resolution = {
  id: number;
  title: string;
  category: string;
  dateAdopted: string;
  status: string;
  description: string;
  fileUrl: string;
  fileSize: string;
};

const data = ref<Resolution[]>([
  {
    id: 1,
    title: "Resolution No. 2024-015: Approval of 2024 Annual Budget",
    category: "Budget",
    dateAdopted: "2024-01-10",
    status: "Adopted",
    description: "Resolution adopting the annual budget for fiscal year 2024",
    fileUrl: "#",
    fileSize: "2.1 MB",
  },
  {
    id: 2,
    title: "Resolution No. 2024-014: Declaration of Local Holiday",
    category: "Special Events",
    dateAdopted: "2024-01-05",
    status: "Adopted",
    description:
      "Resolution declaring the municipality's founding anniversary as a local holiday",
    fileUrl: "#",
    fileSize: "0.8 MB",
  },
  {
    id: 3,
    title: "Resolution No. 2023-098: Support for Senior Citizens Program",
    category: "Social Welfare",
    dateAdopted: "2023-12-20",
    status: "Adopted",
    description:
      "Resolution expressing support for the enhanced senior citizens program",
    fileUrl: "#",
    fileSize: "1.5 MB",
  },
  {
    id: 4,
    title: "Resolution No. 2023-097: Environmental Protection Initiative",
    category: "Environment",
    dateAdopted: "2023-12-15",
    status: "Adopted",
    description:
      "Resolution supporting the municipal environmental protection and conservation program",
    fileUrl: "#",
    fileSize: "1.9 MB",
  },
  {
    id: 5,
    title: "Resolution No. 2023-096: Infrastructure Development Plan",
    category: "Infrastructure",
    dateAdopted: "2023-12-10",
    status: "Adopted",
    description:
      "Resolution adopting the 5-year infrastructure development plan for the municipality",
    fileUrl: "#",
    fileSize: "3.2 MB",
  },
]);

const filteredData = computed(() => {
  const year = currentYear.value;
  const query = searchQuery.value.toLowerCase();

  return data.value.filter((resolution) => {
    const matchesYear = resolution.dateAdopted.startsWith(year);
    const matchesSearch =
      !query ||
      [
        resolution.title,
        resolution.category,
        resolution.status,
        resolution.description,
      ].some((value) => value.toLowerCase().includes(query));

    return matchesYear && matchesSearch;
  });
});

const getCategoryColor = (category: string) => {
  switch (category) {
    case "Budget":
      return "blue";
    case "Special Events":
      return "purple";
    case "Social Welfare":
      return "green";
    case "Environment":
      return "emerald";
    case "Infrastructure":
      return "orange";
    default:
      return "gray";
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "Adopted":
      return "green";
    case "Pending":
      return "yellow";
    case "Withdrawn":
      return "red";
    default:
      return "gray";
  }
};

const columns: TableColumn<Resolution>[] = [
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
    header: "Resolution",
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
    accessorKey: "dateAdopted",
    header: "Adopted",
    cell: ({ row }: { row: any }) => row.getValue("dateAdopted"),
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }: { row: any }) =>
      h(
        UBadge,
        { color: getStatusColor(row.getValue("status")), variant: "outline" },
        () => row.getValue("status"),
      ),
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
    title="Resolutions"
    description="Browse municipal resolutions adopted by the Sangguniang Bayan."
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
        placeholder="Search resolutions..."
        icon="i-lucide-search"
        size="md"
        class="w-64"
      />
    </template>
  </UPageHeader>

  <div>
    <div class="mb-4 flex items-center gap-2">
      <h2 class="text-xl font-semibold">Resolution Registry</h2>
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
        <h2 class="text-xl font-semibold">About Municipal Resolutions</h2>
      </template>
      <div class="prose dark:prose-invert max-w-none">
        <h3 class="text-lg font-semibold mb-3">
          What is a Municipal Resolution?
        </h3>
        <p>
          A municipal resolution is an official expression of the opinion, will,
          or intent of the Sangguniang Bayan (Municipal Council). Unlike
          ordinances, resolutions are typically temporary or administrative in
          nature and do not have the same permanent legal effect.
        </p>

        <h3 class="text-lg font-semibold mb-3 mt-6">Types of Resolutions</h3>
        <ul class="list-disc pl-6 space-y-2">
          <li>
            <strong>Administrative Resolutions:</strong> Internal matters and
            administrative policies
          </li>
          <li>
            <strong>Budget Resolutions:</strong> Adoption of annual and
            supplemental budgets
          </li>
          <li>
            <strong>Ceremonial Resolutions:</strong> Commendations,
            recognitions, and declarations
          </li>
          <li>
            <strong>Policy Resolutions:</strong> Expression of support for
            various programs and initiatives
          </li>
          <li>
            <strong>Emergency Resolutions:</strong> Actions taken during
            emergencies or special situations
          </li>
        </ul>

        <h3 class="text-lg font-semibold mb-3 mt-6">Resolution Process</h3>
        <ol class="list-decimal pl-6 space-y-2">
          <li>Filing of proposed resolution</li>
          <li>Committee review and recommendation</li>
          <li>First reading and deliberation</li>
          <li>Second reading and voting</li>
          <li>Adoption and documentation</li>
          <li>Implementation and monitoring</li>
        </ol>

        <h3 class="text-lg font-semibold mb-3 mt-6">Recent Resolutions</h3>
        <p>
          Recent resolutions adopted by the Sangguniang Bayan focus on key areas
          including:
        </p>
        <ul class="list-disc pl-6 space-y-2">
          <li>Budget appropriations and financial management</li>
          <li>Support for social welfare programs</li>
          <li>Environmental protection initiatives</li>
          <li>Infrastructure development projects</li>
          <li>Special events and local celebrations</li>
        </ul>

        <h3 class="text-lg font-semibold mb-3 mt-6">Contact Information</h3>
        <p>For inquiries about municipal resolutions:</p>
        <ul class="list-disc pl-6 space-y-2">
          <li>Sangguniang Bayan Secretariat Office</li>
          <li>Phone: (032) 123-4567</li>
          <li>Email: sb@municipality.gov.ph</li>
          <li>Office Hours: Monday - Friday, 8:00 AM - 5:00 PM</li>
        </ul>
      </div>
    </UCard>
  </div>
</template>
