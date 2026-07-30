<script setup lang="ts">
import type {
  ImportResult,
  ImportValidationResult,
  MetaListItem,
} from "~/composables/useApiTypes";

type ImportMode = "create" | "update";
type SourceMode = "file" | "url";
type WorkspaceTab = "create" | "update" | "export";

const {
  getMeta,
  downloadImportTemplate,
  validateImportFile,
  validateImportSheets,
  executeImportFile,
  executeImportSheets,
  exportEntity,
} = useApi();

const toast = useToast();

const workspaceTab = ref<WorkspaceTab>("create");
const sourceMode = ref<SourceMode>("file");
const selectedEntity = ref<{ label: string; value: string } | undefined>(
  undefined,
);
const file = ref<File | null>(null);
const fileUploadModel = ref<File | null>(null);
const sheetsUrl = ref("");
const validationResults = ref<ImportValidationResult | null>(null);
const validationMode = ref<ImportMode | null>(null);
const loadingEntities = ref(false);
const validating = ref(false);
const importing = ref(false);
const exporting = ref(false);
const entityOptions = ref<{ label: string; value: string }[]>([]);

const tabItems = [
  { label: "Import", icon: "i-lucide-upload", value: "create" },
  { label: "Update", icon: "i-lucide-refresh-cw", value: "update" },
  { label: "Export", icon: "i-lucide-download", value: "export" },
];

const sourceItems = [
  { label: "File Upload", value: "file" },
  { label: "Google Sheets", value: "url" },
];

const currentMode = computed<ImportMode>(() =>
  workspaceTab.value === "update" ? "update" : "create",
);

const selectedEntityName = computed(() => selectedEntity.value?.value || "");
const selectedEntityLabel = computed(
  () => selectedEntity.value?.label || "selected entity",
);
const isImportWorkspace = computed(() => workspaceTab.value !== "export");
const primaryActionLabel = computed(() =>
  workspaceTab.value === "update" ? "Update Records" : "Import Records",
);

const resetValidation = () => {
  validationResults.value = null;
  validationMode.value = null;
};

const resetSourceInputs = () => {
  file.value = null;
  fileUploadModel.value = null;
  sheetsUrl.value = "";
  resetValidation();
};

