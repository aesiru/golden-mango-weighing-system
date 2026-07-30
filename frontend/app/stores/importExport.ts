import { defineStore } from "pinia";
import type { ImportValidationResult } from "~/composables/useApiTypes";

export type ImportMethod = "file" | "url";

export const useImportExportStore = defineStore("importExport", {
  state: () => ({
    selectedEntity: "",
    importMethod: "file" as ImportMethod,
    file: null as File | null,
    sheetsUrl: "",
    validationResults: null as ImportValidationResult | null,
    validating: false,
    importing: false,
    exporting: false,
    error: "",
  }),
});
