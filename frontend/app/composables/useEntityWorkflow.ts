/**
 * useEntityWorkflow
 * =================
 * Manages all workflow state and transitions for an entity record on the form page.
 * Wraps postWorkflowAction from useApi — do not call workflow API directly from pages.
 *
 * Handles:
 *  - Current workflow state resolution (slug normalization)
 *  - Fetching available transitions for the current state
 *  - Executing transitions with optimistic loading
 *  - Computed UI visibility flags (button, skeleton, badge)
 *  - Dropdown menu items for the workflow button
 *  - Backend-driven workflow progress modal state + loader
 *
 * Usage:
 *   const { workflowActions, workflowLoading, currentWorkflowStateLabel,
 *           workflowMenuItems, showWorkflowButton, showWorkflowButtonSkeleton,
 *           showWorkflowBadge, isWorkflowDisabled, loadWorkflowTransitions }
 *     = useEntityWorkflow(entityName, recordId, formData, entityMeta,
 *                         permissions, permissionsLoading, isNew, saving,
 *                         loadData, loadRelated)
 */
import type { Ref, ComputedRef } from "vue";
import type { WorkflowAction, EntityMeta, WorkflowProgressResponse } from "~/composables/useApiTypes";

export function useEntityWorkflow(
  entityName: ComputedRef<string>,
  recordId: ComputedRef<string>,
  formData: Ref<Record<string, any>>,
  entityMeta: Ref<EntityMeta | null>,
  permissions: Ref<Record<string, boolean> | null>,
  permissionsLoading: Ref<boolean>,
  isNew: ComputedRef<boolean>,
  saving: Ref<boolean>,
  loadData: () => Promise<void>,
  loadRelated: () => Promise<void>,
) {
  const { postWorkflowAction, getWorkflowTransitions, getWorkflowProgress } = useApi();
  const toast = useToast();

  const workflowActions = ref<WorkflowAction[]>([]);
  const workflowLoading = ref(false);
  const workflowProgressLoading = ref(false);
  const workflowProgressOpen = ref(false);
  const workflowProgress = ref<WorkflowProgressResponse | null>(null);

  const workflowMeta = computed(() => (entityMeta.value as any)?.workflow);

  /**
   * Normalizes a raw workflow_state value to the canonical slug
   * using case-insensitive matching against the workflow state definitions.
   */
  const normalizeWorkflowState = (state: string | null | undefined): string | null => {
    if (!state) return null;
    const wf = workflowMeta.value;
    const states = Array.isArray(wf?.states) ? wf.states : [];
    const s = String(state);
    const direct = states.find((x: any) => x?.slug === s);
    if (direct?.slug) return String(direct.slug);
    const lower = s.toLowerCase();
    const bySlugLower = states.find(
      (x: any) => String(x?.slug || "").toLowerCase() === lower,
    );
    if (bySlugLower?.slug) return String(bySlugLower.slug);
    const byLabelLower = states.find(
      (x: any) => String(x?.label || "").toLowerCase() === lower,
    );
    if (byLabelLower?.slug) return String(byLabelLower.slug);
    return s;
  };

  const currentWorkflowState = computed((): string | null => {
    const v = formData.value?.workflow_state;
    if (v) return normalizeWorkflowState(String(v));
    return normalizeWorkflowState(
      workflowMeta.value?.initial_state ||
        workflowMeta.value?.default_state ||
        null,
    );
  });

  const currentWorkflowStateLabel = computed((): string => {
    const wf = workflowMeta.value;
    const slug = currentWorkflowState.value;
    if (!wf?.enabled || !slug) return "";
    const states = Array.isArray(wf.states) ? wf.states : [];
    const match = states.find((s: any) => s?.slug === slug);
    return match?.label ? String(match.label) : String(slug);
  });

  const currentWorkflowStateColor = computed((): "primary" | "secondary" | "success" | "info" | "warning" | "error" | "neutral" => {
    const wf = workflowMeta.value;
    const slug = currentWorkflowState.value;
    if (!wf?.enabled || !slug) return "neutral";
    const states = Array.isArray(wf.states) ? wf.states : [];
    const match = states.find((s: any) => s?.slug === slug);
    const color = match?.color || "neutral";
    // Ensure it's a valid Nuxt UI color
    const validColors = ["primary", "secondary", "success", "info", "warning", "error", "neutral"];
    return validColors.includes(color) ? color as any : "neutral";
  });

  /**
   * Fetches available workflow transitions for the current state.
   * Called after loadData so transitions reflect the latest state.
   */
  const loadWorkflowTransitions = async (): Promise<void> => {
    if (!workflowMeta.value?.enabled) {
      workflowLoading.value = false;
      return;
    }
    workflowLoading.value = true;
    const currentState = formData.value?.workflow_state
      ? String(formData.value.workflow_state)
      : null;
    try {
      const wfRes = await getWorkflowTransitions(entityName.value, currentState);
      if (wfRes.status === "success") {
        workflowActions.value = (wfRes.data || []) as any;
      }
    } catch {
      workflowActions.value = [];
    } finally {
      workflowLoading.value = false;
    }
  };

  const loadWorkflowProgress = async (): Promise<void> => {
    if (isNew.value || !workflowMeta.value?.enabled) return;
    workflowProgressLoading.value = true;
    try {
      const response = await getWorkflowProgress(entityName.value, recordId.value);
      if (response.status === "success") {
        workflowProgress.value = response.data || null;
      }
    } catch (err: any) {
      workflowProgress.value = null;
      if (err?.message) {
        toast.add({ title: err.message, color: "error", type: "foreground" });
      }
    } finally {
      workflowProgressLoading.value = false;
    }
  };

  const openWorkflowProgress = async (): Promise<void> => {
    workflowProgressOpen.value = true;
    await loadWorkflowProgress();
  };

  /**
   * Executes a workflow transition by slug.
   * Reloads both the record data and related tabs after success.
   */
  const handleWorkflowTransition = async (
    actionSlug: string,
  ): Promise<void> => {
    if (saving.value) return;
    try {
      saving.value = true;
      const response = await postWorkflowAction(
        entityName.value,
        recordId.value,
        actionSlug,
      );
      if (response.status === "success") {
        if (response.message) {
          toast.add({ title: response.message, color: "success", type: "foreground" });
        }
        await loadData();
        await loadRelated();
        if (workflowProgressOpen.value) {
          await loadWorkflowProgress();
        }
      } else {
        if (response.message) {
          toast.add({ title: response.message, color: "error", type: "foreground" });
        }
      }
    } catch (err: any) {
      if (err?.message) {
        toast.add({ title: err.message, color: "error", type: "foreground" });
      }
    } finally {
      saving.value = false;
    }
  };

  /**
   * Dropdown items for the workflow button — one item per available transition.
   * Returns [] when the entity has no workflow or no available transitions.
   */
  const workflowMenuItems = computed(() => {
    if (isNew.value) return [];
    const wf = workflowMeta.value;
    if (!wf?.enabled) return [];
    const actions = workflowActions.value || [];
    if (!actions.length) return [];
    const items = actions.map((action: any) => ({
      label: action.action_label || action.action_slug,
      onSelect: () => handleWorkflowTransition(action.action_slug),
    }));
    return items.length ? [items] : [];
  });

  // UI visibility flags

  const showWorkflowButton = computed(() => {
    if (permissionsLoading.value) return false;
    const perms = permissions.value;
    const wf = workflowMeta.value;
    return (
      !isNew.value &&
      !!wf?.enabled &&
      wf?.show_actions !== false &&
      perms?.can_update !== false
    );
  });

  const showWorkflowButtonSkeleton = computed(() => {
    const wf = workflowMeta.value;
    return (
      !isNew.value &&
      !!wf?.enabled &&
      wf?.show_actions !== false &&
      (workflowLoading.value || permissionsLoading.value)
    );
  });

  const showWorkflowBadge = computed(() => {
    const wf = workflowMeta.value;
    return (
      !isNew.value &&
      !!wf?.enabled &&
      wf?.show_actions === false &&
      !!formData.value?.workflow_state
    );
  });

  const isWorkflowDisabled = computed(
    () => workflowLoading.value || workflowActions.value.length === 0,
  );

  const showWorkflowProgressButton = computed(() => {
    const wf = workflowMeta.value;
    return !isNew.value && !!wf?.enabled;
  });

  return {
    workflowActions,
    workflowLoading,
    workflowProgressLoading,
    workflowProgressOpen,
    workflowProgress,
    workflowMeta,
    currentWorkflowState,
    currentWorkflowStateLabel,
    currentWorkflowStateColor,
    workflowMenuItems,
    showWorkflowButton,
    showWorkflowButtonSkeleton,
    showWorkflowBadge,
    showWorkflowProgressButton,
    isWorkflowDisabled,
    loadWorkflowTransitions,
    loadWorkflowProgress,
    openWorkflowProgress,
    handleWorkflowTransition,
  };
}