const loadEntityOptions = async () => {
  if (entityOptions.value.length) return;

  loadingEntities.value = true;
  try {
    const res = await getMeta();
    if (res.status !== "success") {
      throw new Error("Failed to load entities");
    }

    entityOptions.value = (res.data as MetaListItem[])
      .filter((entity) => entity.in_sidebar)
      .map((entity) => ({ label: entity.label, value: entity.name }));
  } catch (error: any) {
    toast.add({
      title: "Failed to load entities",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    loadingEntities.value = false;
  }
};

const ensureEntitySelected = () => {
  if (selectedEntity.value) return true;

  toast.add({
    title: "Select an entity first",
    color: "warning",
  });
  return false;
};

const ensureSourceReady = () => {
  if (sourceMode.value === "file") {
    if (file.value) return true;
    toast.add({
      title: "Choose a file first",
      description: "Upload a CSV or XLSX file before continuing.",
      color: "warning",
    });
    return false;
  }

  if (!sheetsUrl.value) {
    toast.add({
      title: "Paste a Google Sheets URL",
      color: "warning",
    });
    return false;
  }

  try {
    const url = new URL(sheetsUrl.value);
    if (
      !url.hostname.includes("docs.google.com") ||
      !url.pathname.includes("/spreadsheets/")
    ) {
      throw new Error("Invalid Google Sheets URL");
    }
  } catch {
    toast.add({
      title: "Invalid Google Sheets URL",
      description: "Use a valid published or accessible Google Sheets link.",
      color: "warning",
    });
    return false;
  }

  return true;
};

const setSelectedFile = (value: File | File[] | null | undefined) => {
  file.value = Array.isArray(value) ? value[0] || null : value || null;
  if (file.value) {
    resetValidation();
  }
};

const handleTemplateDownload = async () => {
  if (!ensureEntitySelected()) return;

  try {
    const blob = await downloadImportTemplate(selectedEntityName.value);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${selectedEntityName.value}_import_template.xlsx`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error: any) {
    toast.add({
      title: "Template download failed",
      description: error?.message || "Please try again",
      color: "error",
    });
  }
};

const runValidation = async () => {
  if (!ensureEntitySelected() || !ensureSourceReady()) return;

  validating.value = true;
  resetValidation();

  try {
    const response =
      sourceMode.value === "file"
        ? await validateImportFile(
            selectedEntityName.value,
            file.value!,
            currentMode.value,
          )
        : await validateImportSheets(
            selectedEntityName.value,
            sheetsUrl.value,
            currentMode.value,
          );

    validationResults.value = response.data || null;
    validationMode.value = currentMode.value;

    if (response.data?.valid) {
      toast.add({
        title: "Validation successful",
        description: `${response.data.rows || 0} row(s) are ready for ${currentMode.value === "update" ? "update" : "import"}.`,
        color: "success",
      });
      return;
    }

    toast.add({
      title: response.message || "Validation failed",
      description: `Found ${response.data?.errors?.length || 0} row error(s).`,
      color: "error",
    });
  } catch (error: any) {
    toast.add({
      title: error?.message || "Validation failed",
      description: "Please review your data source and try again.",
      color: "error",
    });
  } finally {
    validating.value = false;
  }
};

const runImportAction = async () => {
  if (!ensureEntitySelected() || !ensureSourceReady()) return;

  if (
    !validationResults.value?.valid ||
    validationMode.value !== currentMode.value
  ) {
    toast.add({
      title: "Validate first",
      description: `Run validation for ${currentMode.value === "update" ? "update" : "import"} before applying changes.`,
      color: "warning",
    });
    return;
  }

  importing.value = true;
  try {
    const response =
      sourceMode.value === "file"
        ? await executeImportFile(
            selectedEntityName.value,
            file.value!,
            currentMode.value,
          )
        : await executeImportSheets(
            selectedEntityName.value,
            sheetsUrl.value,
            currentMode.value,
          );

    if (response.status !== "success") {
      throw new Error(response.message || "Operation failed");
    }

    const result = response.data as ImportResult | undefined;
    const successTitle =
      currentMode.value === "update"
        ? "Update successful"
        : "Import successful";
    let description = response.message || "Completed successfully";

    if (currentMode.value === "update" && result?.missing) {
      description += ` Missing: ${result.missing}.`;
    }

    toast.add({
      title: successTitle,
      description,
      color: "success",
    });

    resetSourceInputs();
  } catch (error: any) {
    toast.add({
      title: currentMode.value === "update" ? "Update failed" : "Import failed",
      description:
        error?.message || "Please review the source data and try again.",
      color: "error",
    });
  } finally {
    importing.value = false;
  }
};

const handleExport = async (format: "xlsx" | "csv") => {
  if (!ensureEntitySelected()) return;

  exporting.value = true;
  try {
    const blob = await exportEntity(selectedEntityName.value, format);
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `${selectedEntityName.value}_export.${format}`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error: any) {
    toast.add({
      title: "Export failed",
      description: error?.message || "Please try again",
      color: "error",
    });
  } finally {
    exporting.value = false;
  }
};

watch(workspaceTab, () => {
  resetValidation();
});

watch(sourceMode, () => {
  resetValidation();
});

watch(selectedEntity, () => {
  resetValidation();
});

watch(sheetsUrl, () => {
  if (sourceMode.value === "url") {
    resetValidation();
  }
});
</script>

<template>
  <div class="mx-auto space-y-6 p-6 md:p-6">
    <div
      class="flex flex-col gap-4 md:flex-row md:items-end md:justify-between"
    >
      <div>
        <h1 class="text-2xl md:text-3xl font-semibold">
          Import, Update & Export
        </h1>
        <p class="text-sm text-muted-foreground">
          Work with structured data using templates, file uploads, or Google
          Sheets.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <UButton
          variant="outline"
          icon="i-lucide-file-spreadsheet"
          @click="handleTemplateDownload"
        >
          Download Template
        </UButton>
      </div>
    </div>

    <div class="space-y-3">
      <div class="">
        <UFormField label="Entity" required>
          <USelectMenu
            v-model="selectedEntity"
            :items="entityOptions"
            placeholder="Select entity"
            :loading="loadingEntities"
            class="w-full"
            @update:open="(open: boolean) => open && loadEntityOptions()"
          />
        </UFormField>
      </div>
      <UAlert
        color="neutral"
        variant="subtle"
        icon="i-lucide-info"
        title="Export includes the id column so the file can be reused in Update mode."
      />

      <UTabs
        v-model="workspaceTab"
        :items="tabItems"
        variant="pill"
        color="neutral"
        :unmount-on-hide="false"
        class="w-full"
      >
        <template #content>
          <div
            v-if="isImportWorkspace"
            class="space-y-6 border border-accented rounded-md p-4"
          >
            <div class="grid grid-cols-1 gap-6 lg:grid-cols-8">
              <div class="lg:col-span-5 space-y-5">
                <div
                  class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"
                >
                  <div>
                    <h2 class="text-lg font-semibold">
                      {{
                        workspaceTab === "update"
                          ? "Update Existing Records"
                          : "Create New Records"
                      }}
                    </h2>
                    <p class="text-sm text-muted-foreground">
                      {{
                        workspaceTab === "update"
                          ? "Use exported IDs to update existing records safely."
                          : "Import new rows from a spreadsheet template or Google Sheets."
                      }}
                    </p>
                  </div>
                  <UTabs
                    v-model="sourceMode"
                    :items="sourceItems"
                    variant="pill"
                    color="neutral"
                    :content="false"
                  />
                </div>

                <div v-if="sourceMode === 'file'" class="space-y-3">
                  <div>
                    <h3 class="text-sm font-medium">Upload CSV or XLSX</h3>
                    <p class="text-sm text-muted-foreground">
                      Keep the column names aligned with the template.
                    </p>
                  </div>

                  <UFileUpload
                    v-model="fileUploadModel"
                    accept=".csv,.xlsx"
                    icon="i-lucide-file-up"
                    label="Drop file here or click to browse"
                    description="CSV or XLSX only"
                    :multiple="false"
                    class="w-full"
                    @update:model-value="setSelectedFile"
                  />
                </div>

                <div v-else class="space-y-3">
                  <div>
                    <h3 class="text-sm font-medium">Google Sheets URL</h3>
                    <p class="text-sm text-muted-foreground">
                      Paste a valid Google Sheets URL with accessible data.
                    </p>
                  </div>

                  <UInput
                    v-model="sheetsUrl"
                    placeholder="https://docs.google.com/spreadsheets/..."
                    icon="i-lucide-link"
                    class="w-full"
                  />
                </div>

                <div class="flex flex-wrap gap-3 pt-2">
                  <UButton :loading="validating" @click="runValidation">
                    Validate
                  </UButton>
                  <UButton
                    color="primary"
                    :loading="importing"
                    :disabled="
                      !validationResults?.valid ||
                      validationMode !== currentMode
                    "
                    @click="runImportAction"
                  >
                    {{ primaryActionLabel }}
                  </UButton>
                  <UButton variant="outline" @click="resetSourceInputs">
                    Reset
                  </UButton>
                </div>
              </div>
              <div class="lg:col-span-3">
                <UAlert
                  color="neutral"
                  variant="subtle"
                  icon="i-lucide-lightbulb"
                  title="How to use this"
                >
                  <template #description>
                    <div class="text-sm text-muted-foreground">
                      <p>
                        <strong>Import:</strong> creates new records and skips
                        duplicates when the title field already exists.
                      </p>
                      <p>
                        <strong>Update:</strong> requires the `id` column from
                        an exported file to match existing records.
                      </p>
                      <p>
                        <strong>Tip:</strong> export first, edit the rows you
                        need, then upload the file in Update mode.
                      </p>
                    </div>
                  </template>
                </UAlert>
              </div>
            </div>

            <div v-if="validationResults" class="space-y-4">
              <UAlert
                v-if="validationResults.valid"
                color="success"
                variant="subtle"
                icon="i-lucide-check-circle"
                :title="`${validationResults.rows || 0} row(s) validated successfully`"
                :description="
                  workspaceTab === 'update'
                    ? 'The selected rows are ready to update existing records.'
                    : 'The selected rows are ready to create new records.'
                "
              />

              <UAlert
                v-else
                color="error"
                variant="subtle"
                icon="i-lucide-alert-circle"
                title="Validation errors found"
                description="Fix the row errors below before continuing."
              />

              <UAlert
                v-if="validationResults.warnings?.length"
                color="warning"
                variant="subtle"
                icon="i-lucide-triangle-alert"
              >
                <template #title>Warnings</template>
                <template #description>
                  <div class="space-y-1">
                    <p
                      v-for="warning in validationResults.warnings"
                      :key="warning"
                    >
                      {{ warning }}
                    </p>
                  </div>
                </template>
              </UAlert>

              <div
                v-if="validationResults.errors?.length"
                class="max-h-80 overflow-y-auto rounded-xl border border-accented divide-y divide-accented"
              >
                <div
                  v-for="rowError in validationResults.errors"
                  :key="rowError.row"
                  class="p-4 space-y-2"
                >
                  <div class="text-sm font-semibold">
                    Row {{ rowError.row }}
                  </div>
                  <div class="space-y-1 text-sm text-muted-foreground">
                    <p
                      v-for="error in rowError.errors"
                      :key="`${rowError.row}-${error.field}-${error.message}`"
                    >
                      <strong>{{ error.field }}:</strong> {{ error.message }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="space-y-6 border border-accented rounded-md p-4">
            <div class="grid grid-cols-1 gap-6 lg:grid-cols-8">
              <div class="lg:col-span-5 space-y-5">
                <div>
                  <h2 class="text-lg font-semibold">Export Existing Data</h2>
                  <p class="text-sm text-muted-foreground">
                    Download current records, review them offline, then use the
                    file again for updates.
                  </p>
                </div>

                <div class="flex flex-wrap gap-3">
                  <UButton
                    color="neutral"
                    :loading="exporting"
                    @click="handleExport('xlsx')"
                  >
                    Export XLSX
                  </UButton>
                  <UButton
                    variant="outline"
                    :loading="exporting"
                    @click="handleExport('csv')"
                  >
                    Export CSV
                  </UButton>
                </div>
              </div>
              <div class="lg:col-span-3">
                <UAlert
                  color="neutral"
                  variant="subtle"
                  icon="i-lucide-info"
                  title="Export workflow"
                >
                  <template #description>
                    <div class="space-y-2 text-sm text-muted-foreground">
                      <p>
                        Exported data includes the `id` field so the sheet can
                        be reused for update operations.
                      </p>
                      <p>
                        For the safest workflow: export, edit only the fields
                        you need, then upload in <strong>Update</strong> mode.
                      </p>
                    </div>
                  </template>
                </UAlert>
              </div>
            </div>
          </div>

          <div v-if="validationResults" class="space-y-4">
            <UAlert
              v-if="validationResults.valid"
              color="success"
              variant="subtle"
              icon="i-lucide-check-circle"
              :title="`${validationResults.rows || 0} row(s) validated successfully`"
              :description="
                workspaceTab === 'update'
                  ? 'The selected rows are ready to update existing records.'
                  : 'The selected rows are ready to create new records.'
              "
            />

            <UAlert
              v-else
              color="error"
              variant="subtle"
              icon="i-lucide-alert-circle"
              title="Validation errors found"
              description="Fix the row errors below before continuing."
            />

            <UAlert
              v-if="validationResults.warnings?.length"
              color="warning"
              variant="subtle"
              icon="i-lucide-triangle-alert"
            >
              <template #title>Warnings</template>
              <template #description>
                <div class="space-y-1">
                  <p
                    v-for="warning in validationResults.warnings"
                    :key="warning"
                  >
                    {{ warning }}
                  </p>
                </div>
              </template>
            </UAlert>

            <div
              v-if="validationResults.errors?.length"
              class="max-h-80 overflow-y-auto rounded-xl border border-accented divide-y divide-accented"
            >
              <div
                v-for="rowError in validationResults.errors"
                :key="rowError.row"
                class="p-4 space-y-2"
              >
                <div class="text-sm font-semibold">Row {{ rowError.row }}</div>
                <div class="space-y-1 text-sm text-muted-foreground">
                  <p
                    v-for="error in rowError.errors"
                    :key="`${rowError.row}-${error.field}-${error.message}`"
                  >
                    <strong>{{ error.field }}:</strong> {{ error.message }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </template>
      </UTabs>
    </div>
  </div>
</template>
