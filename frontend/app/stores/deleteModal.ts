import { defineStore } from 'pinia';

export interface DeleteModalConfig {
  entityName: string;
  itemName: string;
  itemId: string;
  onConfirm: () => Promise<void>;
}

export const useDeleteModalStore = defineStore('deleteModal', {
  state: () => ({
    isOpen: false,
    config: null as DeleteModalConfig | null,
    loading: false,
  }),
  
  actions: {
    open(modalConfig: DeleteModalConfig) {
      this.config = modalConfig;
      this.isOpen = true;
      this.loading = false;
    },
    
    close() {
      this.isOpen = false;
      this.loading = false;
      setTimeout(() => {
        this.config = null;
      }, 200);
    },
    
    async confirm() {
      if (!this.config) return;
      this.loading = true;

      try {
        await this.config.onConfirm();
        this.close();
      } catch (error) {
        console.error('Delete failed:', error);
        this.loading = false;
      }
    },
  },
});
