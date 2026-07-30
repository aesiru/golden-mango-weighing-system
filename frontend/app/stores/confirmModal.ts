import { defineStore } from 'pinia'

export interface ConfirmModalConfig {
  title: string
  message: string
  confirmLabel?: string
  cancelLabel?: string
  confirmColor?: string
  onConfirm: () => void | Promise<void>
  onCancel?: () => void
}

export const useConfirmModalStore = defineStore('confirmModal', {
  state: () => ({
    isOpen: false,
    config: null as ConfirmModalConfig | null,
    loading: false,
  }),

  actions: {
    open(modalConfig: ConfirmModalConfig) {
      this.config = modalConfig
      this.isOpen = true
      this.loading = false
    },

    close() {
      this.isOpen = false
      this.loading = false
      setTimeout(() => {
        this.config = null
      }, 200)
    },

    async confirm() {
      if (!this.config) return
      this.loading = true
      try {
        await this.config.onConfirm()
        this.close()
      } catch (error) {
        console.error('Confirm action failed:', error)
        this.loading = false
      }
    },

    cancel() {
      if (this.config?.onCancel) {
        this.config.onCancel()
      }
      this.close()
    },
  },
})
