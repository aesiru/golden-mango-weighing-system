import { defineStore } from 'pinia'
import { useEntityApi } from '~/composables/useEntityApi'

interface EntityModalState {
  isOpen: boolean
  entity: string | null
  prefillData: Record<string, any>
  callback?: (result: any) => void
}

export const useEntityModalStore = defineStore('entityModal', {
  state: (): EntityModalState => ({
    isOpen: false,
    entity: null,
    prefillData: {},
    callback: undefined
  }),
  
  actions: {
    open(entity: string, prefillData: Record<string, any> = {}, callback?: (result: any) => void) {
      this.isOpen = true
      this.entity = entity
      this.prefillData = prefillData
      this.callback = callback
    },
    
    close() {
      this.isOpen = false
      this.entity = null
      this.prefillData = {}
      this.callback = undefined
    },
    
    async submit(formData: Record<string, any>) {
      if (!this.entity) return
      
      const { postEntityAction } = useEntityApi()
      
      const response = await postEntityAction(this.entity, {
        action: 'create',
        data: {
          ...this.prefillData,
          ...formData
        }
      })
      
      if (response.status === 'success') {
        if (this.callback) {
          this.callback(response)
        }
        this.close()
      }
      
      return response
    }
  }
})
