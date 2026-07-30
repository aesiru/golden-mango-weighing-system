import { useApiFetch } from "./useApiFetch";
import type { Component } from "vue";

export interface DashboardSummary {
  total: number;
  by_status: Record<string, number>;
  overdue_count?: number;
  activity_summary?: Record<string, Record<string, number>>;
}

export interface RecentRecord {
  id: string;
  display_name: string;
  status: string;
  updated_at: string;
}

export interface WorkOrderDashboard {
  summary: DashboardSummary & {
    overdue_count: number;
    activity_summary: Record<string, Record<string, number>>;
  };
  recent: RecentRecord[];
}

export interface PurchaseRequestDashboard {
  summary: DashboardSummary;
  recent: RecentRecord[];
}

export interface InventorySummary {
  total_items: number;
  low_stock_count: number;
  location_count: number;
}

export interface TopItem {
  item_display_name: string;
  total: number;
  by_location: Record<string, number>;
}

export interface InventoryDashboard {
  summary: InventorySummary;
  top_items: TopItem[];
}

export const STATUS_COLORS = {
  draft: "gray",
  pending: "yellow",
  in_progress: "blue",
  completed: "green",
  rejected: "red",
  overdue: "orange",
  requested: "blue",
  approved: "green",
  closed: "gray",
  // PR-specific states
  pending_review: "yellow",
  pending_approval: "orange",
};

// ---------------------------------------------------------------------------
// Role-Based Dashboard types
// ---------------------------------------------------------------------------

export interface DashboardWidgetConfig {
  readonly: boolean;
}

export interface DashboardWidget<T = Record<string, unknown>> {
  type: string;
  title: string;
  config: DashboardWidgetConfig;
  data: T;
}

export interface DashboardOption {
  key: string;
  label: string;
  description: string;
  icon: string;
}

export interface SelectedDashboard extends DashboardOption {
  widgets: DashboardWidget[];
  stats: DashboardStatConfig[];
  charts: DashboardChartConfig[];
}

export interface DashboardStatConfig {
  title: string;
  icon: string;
  source: string;
  field: string;
  variation?: number;
}

export interface DashboardChartConfig {
  title: string;
  subtitle: string;
  badge_color: "primary" | "info" | "success" | "warning" | "error" | "neutral";
  source: string;
  total_field: string;
  data_field: string;
  preferred_order?: string[];
  custom_data?: boolean;
}

export interface RoleBasedDashboard {
  user_roles: string[];
  generated_at: string;
  allowed_dashboards: DashboardOption[];
  selected_dashboard: SelectedDashboard | null;
}

// Widget data shapes for type-safe access inside widget components
export interface PRStatusSummaryData {
  total: number;
  by_status: Record<string, number>;
  period: string;
  approved_today?: number;
  error?: string;
}

export interface AttentionItem {
  id: string;
  display_name: string;
  status: string;
  [key: string]: unknown;
}

export interface PRAttentionListData {
  items: Array<
    AttentionItem & {
      pr_description: string;
      requestor: string | null;
      date_requested: string | null;
      days_pending: number;
      updated_at: string | null;
    }
  >;
  error?: string;
}

export interface InventorySummaryData {
  total_items: number;
  location_count: number;
  low_stock_count: number;
  error?: string;
}

export interface LowStockItem {
  item_id: string | null;
  item_name: string;
  item_code?: string;
  location: string | null;
  site_code?: string;
  actual_inv: number;
  available_inv: number;
}

export interface InventoryLowStockData {
  items: LowStockItem[];
  threshold: number;
  error?: string;
}

export interface StockCountSummaryData {
  pending_count: number;
  in_progress_count: number;
  total_active: number;
  error?: string;
}

export interface WOSummaryData {
  total: number;
  by_status: Record<string, number>;
  overdue_count: number;
  overdue?: number;
  error?: string;
}

export interface WOAttentionItem extends AttentionItem {
  priority: string | null;
  due_date: string | null;
  days_overdue: number;
  description: string | null;
}

export interface WOAttentionListData {
  items: WOAttentionItem[];
  error?: string;
}

export interface MyWOItem extends AttentionItem {
  priority: string | null;
  due_date: string | null;
  description: string | null;
}

export interface MyWOListData {
  items: MyWOItem[];
  note?: string;
  error?: string;
}

export interface MaintenanceSummaryData {
  by_status: Record<string, number>;
  upcoming_7_days_count: number;
  total?: number;
  upcoming_7_days?: number;
  error?: string;
}

export interface WorkOrderTypeDistributionData {
  total: number;
  by_type: Record<string, number>;
  error?: string;
}

// Widget registry type alias
export type WidgetRegistry = Record<string, Component>;

export const useDashboard = () => {
  const { apiFetch, baseURL } = useApiFetch();

  const getWorkOrderSummary = async () => {
    return apiFetch<WorkOrderDashboard>(
      `${baseURL}/operations/dashboard/work-orders`,
    );
  };

  const getPurchaseRequestSummary = async () => {
    return apiFetch<PurchaseRequestDashboard>(
      `${baseURL}/operations/dashboard/purchase-requests`,
    );
  };

  const getInventorySummary = async () => {
    return apiFetch<InventoryDashboard>(
      `${baseURL}/operations/dashboard/inventory`,
    );
  };

  const getRoleBasedDashboard = async (dashboardKey?: string) => {
    return apiFetch<RoleBasedDashboard>(
      `${baseURL}/operations/dashboard/role-based`,
      dashboardKey
        ? {
            query: {
              dashboard_key: dashboardKey,
            },
          }
        : undefined,
    );
  };

  const getDashboardWidgets = async (
    dashboardKey: string,
    startDate?: Date,
    endDate?: Date,
  ) => {
    const query: Record<string, string> = {};
    if (startDate) {
      // Use local date components to avoid timezone conversion issues
      const year = startDate.getFullYear();
      const month = String(startDate.getMonth() + 1).padStart(2, "0");
      const day = String(startDate.getDate()).padStart(2, "0");
      query.start_date = `${year}-${month}-${day}`;
    }
    if (endDate) {
      // Use local date components to avoid timezone conversion issues
      const year = endDate.getFullYear();
      const month = String(endDate.getMonth() + 1).padStart(2, "0");
      const day = String(endDate.getDate()).padStart(2, "0");
      query.end_date = `${year}-${month}-${day}`;
    }

    return apiFetch<{
      dashboard_key: string;
      widgets: any[];
      generated_at: string;
    }>(
      `${baseURL}/operations/dashboard/widgets/${dashboardKey}`,
      Object.keys(query).length > 0 ? { query } : undefined,
    );
  };

  const getStatusColor = (status?: string | null) => {
    if (!status) return "neutral";
    const normalized = status.toLowerCase().replace(/\s+/g, "_");
    return STATUS_COLORS[normalized as keyof typeof STATUS_COLORS] || "neutral";
  };

  const formatRelativeTime = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60)
      return `${diffMins} minute${diffMins > 1 ? "s" : ""} ago`;
    if (diffHours < 24)
      return `${diffHours} hour${diffHours > 1 ? "s" : ""} ago`;
    return `${diffDays} day${diffDays > 1 ? "s" : ""} ago`;
  };

  return {
    getWorkOrderSummary,
    getPurchaseRequestSummary,
    getInventorySummary,
    getRoleBasedDashboard,
    getDashboardWidgets,
    getStatusColor,
    formatRelativeTime,
  };
};
