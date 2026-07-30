<script setup lang="ts">
import { getPaginationRowModel } from "@tanstack/vue-table";
import type { TableColumn } from "@nuxt/ui";
import { UBadge } from "#components";

const table = useTemplateRef("table");

definePageMeta({
  title: "Bids and Awards",
  layout: "transparency",
});

const getStatusColor = (status: string) => {
  switch (status) {
    case "Awarded":
      return "primary";
    case "Bidding":
      return "primary";
    case "Closed":
      return "neutral";
    default:
      return "neutral";
  }
};

const availableYears = ref(["2026", "2025", "2024", "2023"]);
const currentYear = ref("2026");
const searchQuery = ref("");

type Bids = {
  id: string;
  date: string;
  status: string;
  awarded: string;
  amount: number;
  view_count: number;
};

const data = ref<Bids[]>([
  {
    id: "4600",
    date: "2024-03-11T15:30:00",
    status: "Awarded",
    awarded: "ABC Office Supplies",
    amount: 594000,
    view_count: 123,
  },
]);

const columns: TableColumn<Bids>[] = [
  {
    accessorKey: "id",
    header: "#",
    cell: ({ row }: { row: any }) => `#${row.getValue("id")}`,
  },
  {
    accessorKey: "date",
    header: "Date",
    cell: ({ row }: { row: any }) => {
      return new Date(row.getValue("date")).toLocaleString("en-US", {
        day: "numeric",
        month: "short",
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
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
    accessorKey: "awarded",
    header: "Awarded",
    cell: ({ row }: { row: any }) => {
      return row.getValue("awarded");
    },
  },
  {
    accessorKey: "amount",
    header: "Amount",
    meta: {
      class: {
        th: "text-right",
        td: "text-right font-medium",
      },
    },
    cell: ({ row }: { row: any }) => {
      const amount = Number.parseFloat(row.getValue("amount"));
      return new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "PHP",
      }).format(amount);
    },
  },
  {
    accessorKey: "view_count",
    header: "Views",
    meta: {
      class: {
        th: "text-right",
        td: "text-right font-medium",
      },
    },
    cell: ({ row }: { row: any }) => {
      return row.getValue("view_count");
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
    title="Bids and Awards"
    description="View current bidding opportunities and awarded contracts"
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
        <h2 class="text-xl font-semibold">{{ currentYear }} Bids and Awards</h2>
        <UBadge color="primary" size="sm"> {{ data.length }}</UBadge>
      </div>

      <div>
        <UTable
          ref="table"
          v-model:pagination="pagination"
          :columns="columns"
          :data="data"
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
            :total="data.length"
            @update:page="(p) => (pagination.pageIndex = p - 1)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
