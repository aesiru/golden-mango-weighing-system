import type { ConfirmDialogOptions } from "~/composables/useConfirmDialog";

interface DeleteDialogOptions {
  entityName: string;
  itemName?: string;
  confirmLabel?: string;
  cancelLabel?: string;
}

export const useDeleteDialog = () => {
  const confirm = useConfirmDialog();

  return (options: DeleteDialogOptions): Promise<boolean> => {
    const description = options.itemName
      ? `Are you sure you want to delete ${options.entityName} ${options.itemName}? This action cannot be undone.`
      : `Are you sure you want to delete ${options.entityName}? This action cannot be undone.`;

    const config: ConfirmDialogOptions = {
      title: `Delete ${options.entityName}`,
      description,
      confirmLabel: options.confirmLabel || "Delete",
      cancelLabel: options.cancelLabel || "Cancel",
      confirmColor: "error",
    };

    return confirm(config);
  };
};
