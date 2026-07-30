<script setup lang="ts">
import { CalendarDate, parseDate } from "@internationalized/date";

const { getEntityOptions } = useApi();
const { apiFetch, baseURL } = useApiFetch();
const toast = useToast();

interface ReportFilter {
  key: string;
  label: string;
  type: string;
  default?: any;
  description?: string;
  link_entity?: string;
}

interface ReportDef {
  key: string;
  title: string;
  description: string;
  icon: string;
  category: string;
  filters: ReportFilter[];
}

const reports = ref<ReportDef[]>([]);
const loading = ref(true);
const generating = ref(false);
const selectedReport = ref<ReportDef | null>(null);
const filterModalOpen = ref(false);
const filterValues = ref<Record<string, any>>({});
const linkOptions = ref<Record<string, { label: string; value: string }[]>>({});
const loadingLinkOptions = ref<Record<string, boolean>>({});

// Report preview state
const previewHtml = ref("");
const showPreview = ref(false);
const printLoading = ref(false);
const previewIframe = ref<HTMLIFrameElement | null>(null);

const dateRangeRef = useTemplateRef("dateRangeRef");
type ReportDateRange = { start: CalendarDate; end: CalendarDate };

const getDefaultDateRange = (): ReportDateRange => {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - 30);

  const toValue = (date: Date) =>
    `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(
      date.getDate(),
    ).padStart(2, "0")}`;

  return {
    start: parseDate(toValue(start)),
    end: parseDate(toValue(end)),
  };
};

const toCalendarDate = (value?: string | null): CalendarDate | undefined => {
  if (!value) return undefined;
  try {
    return parseDate(value);
  } catch {
    return undefined;
  }
};

const fromCalendarDate = (
  value: CalendarDate | null | undefined,
): string | undefined => {
  if (!value) return undefined;
  return value.toString();
};

const hasDateRangeFilters = computed(() => {
  const filters = selectedReport.value?.filters || [];
  return (
    filters.some((f) => f.key === "from_date" && f.type === "date") &&
    filters.some((f) => f.key === "to_date" && f.type === "date")
  );
});

const nonRangeFilters = computed(() => {
  const filters = selectedReport.value?.filters || [];
  if (!hasDateRangeFilters.value) return filters;
  return filters.filter((f) => f.key !== "from_date" && f.key !== "to_date");
});

const dateRangeValue = computed<ReportDateRange | null>({
  get() {
    const start = toCalendarDate(filterValues.value.from_date);
    const end = toCalendarDate(filterValues.value.to_date);
    if (!hasDateRangeFilters.value) return null;
    if (!start || !end) return getDefaultDateRange();
    return { start, end };
  },
  set(value) {
    const range = value ?? getDefaultDateRange();
    filterValues.value.from_date = fromCalendarDate(range.start);
    filterValues.value.to_date = fromCalendarDate(range.end);
  },
});

const loadLinkOptions = async (linkEntity?: string) => {
  if (!linkEntity || linkOptions.value[linkEntity]) return;
  loadingLinkOptions.value[linkEntity] = true;
  try {
    const res = await getEntityOptions(linkEntity, undefined, 10);
    if (res.status === "success") {
      linkOptions.value[linkEntity] = res.options || [];
    }
  } catch {
    linkOptions.value[linkEntity] = [];
  } finally {
    loadingLinkOptions.value[linkEntity] = false;
  }
};

const loadReports = async () => {
  loading.value = true;
  try {
    const res = await apiFetch<{ status: string; data: ReportDef[] }>(
      `${baseURL}/reports`,
    );
    if (res.status === "success") {
      reports.value = res.data;
    }
  } catch (err: any) {
    toast.add({
      title: "Failed to load reports",
      description: err?.message,
      color: "error",
    });
  } finally {
    loading.value = false;
  }
};

