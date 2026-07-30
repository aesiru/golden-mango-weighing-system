<script setup lang="ts">
import { computed, h, onMounted, ref, watch } from "vue";
import type { NavigationMenuItem } from "@nuxt/ui";
import { VisDonut, VisSingleContainer } from "@unovis/vue";
import { CalendarDate } from "@internationalized/date";
import {
  useDashboard,
  type DashboardOption,
  type DashboardWidget,
  type DashboardChartConfig,
  type InventorySummaryData,
  type MaintenanceSummaryData,
  type PRStatusSummaryData,
  type SelectedDashboard,
  type StockCountSummaryData,
  type WOSummaryData,
  type WorkOrderTypeDistributionData,
} from "~/composables/useDashboard";
import { useBootInfo } from "~/composables/useBootInfo";

interface Stat {
  title: string;
  icon: string;
  value: number;
  variation: number;
  description: string;
}

interface DonutSlice {
  label: string;
  value: number;
  color: string;
}

interface DashboardChart {
  title: string;
  subtitle: string;
  badgeColor: "primary" | "info" | "success" | "warning" | "error" | "neutral";
  badgeLabel: string;
  totalLabel: string;
  data: DonutSlice[];
}

definePageMeta({
  title: "Dashboard",
  middleware: "auth" as any,
});

const { getDashboardWidgets } = useDashboard();
const { bootInfo } = useBootInfo();
const UBadge = resolveComponent("UBadge");

const loading = ref(true);
const error = ref<string | null>(null);
const allowedDashboards = ref<DashboardOption[]>([]);
const activeDashboard = ref<SelectedDashboard | null>(null);
const dateFilter = ref<{ start_date?: string; end_date?: string } | null>(null);
const selected = ref<{ start: Date; end: Date }>({
  start: (() => {
    const d = new Date();
    d.setDate(d.getDate() - 30);
    return d;
  })(),
  end: new Date(),
});

// Calendar model uses CalendarDate from @internationalized/date
const calendarModel = ref<{ start: CalendarDate; end: CalendarDate }>({
  start: new CalendarDate(
    selected.value.start.getFullYear(),
    selected.value.start.getMonth() + 1,
    selected.value.start.getDate(),
  ),
  end: new CalendarDate(
    selected.value.end.getFullYear(),
    selected.value.end.getMonth() + 1,
    selected.value.end.getDate(),
  ),
});

const quickRanges = [
  { label: "Last 7 days", days: 7 },
  { label: "Last 14 days", days: 14 },
  { label: "Last 30 days", days: 30 },
  { label: "Last 3 months", months: 3 },
  { label: "Last 6 months", months: 6 },
  { label: "Last year", years: 1 },
];

const statusColors: Record<string, string> = {
  Draft: "#94a3b8",
  "Pending Review": "#f59e0b",
  "Pending Approval": "#f97316",
  Approved: "#22c55e",
  Closed: "#3b82f6",
  Rejected: "#ef4444",
  Open: "#3b82f6",
  "In Progress": "#8b5cf6",
  Completed: "#22c55e",
  Overdue: "#ef4444",
  Pending: "#f59e0b",
  "On Hold": "#fb7185",
  "Preventive Maint.": "#22c55e",
  "Corrective Maint.": "#f97316",
  Unassigned: "#94a3b8",
};

const isRangeSelected = (range: {
  days?: number;
  months?: number;
  years?: number;
}) => {
  const now = new Date();
  const start = new Date();
  if (range.days) start.setDate(now.getDate() - range.days);
  else if (range.months) start.setMonth(now.getMonth() - range.months);
  else if (range.years) start.setFullYear(now.getFullYear() - range.years);
  return (
    Math.abs(start.getTime() - selected.value.start.getTime()) < 86_400_000
  );
};

const selectRange = (range: {
  days?: number;
  months?: number;
  years?: number;
}) => {
  const end = new Date();
  const start = new Date();
  if (range.days) start.setDate(end.getDate() - range.days);
  else if (range.months) start.setMonth(end.getMonth() - range.months);
  else if (range.years) start.setFullYear(end.getFullYear() - range.years);
  selected.value = { start, end };

  // Update calendar model to match
  calendarModel.value = {
    start: new CalendarDate(
      start.getFullYear(),
      start.getMonth() + 1,
      start.getDate(),
    ),
    end: new CalendarDate(end.getFullYear(), end.getMonth() + 1, end.getDate()),
  };

  // Refresh dashboard with new date range
  loadDashboard(selectedDashboardKey.value || undefined);
};

