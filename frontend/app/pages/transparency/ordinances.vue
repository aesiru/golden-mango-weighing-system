<script setup lang="ts">
import { getPaginationRowModel } from "@tanstack/vue-table";
import { UBadge } from "#components";
import type { TableColumn } from "@nuxt/ui/runtime/components/Table.d.vue.js";

const table = useTemplateRef("table");

definePageMeta({
  title: "Ordinances",
});

type Ordinance = {
  id: number;
  title: string;
  category: string;
  status: string;
  description: string;
  fileUrl: string;
  fileSize: string;
  downloadCount: number;
};

// Sample data for ordinances
const ordinances: Ordinance[] = [
  {
    id: 1,
    title: "MO No. 2024-001: Anti-Smoking Regulation",
    category: "Health",
    status: "Effective",
    description:
      "An ordinance regulating smoking in public places within the municipality",
    fileUrl: "#",
    fileSize: "1.2 MB",
    downloadCount: 150,
  },
  {
    id: 2,
    title: "MO No. 2023-045: Waste Management Program",
    category: "Environment",
    status: "Effective",
    description:
      "Comprehensive waste management and segregation program for all barangays",
    fileUrl: "#",
    fileSize: "2.8 MB",
    downloadCount: 200,
  },
  {
    id: 3,
    title: "MO No. 2023-044: Traffic Management Code",
    category: "Transportation",
    status: "Effective",
    description:
      "Updated traffic rules and regulations for municipal roads and highways",
    fileUrl: "#",
    fileSize: "3.5 MB",
    downloadCount: 180,
  },
  {
    id: 4,
    title: "MO No. 2023-043: Business Permit Simplification",
    category: "Business",

    status: "Effective",
    description:
      "Streamlined process for business permit application and renewal",
    fileUrl: "#",
    fileSize: "1.8 MB",
    downloadCount: 120,
  },
  {
    id: 5,
    title: "MO No. 2023-042: Senior Citizen Benefits",
    category: "Social Welfare",
    status: "Effective",
    description:
      "Enhanced benefits and privileges for senior citizens",
    fileUrl: "#",
    fileSize: "2.1 MB",
    downloadCount: 95,
  },
];

const getCategoryColor = (category: string) => {
  switch (category) {
    case "Health":
      return "primary";
    case "Environment":
      return "success";
    case "Transportation":
      return "info";
    case "Business":
      return "warning";
    case "Social Welfare":
      return "neutral";
    default:
      return "neutral";
  }
};

const getStatusColor = (status: string) => {
  switch (status) {
    case "Effective":
      return "primary";
    case "Pending":
      return "warning";
    case "Suspended":
      return "destructive";
    default:
      return "neutral";
  }
};

const searchQuery = ref("");
const currentYear = ref(new Date().getFullYear());
const availableYears = ref([2023, 2024, 2025]);

const columns: TableColumn<Ordinance>[] = [
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ row }: { row: any }) => {
      return row.getValue("title");
    },
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }: { row: any }) => {
      return h(UBadge, { color: getStatusColor(row.getValue("status")) }, () =>
        row.getValue("status"),
      );
    },
  },

  {
    accessorKey: "category",
    header: "Category",
    cell: ({ row }: { row: any }) => {
      return h(
        UBadge,
        { color: getCategoryColor(row.getValue("category")) },
        () => row.getValue("category"),
      );
    },
  },
  {
    accessorKey: "fileSize",
    header: "File Size",
    meta: {
      class: {
        th: "text-right",
        td: "text-right font-medium",
      },
    },
    cell: ({ row }: { row: any }) => {
      return row.getValue("fileSize");
    },
  },
  {
    accessorKey: "downloadCount",
    header: "Downloads",
    meta: {
      class: {
        th: "text-right",
        td: "text-right font-medium",
      },
    },
    cell: ({ row }: { row: any }) => {
      return row.getValue("downloadCount");
    },
  },
];

const pagination = ref({
  pageIndex: 0,
  pageSize: 5,
});
</script>

<template>
  <UPageHeader
    title="Municipal Ordinances"
    description="View all municipal ordinances and local laws enacted by the Sangguniang Bayan"
    headline="Transparency"
    :ui="{ root: 'pt-0' }"
  >
    <template #links>
      <!-- SHOULD BE FILTERS LIKE YEAR -->
      <USelect
        icon="i-lucide-calendar"
        v-model="currentYear"
        :items="availableYears"
        variant="subtle"
        size="md"
      />
      <UInput
        v-model="searchQuery"
        placeholder="Search bids..."
        icon="i-lucide-search"
        size="md"
        class="w-64"
      />
    </template>
  </UPageHeader>

  <div>
    <!-- ADD A TOOLBAR FOR SEARCH AND FILTER -->

    <div>
      <div class="mb-4 flex items-center gap-2">
        <h2 class="text-xl font-semibold">{{ currentYear }} Ordinances</h2>
        <UBadge color="primary" size="sm"> {{ ordinances.length }}</UBadge>
      </div>

      <div>
        <UTable
          ref="table"
          v-model:pagination="pagination"
          :columns="columns"
          :data="ordinances"
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
            :total="ordinances.length"
            @update:page="(p) => (pagination.pageIndex = p - 1)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