const openFilterModal = (report: ReportDef) => {
  selectedReport.value = report;
  filterValues.value = {};

  if (
    report.filters.some((f) => f.key === "from_date" && f.type === "date") &&
    report.filters.some((f) => f.key === "to_date" && f.type === "date")
  ) {
    const defaultRange = getDefaultDateRange();
    filterValues.value.from_date = fromCalendarDate(defaultRange.start);
    filterValues.value.to_date = fromCalendarDate(defaultRange.end);
  }

  // Set defaults
  for (const f of report.filters) {
    if (f.default !== undefined) {
      filterValues.value[f.key] = f.default;
    }
    if (f.type === "link" && f.link_entity) {
      loadLinkOptions(f.link_entity);
    }
  }
  filterModalOpen.value = true;
};

const getRequestFilters = () => {
  const payload: Record<string, any> = {};
  for (const [key, value] of Object.entries(filterValues.value)) {
    if (value === undefined || value === null || value === "") continue;
    payload[key] = value;
  }
  return payload;
};

const generatePreview = async () => {
  if (!selectedReport.value) return;
  generating.value = true;
  try {
    const res = await apiFetch<{
      status: string;
      data: { html: string; title: string };
    }>(`${baseURL}/reports/${selectedReport.value.key}/generate`, {
      method: "POST",
      body: getRequestFilters(),
    });
    if (res.status === "success") {
      previewHtml.value = res.data.html;
      filterModalOpen.value = false;
      showPreview.value = true;
    }
  } catch (err: any) {
    toast.add({
      title: "Failed to generate report",
      description: err?.message,
      color: "error",
    });
  } finally {
    generating.value = false;
  }
};

const downloadPdf = async () => {
  if (!selectedReport.value) return;
  printLoading.value = true;
  try {
    const blob = await apiFetch<Blob>(
      `${baseURL}/reports/${selectedReport.value.key}/pdf`,
      {
        method: "POST",
        body: getRequestFilters(),
        responseType: "blob",
      } as any,
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedReport.value.key}_${new Date().toISOString().slice(0, 10)}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    toast.add({ title: "PDF downloaded", color: "success" });
  } catch (err: any) {
    toast.add({
      title: "Failed to download PDF",
      description: err?.message,
      color: "error",
    });
  } finally {
    printLoading.value = false;
  }
};

