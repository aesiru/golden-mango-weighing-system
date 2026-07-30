/**
 * usePrintPreview Composable
 * ===========================
 * Handles print preview and PDF download for entity form pages.
 * Extracts print logic from [id].vue to keep the form page lean.
 */
export function usePrintPreview() {
  const { apiFetch, baseURL } = useApiFetch()
  const toast = useToast()

  const previewHtml = ref('')
  const showPreview = ref(false)
  const loading = ref(false)

  /**
   * Fetch the print HTML for an entity record and open the preview modal.
   */
  const openPreview = async (entityName: string, recordId: string) => {
    loading.value = true
    try {
      const html = (await apiFetch(
        `${baseURL}/entity/${entityName}/${recordId}/print`,
        { responseType: 'text' } as any,
      )) as string
      previewHtml.value = html
      showPreview.value = true
    } catch (error: any) {
      toast.add({
        title: error.message || 'Failed to load print preview',
        color: 'error',
        type: 'foreground',
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Open the print HTML in a new browser window for direct printing.
   */
  const printDirect = async (entityName: string, recordId: string) => {
    loading.value = true
    try {
      const html = (await apiFetch(
        `${baseURL}/entity/${entityName}/${recordId}/print`,
        { responseType: 'text' } as any,
      )) as string
      const printWindow = window.open('', '_blank')
      if (printWindow) {
        printWindow.document.write(html)
        printWindow.document.close()
        printWindow.focus()
        printWindow.onload = () => printWindow.print()
      }
    } catch (error: any) {
      toast.add({
        title: error.message || 'Print failed',
        color: 'error',
        type: 'foreground',
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Download PDF for an entity record.
   */
  const downloadPdf = async (entityName: string, recordId: string) => {
    loading.value = true
    try {
      const blob = await apiFetch<Blob>(
        `${baseURL}/entity/${entityName}/${recordId}/print/pdf`,
        { method: 'GET', responseType: 'blob' } as any,
      )
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${entityName}_${recordId}_${new Date().toISOString().slice(0, 10)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
      toast.add({ title: 'PDF downloaded', color: 'success', type: 'foreground' })
    } catch (error: any) {
      toast.add({
        title: error.message || 'PDF download failed',
        color: 'error',
        type: 'foreground',
      })
    } finally {
      loading.value = false
    }
  }

  /**
   * Print from the currently loaded preview HTML.
   */
  const printFromPreview = () => {
    if (!previewHtml.value) return
    const printWindow = window.open('', '_blank')
    if (printWindow) {
      printWindow.document.write(previewHtml.value)
      printWindow.document.close()
      printWindow.focus()
      printWindow.onload = () => printWindow.print()
    }
  }

  return {
    previewHtml,
    showPreview,
    loading,
    openPreview,
    printDirect,
    downloadPdf,
    printFromPreview,
  }
}