const loadDashboard = async (dashboardKey?: string) => {
  loading.value = true;
  error.value = null;

  try {
    // Use allowed dashboards from boot info
    const bootDashboards = bootInfo.value?.allowed_dashboards || [];
    allowedDashboards.value = [...bootDashboards] as DashboardOption[];

    // Determine which dashboard to load
    const targetKey =
      dashboardKey ||
      (bootDashboards.length > 0 && bootDashboards[0]?.key
        ? bootDashboards[0].key
        : null);

    if (!targetKey) {
      activeDashboard.value = null;
      return;
    }

    // Get dashboard definition from boot data
    const dashboardDef = bootDashboards.find((d: any) => d.key === targetKey);
    if (!dashboardDef) {
      throw new Error(`Dashboard ${targetKey} not found in allowed dashboards`);
    }

    // Fetch widget data only from the new endpoint with date filter
    const widgetResponse = await getDashboardWidgets(
      targetKey,
      selected.value.start,
      selected.value.end,
    );

    // Capture date filter from response
    dateFilter.value = (widgetResponse as any).date_filter || null;

    // Combine static definition from boot with dynamic widget data and updated config
    activeDashboard.value = {
      ...dashboardDef,
      widgets: widgetResponse.widgets,
      stats: (widgetResponse as any).stats || dashboardDef.stats || [],
      charts: (widgetResponse as any).charts || dashboardDef.charts || [],
    } as SelectedDashboard;
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : "Failed to load dashboard";
  } finally {
    loading.value = false;
  }
};

const onDateRangeChange = (v: any) => {
  // Update calendar model
  if (v?.start) calendarModel.value.start = v.start;
  if (v?.end) calendarModel.value.end = v.end;

  // Convert CalendarDate to Date for API calls
  if (v?.start) {
    selected.value.start = new Date(
      v.start.year,
      v.start.month - 1,
      v.start.day,
    );
  }
  if (v?.end) {
    selected.value.end = new Date(v.end.year, v.end.month - 1, v.end.day);
  }

  // Only refresh if we have a complete range (both start and end)
  if (v?.start && v?.end) {
    loadDashboard(selectedDashboardKey.value || undefined);
  } else {
  }
};

onMounted(async () => {
  await loadDashboard();
});

// Watch calendarModel for changes and trigger dashboard refresh
watch(
  calendarModel,
  (newVal) => {
    if (newVal?.start && newVal?.end) {
      // Convert CalendarDate to Date for API calls
      selected.value.start = new Date(
        newVal.start.year,
        newVal.start.month - 1,
        newVal.start.day,
      );
      selected.value.end = new Date(
        newVal.end.year,
        newVal.end.month - 1,
        newVal.end.day,
      );

      loadDashboard(selectedDashboardKey.value || undefined);
    }
  },
  { deep: true },
);

const selectedDashboardKey = computed(() => activeDashboard.value?.key ?? "");
const selectedDashboardLabel = computed(
  () => activeDashboard.value?.label ?? "Dashboard",
);
const selectedDashboardDescription = computed(
  () => activeDashboard.value?.description ?? "Role-based operational insight.",
);

