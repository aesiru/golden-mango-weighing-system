import { useApi } from "./useApi";

export type DiagramLayout = {
  id: string;
  name: string;
  filters: { system?: string | null; expandedLocations?: string[] };
  created_at: string;
  updated_at: string;
};

export const useDiagramLayouts = () => {
  const {
    getDiagramLayouts,
    createDiagramLayout,
    updateDiagramLayout,
    deleteDiagramLayout,
  } = useApi();

  const layouts = ref<DiagramLayout[]>([]);
  const loading = ref(false);

  const fetchLayouts = async () => {
    loading.value = true;
    try {
      const response = await getDiagramLayouts();
      layouts.value = response.layouts || [];
    } finally {
      loading.value = false;
    }
  };

  const saveLayout = async (
    name: string,
    filters: { system?: string | null; expandedLocations?: string[] },
  ) => {
    const response = await createDiagramLayout({ name, filters });
    layouts.value.push(response.layout);
    return response.layout as DiagramLayout;
  };

  const renameLayout = async (id: string, name: string) => {
    const response = await updateDiagramLayout(id, { name });
    const idx = layouts.value.findIndex((l) => l.id === id);
    if (idx !== -1) layouts.value[idx] = response.layout;
    return response.layout as DiagramLayout;
  };

  const updateLayoutFilters = async (
    id: string,
    filters: { system?: string | null; expandedLocations?: string[] },
  ) => {
    const response = await updateDiagramLayout(id, { filters });
    const idx = layouts.value.findIndex((l) => l.id === id);
    if (idx !== -1) layouts.value[idx] = response.layout;
    return response.layout as DiagramLayout;
  };

  const removeLayout = async (id: string) => {
    await deleteDiagramLayout(id);
    layouts.value = layouts.value.filter((l) => l.id !== id);
  };

  return {
    layouts,
    loading,
    fetchLayouts,
    saveLayout,
    renameLayout,
    updateLayoutFilters,
    removeLayout,
  };
};