const downloadExcel = async () => {
  if (!selectedReport.value) return;
  printLoading.value = true;
  try {
    const blob = await apiFetch<Blob>(
      `${baseURL}/reports/${selectedReport.value.key}/xlsx`,
      {
        method: "POST",
        body: getRequestFilters(),
        responseType: "blob",
      } as any,
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${selectedReport.value.key}_${new Date().toISOString().slice(0, 10)}.xlsx`;
    a.click();
    URL.revokeObjectURL(url);
    toast.add({ title: "Excel downloaded", color: "success" });
  } catch (err: any) {
    toast.add({
      title: "Failed to download Excel",
      description: err?.message,
      color: "error",
    });
  } finally {
    printLoading.value = false;
  }
};

const printFromPreview = () => {
  if (!previewHtml.value) return;
  const printWindow = window.open("", "_blank");
  if (printWindow) {
    printWindow.document.write(previewHtml.value);
    printWindow.document.close();
    printWindow.focus();
    printWindow.onload = () => printWindow.print();
  }
};

const resizeIframe = () => {
  const iframe = previewIframe.value;
  if (!iframe) return;
  try {
    const doc = iframe.contentDocument || iframe.contentWindow?.document;
    if (doc?.body) {
      const contentHeight =
        doc.documentElement.scrollHeight || doc.body.scrollHeight;
      if (contentHeight > 0) {
        const wrapper = iframe.parentElement;
        if (wrapper) {
          wrapper.style.paddingTop = "0";
          wrapper.style.height = `${contentHeight}px`;
        }
        iframe.style.height = `${contentHeight}px`;
      }
    }
  } catch (_error) {
    // Keep aspect-ratio wrapper fallback
  }
};

// Resize iframe when preview HTML changes
watch(previewHtml, () => {
  nextTick(() => {
    resizeIframe();
  });
});

// Group reports by category
const groupedReports = computed(() => {
  const groups: Record<string, ReportDef[]> = {};
  for (const r of reports.value) {
    const cat = r.category || "General";
    if (!groups[cat]) groups[cat] = [];
    groups[cat].push(r);
  }
  return groups;
});

onMounted(() => {
  loadReports();
});

definePageMeta({ middleware: "auth" as any });
</script>

<template>
  <div class="h-full min-h-0 overflow-y-auto p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">Reports</h1>
        <p class="text-sm text-muted-foreground">
          Generate and download reports as PDF
        </p>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="flex items-center justify-center py-20">
      <UIcon
        name="i-lucide-loader-2"
        class="animate-spin h-8 w-8 text-primary"
      />
    </div>

    <!-- Report Cards by Category -->
    <template v-else>
      <div
        v-for="(categoryReports, category) in groupedReports"
        :key="category"
        class="space-y-4"
      >
        <h2 class="text-lg font-semibold flex items-center gap-2">
          <UIcon name="i-lucide-folder" class="w-5 h-5 text-primary" />
          {{ category }}
        </h2>
        <UPageGrid>
          <UCard
            v-for="report in categoryReports"
            :key="report.key"
            variant="outline"
            class="cursor-pointer group transition-all hover:shadow-sm hover:ring-1 hover:ring-primary/30"
            :ui="{ body: 'p-5 space-y-3' }"
            @click="openFilterModal(report)"
          >
            <div class="flex items-start gap-3">
              <div
                class="p-2 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-white transition-colors"
              >
                <UIcon :name="report.icon" class="w-6 h-6" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-semibold text-sm">{{ report.title }}</h3>
                <p class="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {{ report.description }}
                </p>
              </div>
            </div>
            <div
              class="mt-3 flex items-center gap-1 text-xs text-muted-foreground"
            >
              <UIcon name="i-lucide-sliders-horizontal" class="w-3 h-3" />
              {{ report.filters.length }} filter{{
                report.filters.length !== 1 ? "s" : ""
              }}
            </div>
          </UCard>
        </UPageGrid>
      </div>

      <div
        v-if="reports.length === 0"
        class="text-center py-20 text-muted-foreground"
      >
        <UIcon name="i-lucide-file-x" class="w-12 h-12 mx-auto mb-3" />
        <p class="text-lg font-medium">No reports available</p>
        <p class="text-sm">Reports will appear here once configured.</p>
      </div>
    </template>

    <!-- Filter Modal -->
    <UModal
      v-model:open="filterModalOpen"
      :title="selectedReport?.title || 'Report Filters'"
      scrollable
    >
      <template #body>
        <div v-if="selectedReport" class="space-y-4">
          <p class="text-sm text-muted-foreground">
            {{ selectedReport.description }}
          </p>

          <UFormField
            v-if="hasDateRangeFilters"
            label="Date Range"
            hint="Select the report period"
          >
            <UInputDate
              ref="dateRangeRef"
              :model-value="dateRangeValue as any"
              @update:model-value="(val) => (dateRangeValue = val as any)"
              range
              color="neutral"
              variant="outline"
              class="w-full"
            >
              <template #trailing>
                <UPopover :reference="dateRangeRef?.inputsRef?.[0]?.$el">
                  <UButton
                    color="neutral"
                    variant="link"
                    size="sm"
                    icon="i-lucide-calendar-range"
                    aria-label="Select a date range"
                    class="px-0"
                  />

                  <template #content>
                    <UCalendar
                      :model-value="dateRangeValue as any"
                      @update:model-value="
                        (val) => (dateRangeValue = val as any)
                      "
                      class="p-2"
                      :number-of-months="2"
                      range
                    />
                  </template>
                </UPopover>
              </template>
            </UInputDate>
          </UFormField>

          <div
            v-for="filter in nonRangeFilters"
            :key="filter.key"
            class="space-y-1"
          >
            <UFormField :label="filter.label" :hint="filter.description">
              <UInput
                v-if="filter.type === 'number'"
                type="number"
                v-model="filterValues[filter.key]"
                :placeholder="String(filter.default ?? '')"
                class="w-full"
              />
              <UInput
                v-else-if="filter.type === 'text' || filter.type === 'string'"
                v-model="filterValues[filter.key]"
                class="w-full"
              />
              <UInputDate
                v-else-if="filter.type === 'date'"
                :model-value="toCalendarDate(filterValues[filter.key]) as any"
                @update:model-value="
                  filterValues[filter.key] = fromCalendarDate(
                    $event as CalendarDate | null | undefined,
                  )
                "
                color="neutral"
                variant="outline"
                class="w-full"
              />
              <UInputMenu
                v-else-if="filter.type === 'link' && filter.link_entity"
                v-model="filterValues[filter.key]"
                :items="linkOptions[filter.link_entity] || []"
                value-key="value"
                :loading="loadingLinkOptions[filter.link_entity]"
                :placeholder="`Select ${filter.label}`"
                class="w-full"
              />
              <UInput
                v-else
                v-model="filterValues[filter.key]"
                :placeholder="filter.label"
                class="w-full"
              />
            </UFormField>
          </div>

          <div
            v-if="selectedReport.filters.length === 0"
            class="text-center py-4 text-muted-foreground text-sm"
          >
            No filters required for this report.
          </div>
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="outline" @click="filterModalOpen = false">
            Cancel
          </UButton>
          <UButton
            icon="i-lucide-eye"
            :loading="generating"
            @click="generatePreview"
          >
            Preview
          </UButton>
          <UButton
            icon="i-lucide-file-spreadsheet"
            variant="outline"
            :loading="generating"
            @click="downloadExcel"
          >
            Export Excel
          </UButton>
          <UButton
            icon="i-lucide-download"
            color="primary"
            variant="soft"
            :loading="generating"
            @click="downloadPdf"
          >
            Download PDF
          </UButton>
        </div>
      </template>
    </UModal>

    <!-- Preview Modal -->
    <UModal
      v-model:open="showPreview"
      :title="`${selectedReport?.title || 'Report'} — Preview`"
      :ui="{
        content: 'max-w-4xl w-full max-h-screen flex flex-col',
        body: 'flex-1 min-h-0',
        footer: 'shrink-0',
      }"
    >
      <template #body>
        <div class="relative flex-1 min-h-0 bg-white overflow-auto">
          <div
            v-if="printLoading"
            class="absolute inset-0 flex items-center justify-center bg-white/80 z-10"
          >
            <UIcon
              name="i-lucide-loader-2"
              class="animate-spin text-2xl text-gray-400"
            />
          </div>
          <iframe
            v-if="previewHtml"
            ref="previewIframe"
            :srcdoc="previewHtml"
            class="w-full min-h-full border-0"
            style="height: auto"
            @load="resizeIframe"
          />
        </div>
      </template>

      <template #footer>
        <div class="flex justify-end gap-2">
          <UButton variant="outline" @click="showPreview = false">
            Close
          </UButton>
          <UButton
            icon="i-lucide-printer"
            variant="soft"
            @click="printFromPreview"
          >
            Print
          </UButton>
          <UButton
            icon="i-lucide-file-spreadsheet"
            variant="outline"
            :loading="printLoading"
            @click="downloadExcel"
          >
            Export Excel
          </UButton>
          <UButton
            icon="i-lucide-download"
            color="primary"
            :loading="printLoading"
            @click="downloadPdf"
          >
            Download PDF
          </UButton>
        </div>
      </template>
    </UModal>
  </div>
</template>