const formattedDateFilter = computed(() => {
  if (!dateFilter.value?.start_date || !dateFilter.value?.end_date) return null;

  const startDate = new Date(dateFilter.value.start_date);
  const endDate = new Date(dateFilter.value.end_date);

  const formatDate = (date: Date) => {
    return date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  return `${formatDate(startDate)} - ${formatDate(endDate)}`;
});
const activeWidgets = computed(() => activeDashboard.value?.widgets ?? []);
const widgetMap = computed<Record<string, DashboardWidget>>(() =>
  Object.fromEntries(
    activeWidgets.value.map((widget) => [widget.type, widget]),
  ),
);
const hasReadonlyWidgets = computed(() =>
  activeWidgets.value.some((widget) => widget.config.readonly),
);

const getWidgetData = <T,>(type: string) =>
  widgetMap.value[type]?.data as T | undefined;
const donutValue = (d: DonutSlice) => d.value;
const donutColor = (d: DonutSlice) => d.color;
const donutTotal = (data: DonutSlice[]) =>
  data.reduce((sum, slice) => sum + slice.value, 0);

const toDonutData = (
  statusMap: Record<string, number> | undefined,
  preferredOrder: string[],
) => {
  if (!statusMap) return [] as DonutSlice[];

  const preferred = preferredOrder.filter((key) => key in statusMap);
  const otherKeys = Object.keys(statusMap).filter(
    (key) => !preferredOrder.includes(key),
  );

  const slices: DonutSlice[] = preferred.map((label) => ({
    label,
    value: Number(statusMap[label] ?? 0),
    color: statusColors[label] ?? "#64748b",
  }));

  // Group non-preferred statuses as "others"
  if (otherKeys.length > 0) {
    const othersTotal = otherKeys.reduce(
      (sum, key) => sum + Number(statusMap[key] ?? 0),
      0,
    );
    if (othersTotal > 0) {
      slices.push({
        label: "Others",
        value: othersTotal,
        color: "#94a3b8",
      });
    }
  }

  return slices.filter((item) => item.value > 0);
};

const procurementStatus = computed(
  () =>
    getWidgetData<PRStatusSummaryData>("pr_status_summary") ?? {
      total: 0,
      by_status: {},
      period: "current",
    },
);

const workOrderStatus = computed(
  () =>
    getWidgetData<WOSummaryData>("work_order_summary") ?? {
      total: 0,
      by_status: {},
      overdue_count: 0,
    },
);
const workOrderTypeDistribution = computed(
  () =>
    getWidgetData<WorkOrderTypeDistributionData>(
      "work_order_type_distribution",
    ) ?? {
      total: 0,
      by_type: {},
    },
);
const maintenanceSummary = computed(
  () =>
    getWidgetData<MaintenanceSummaryData>("maintenance_summary") ?? {
      by_status: {},
      upcoming_7_days_count: 0,
      total: 0,
    },
);

const inventorySummary = computed(
  () =>
    getWidgetData<InventorySummaryData>("inventory_summary") ?? {
      total_items: 0,
      low_stock_count: 0,
      location_count: 0,
    },
);
const stockCountSummary = computed(
  () =>
    getWidgetData<StockCountSummaryData>("stock_count_summary") ?? {
      pending_count: 0,
      in_progress_count: 0,
      total_active: 0,
      by_status: {},
    },
);

const activeStats = computed<Stat[]>(() => {
  const statsConfig = activeDashboard.value?.stats ?? [];
  return statsConfig.map((statConfig: any) => {
    const sourceData = getWidgetData<any>(statConfig.source);
    let value = 0;

    if (sourceData) {
      if (statConfig.field.includes(".")) {
        const parts = statConfig.field.split(".");
        value =
          parts.reduce((obj: any, key: string) => obj?.[key], sourceData) ?? 0;
      } else {
        value = sourceData[statConfig.field] ?? 0;
      }
    }

    return {
      title: statConfig.title,
      icon: statConfig.icon,
      value: typeof value === "number" ? value : 0,
      variation: statConfig.variation ?? 0,
      description: statConfig.title,
    };
  });
});

const activeCharts = computed<DashboardChart[]>(() => {
  const chartsConfig = activeDashboard.value?.charts ?? [];
  return chartsConfig.map((chartConfig: DashboardChartConfig) => {
    const sourceData = getWidgetData<any>(chartConfig.source);
    let badgeLabel = "";
    let data: DonutSlice[] = [];
    let totalLabel = "";

    if (sourceData) {
      if (chartConfig.custom_data) {
        // Handle custom data logic for inventory charts
        if (chartConfig.title === "Inventory Health") {
          const totalItems = inventorySummary.value.total_items ?? 0;
          const lowStock = inventorySummary.value.low_stock_count ?? 0;
          const healthy = Math.max(totalItems - lowStock, 0);
          badgeLabel = `${lowStock} low stock`;
          totalLabel = "tracked items";
          data = [
            { label: "Healthy", value: healthy, color: "#22c55e" },
            { label: "Low Stock", value: lowStock, color: "#ef4444" },
          ].filter((slice) => slice.value > 0);
        } else if (chartConfig.title === "Stock Count Activity") {
          const activeCounts = stockCountSummary.value.total_active ?? 0;
          const pendingCounts = stockCountSummary.value.pending_count ?? 0;
          const inProgressCounts =
            stockCountSummary.value.in_progress_count ?? 0;
          badgeLabel = `${activeCounts} active`;
          totalLabel = "count tasks";
          data = [
            { label: "Pending", value: pendingCounts, color: "#f59e0b" },
            { label: "In Progress", value: inProgressCounts, color: "#8b5cf6" },
            {
              label: "No Active Tasks",
              value: activeCounts === 0 ? 1 : 0,
              color: "#94a3b8",
            },
          ].filter((slice) => slice.value > 0);
        }
      } else {
        // Standard donut chart from by_status data
        const totalValue = sourceData[chartConfig.total_field] ?? 0;
        const statusData = sourceData[chartConfig.data_field] ?? {};
        badgeLabel = `${totalValue} total`;
        totalLabel =
          chartConfig.title.toLowerCase().replace(" status", "") + "s";
        data = toDonutData(statusData, chartConfig.preferred_order || []);
      }
    }

    return {
      title: chartConfig.title,
      subtitle: chartConfig.subtitle,
      badgeColor: chartConfig.badge_color,
      badgeLabel,
      totalLabel,
      data,
    };
  });
});

const badgeColor = (status: string) => {
  const map: Record<
    string,
    "neutral" | "warning" | "success" | "error" | "info"
  > = {
    Draft: "neutral",
    "Pending Review": "warning",
    "Pending Approval": "warning",
    Approved: "success",
    Rejected: "error",
    Closed: "info",
    Open: "info",
    "In Progress": "primary" as never,
    Completed: "success",
    "On Hold": "warning",
  };
  return (map[status] ?? "neutral") as
    | "neutral"
    | "warning"
    | "success"
    | "error"
    | "info";
};

// Navigation menu links for dashboard switching
const navigationLinks = computed<NavigationMenuItem[][]>(() => {
  return [
    allowedDashboards.value.map((dashboard) => ({
      label: dashboard.label,
      icon: dashboard.icon,
      value: dashboard.key,
      active: selectedDashboardKey.value === dashboard.key,
      onSelect: () => loadDashboard(dashboard.key),
    })),
  ];
});
</script>

<template>
  <UDashboardPanel id="dashboard" :ui="{ body: 'lg:py-8' }">
    <template #header>
      <UDashboardNavbar title="Dashboard" :ui="{ right: 'gap-3' }">
        <template #right>
          <UPopover :content="{ align: 'start' }" :modal="true">
            <UButton
              color="neutral"
              variant="outline"
              icon="i-lucide-calendar"
              class="data-[state=open]:bg-elevated group"
            >
              <span class="truncate">
                {{ selected.start.toLocaleDateString() }} -
                {{ selected.end.toLocaleDateString() }}
              </span>
              <template #trailing>
                <UIcon
                  name="i-lucide-chevron-down"
                  class="shrink-0 text-dimmed size-4 group-data-[state=open]:rotate-180 transition-transform duration-200"
                />
              </template>
            </UButton>

            <template #content>
              <div class="flex items-stretch sm:divide-x divide-default">
                <div class="hidden sm:flex flex-col justify-center py-2">
                  <UButton
                    v-for="(r, i) in quickRanges"
                    :key="i"
                    :label="r.label"
                    color="neutral"
                    variant="ghost"
                    class="rounded-none px-4 text-sm"
                    :class="
                      isRangeSelected(r)
                        ? 'bg-elevated font-medium'
                        : 'hover:bg-elevated/50'
                    "
                    truncate
                    @click="selectRange(r)"
                  />
                </div>
                <UCalendar
                  v-model="calendarModel as any"
                  class="p-2"
                  :number-of-months="2"
                  range
                />
              </div>
            </template>
          </UPopover>
        </template>
      </UDashboardNavbar>

      <UDashboardToolbar>
        <template #left>
          <!-- NOTE: The -mx-1 class is used to align with the DashboardSidebarCollapse button here. -->
          <UNavigationMenu
            :items="navigationLinks"
            highlight
            color="neutral"
            class="-mx-1 flex-1"
          />
        </template>

        <template #right>
          <UBadge
            v-if="hasReadonlyWidgets"
            color="warning"
            variant="subtle"
            size="sm"
            label="Read only"
          />
          <UButton
            color="neutral"
            variant="ghost"
            icon="i-lucide-refresh-cw"
            size="sm"
            label="Refresh"
            @click="loadDashboard(selectedDashboardKey || undefined)"
          />
        </template>
      </UDashboardToolbar>
    </template>

    <template #body>
      <div class="flex flex-col gap-6 w-full">
        <template v-if="loading">
          <div class="space-y-6">
            <div class="grid grid-cols-2 lg:grid-cols-6 gap-4">
              <USkeleton v-for="i in 6" :key="i" class="h-28 rounded-xl" />
            </div>
            <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <USkeleton class="h-72 rounded-xl" />
              <USkeleton class="h-72 rounded-xl" />
            </div>
            <USkeleton class="h-80 rounded-xl" />
          </div>
        </template>

        <template v-else-if="error">
          <div class="flex flex-col items-center justify-center h-64 gap-4">
            <UIcon name="i-lucide-alert-triangle" class="size-12 text-error" />
            <p class="text-muted text-sm">{{ error }}</p>
            <UButton
              size="sm"
              variant="outline"
              label="Retry"
              icon="i-lucide-refresh-cw"
              @click="loadDashboard(selectedDashboardKey || undefined)"
            />
          </div>
        </template>

        <template v-else-if="!activeDashboard">
          <div
            class="flex flex-col items-center justify-center h-72 gap-4 px-6"
          >
            <UIcon
              name="i-lucide-layout-dashboard"
              class="size-12 text-muted"
            />
            <div class="text-center space-y-1">
              <p class="font-medium text-highlighted">
                No dashboards available
              </p>
              <p class="text-sm text-muted">
                Your current role set does not map to any configured dashboard.
              </p>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="space-y-6">
            <UCard
              variant="subtle"
              class="overflow-hidden bg-gradient-to-br from-primary-800 to-primary-600"
              color=""
            >
              <div
                class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
              >
                <div class="space-y-1">
                  <div class="flex items-center gap-2">
                    <UIcon
                      :name="activeDashboard.icon"
                      class="size-5 text-primary"
                    />
                    <p
                      class="text-lg font-semibold text-highlighted text-white"
                    >
                      {{ selectedDashboardLabel }} Overview
                    </p>
                  </div>
                  <p class="text-sm text-muted max-w-2xl text-white">
                    {{ selectedDashboardDescription }}
                  </p>
                </div>

                <div class="grid grid-cols-3 gap-3 min-w-[220px] lg:w-auto">
                  <div
                    class="rounded-lg col-span-2 bg-default/60 px-4 py-3 border border-muted"
                  >
                    <p class="text-[11px] uppercase tracking-wide text-muted">
                      Date Range
                    </p>
                    <p
                      class="text-xl font-semibold text-highlighted text-primary-900"
                    >
                      {{ formattedDateFilter }}
                    </p>
                  </div>
                  <div
                    class="rounded-lg bg-default/60 px-4 py-3 border border-muted"
                  >
                    <p class="text-[11px] uppercase tracking-wide text-muted">
                      Widgets
                    </p>
                    <p
                      class="text-xl font-semibold text-highlighted text-primary-900"
                    >
                      {{ activeWidgets.length }}
                    </p>
                  </div>
                </div>
              </div>
            </UCard>

            <UPageGrid class="lg:grid-cols-4 gap-px">
              <UPageCard
                v-for="(stat, i) in activeStats"
                :key="i"
                :icon="stat.icon"
                :title="stat.title"
                variant="subtle"
                :ui="{
                  container: 'gap-y-1',
                  wrapper: 'items-start',
                  leading:
                    'p-2 rounded-lg bg-primary/10 ring ring-inset ring-primary/20',
                  title:
                    'font-normal text-muted text-[11px] uppercase tracking-wide',
                }"
                class="lg:rounded-none first:rounded-l-xl last:rounded-r-xl hover:z-1 transition-shadow hover:shadow-md"
              >
                <div class="flex gap-2 items-center">
                  <span
                    class="text-2xl font-bold text-highlighted tabular-nums"
                  >
                    {{ stat.value }}
                  </span>
                  <UBadge
                    :color="
                      stat.variation > 0
                        ? 'success'
                        : stat.variation < 0
                          ? 'error'
                          : 'neutral'
                    "
                    variant="subtle"
                    size="md"
                  >
                    {{ stat.variation > 0 ? "+" : "" }}{{ stat.variation }}%
                  </UBadge>
                </div>
                <p class="text-[11px] text-muted mt-0.5">
                  {{ stat.description }}
                </p>
              </UPageCard>
            </UPageGrid>

            <div
              :class="`grid grid-cols-1 ${activeCharts.length === 1 ? '' : 'lg:grid-cols-2'} gap-6`"
            >
              <UCard
                v-for="chart in activeCharts"
                :key="chart.title"
                variant="outline"
                :ui="{ body: 'p-0' }"
              >
                <template #header>
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="font-semibold text-highlighted">
                        {{ chart.title }}
                      </p>
                      <p class="text-xs text-muted mt-0.5">
                        {{ chart.subtitle }}
                      </p>
                    </div>
                    <UBadge
                      :color="chart.badgeColor"
                      variant="subtle"
                      :label="chart.badgeLabel"
                    />
                  </div>
                </template>

                <div
                  class="flex flex-col sm:flex-row items-center gap-6 px-6 pb-6"
                >
                  <div class="relative shrink-0 size-44">
                    <VisSingleContainer :data="chart.data" :height="176">
                      <VisDonut
                        :value="donutValue"
                        :color="donutColor"
                        :arcWidth="36"
                        :padAngle="0.02"
                        :cornerRadius="4"
                      />
                    </VisSingleContainer>
                    <div
                      class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none"
                    >
                      <span class="text-2xl font-bold text-highlighted">
                        {{ donutTotal(chart.data) }}
                      </span>
                      <span class="text-[11px] text-muted">{{
                        chart.totalLabel
                      }}</span>
                    </div>
                  </div>

                  <div class="flex-1 space-y-2 w-full">
                    <div
                      v-for="item in chart.data"
                      :key="item.label"
                      class="flex items-center justify-between gap-3"
                    >
                      <div class="flex items-center gap-2 min-w-0">
                        <span
                          class="size-2.5 rounded-full shrink-0"
                          :style="{ backgroundColor: item.color }"
                        />
                        <span class="text-sm text-default truncate">{{
                          item.label
                        }}</span>
                      </div>
                      <div class="flex items-center gap-2 shrink-0">
                        <div
                          class="w-20 bg-elevated rounded-full h-1.5 overflow-hidden"
                        >
                          <div
                            class="h-full rounded-full transition-all duration-500"
                            :style="{
                              width: `${donutTotal(chart.data) ? (item.value / donutTotal(chart.data)) * 100 : 0}%`,
                              backgroundColor: item.color,
                            }"
                          />
                        </div>
                        <span
                          class="text-sm font-medium tabular-nums text-highlighted w-8 text-right"
                        >
                          {{ item.value }}
                        </span>
                      </div>
                    </div>
                  </div>
                </div>
              </UCard>
            </div>

            <UCard variant="outline" :ui="{ body: 'p-0' }">
              <template #header>
                <div class="flex items-center justify-between">
                  <div>
                    <p class="font-semibold text-highlighted">
                      {{
                        selectedDashboardKey === "procurement"
                          ? "Purchase Request Queue"
                          : selectedDashboardKey === "work-management"
                            ? "Work Management Queue"
                            : "Low Stock Watchlist"
                      }}
                    </p>
                    <p class="text-xs text-muted mt-0.5">
                      {{
                        selectedDashboardKey === "procurement"
                          ? "Pending approval requests that need attention."
                          : selectedDashboardKey === "work-management"
                            ? "Overdue, urgent, or user-assigned work orders."
                            : "Items currently below the replenishment threshold."
                      }}
                    </p>
                  </div>
                  <UButton
                    v-if="selectedDashboardKey === 'procurement'"
                    to="/purchase-requests"
                    size="sm"
                    color="neutral"
                    variant="ghost"
                    trailing-icon="i-lucide-arrow-right"
                    label="View All"
                  />
                </div>
              </template>
            </UCard>
          </div>
        </template>
      </div>
    </template>
  </UDashboardPanel>
</template>
