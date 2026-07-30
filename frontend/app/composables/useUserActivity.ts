import { useApiFetch } from "~/composables/useApiFetch";

export interface UserActivity {
  id: string;
  activity_type: string;
  entity_name?: string;
  page_path?: string;
  page_label?: string;
  visit_count: number;
  score: number;
  last_visited_at?: string;
}

export interface FrequentEntity {
  entity_name: string;
  page_label: string;
  visit_count: number;
  score: number;
  last_visited: string;
}

export interface FrequentPage {
  page_path: string;
  page_label: string;
  visit_count: number;
  score: number;
  last_visited: string;
}

interface QueuedActivity {
  activity_type: "entity_view" | "page_visit" | "quick_create" | "admin_action";
  entity_name?: string;
  page_path?: string;
  page_label?: string;
}

// Batch tracking configuration
const BATCH_SIZE = 20;
const BATCH_INTERVAL_MS = 5 * 60 * 1000; // 5 minutes

export const useUserActivity = () => {
  const { apiFetch, baseURL } = useApiFetch();
  const config = useRuntimeConfig();

  // Activity queue for batch tracking
  const activityQueue = ref<QueuedActivity[]>([]);
  const isFlushing = ref(false);

  // Deduplicate activities by key (activity_type + entity_name + page_path)
  const deduplicateQueue = () => {
    const seen = new Set<string>();
    const deduplicated: QueuedActivity[] = [];
    
    for (const activity of activityQueue.value) {
      const key = `${activity.activity_type}|${activity.entity_name || ''}|${activity.page_path || ''}`;
      if (!seen.has(key)) {
        seen.add(key);
        deduplicated.push(activity);
      }
    }
    
    activityQueue.value = deduplicated;
  };

  // Send batch of activities to backend
  const flushQueue = async () => {
    if (isFlushing.value || activityQueue.value.length === 0) return;
    
    isFlushing.value = true;
    
    try {
      deduplicateQueue();
      
      if (activityQueue.value.length === 0) {
        isFlushing.value = false;
        return;
      }

      await apiFetch("/features/user-activity/batch", {
        method: "POST",
        body: {
          activities: activityQueue.value,
        },
      });
      
      activityQueue.value = [];
    } catch (error) {
      // Silently fail - keep queue for next attempt
    } finally {
      isFlushing.value = false;
    }
  };

  // Timer-based flush
  let flushTimer: NodeJS.Timeout | null = null;
  
  const startFlushTimer = () => {
    if (flushTimer) clearInterval(flushTimer);
    flushTimer = setInterval(() => {
      flushQueue();
    }, BATCH_INTERVAL_MS);
  };

  // Track activity (adds to queue instead of sending immediately)
  const trackActivity = (
    activityType: "entity_view" | "page_visit" | "quick_create" | "admin_action",
    options: {
      entityName?: string;
      pagePath?: string;
      pageLabel?: string;
    } = {}
  ) => {
    // Add to queue
    activityQueue.value.push({
      activity_type: activityType,
      entity_name: options.entityName,
      page_path: options.pagePath,
      page_label: options.pageLabel,
    });

    // Flush if queue reaches batch size
    if (activityQueue.value.length >= BATCH_SIZE) {
      flushQueue();
    }
  };

  // Initialize timer on client-side
  if (typeof window !== 'undefined') {
    onMounted(() => {
      startFlushTimer();
      // Flush on page unload
      window.addEventListener('beforeunload', flushQueue);
    });
    
    onUnmounted(() => {
      if (flushTimer) clearInterval(flushTimer);
      window.removeEventListener('beforeunload', flushQueue);
      flushQueue();
    });
  }

  const getFrequentEntities = async (limit: number = 5, daysAgo: number = 30): Promise<FrequentEntity[]> => {
    try {
      // Flush any pending activities before fetching
      await flushQueue();
      
      const response = await apiFetch<{ status: string; data: FrequentEntity[] }>(
        `/features/user-activity/frequent-entities?limit=${limit}&days_ago=${daysAgo}`
      );
      return response.data || [];
    } catch (error) {
      return [];
    }
  };

  const getFrequentPages = async (limit: number = 5, daysAgo: number = 30): Promise<FrequentPage[]> => {
    try {
      // Flush any pending activities before fetching
      await flushQueue();
      
      const response = await apiFetch<{ status: string; data: FrequentPage[] }>(
        `/features/user-activity/frequent-pages?limit=${limit}&days_ago=${daysAgo}`
      );
      return response.data || [];
    } catch (error) {
      return [];
    }
  };

  const getAllActivities = async (
    activityType?: string,
    limit: number = 10,
    daysAgo?: number
  ): Promise<UserActivity[]> => {
    try {
      // Flush any pending activities before fetching
      await flushQueue();
      
      const params = new URLSearchParams({
        limit: limit.toString(),
      });
      if (activityType) params.append("activity_type", activityType);
      if (daysAgo) params.append("days_ago", daysAgo.toString());

      const response = await apiFetch<{ status: string; data: UserActivity[] }>(
        `/features/user-activity/all-activities?${params.toString()}`
      );
      return response.data || [];
    } catch (error) {
      return [];
    }
  };

  const getRecentRecords = async (limit: number = 10): Promise<any[]> => {
    try {
      const response = await apiFetch<{ status: string; data: any[] }>(
        `/features/user-activity/recent-records?limit=${limit}`
      );
      return response.data || [];
    } catch (error) {
      return [];
    }
  };

  const getHomeData = async (
    entitiesLimit: number = 5,
    pagesLimit: number = 5,
    recordsLimit: number = 10,
    daysAgo: number = 30
  ): Promise<{
    frequentEntities: any[];
    frequentPages: any[];
    recentRecords: any[];
    entityIcons: Record<string, string>;
  }> => {
    try {
      await flushQueue();
      
      const params = new URLSearchParams({
        entities_limit: entitiesLimit.toString(),
        pages_limit: pagesLimit.toString(),
        records_limit: recordsLimit.toString(),
        days_ago: daysAgo.toString(),
      });
      
      const response = await apiFetch<{
        status: string;
        data: {
          frequent_entities: any[];
          frequent_pages: any[];
          recent_records: any[];
          entity_icons: Record<string, string>;
        };
      }>(`/features/user-activity/home-data?${params.toString()}`);
      
      return {
        frequentEntities: response.data.frequent_entities || [],
        frequentPages: response.data.frequent_pages || [],
        recentRecords: response.data.recent_records || [],
        entityIcons: response.data.entity_icons || {},
      };
    } catch (error) {
      return {
        frequentEntities: [],
        frequentPages: [],
        recentRecords: [],
        entityIcons: {},
      };
    }
  };

  return {
    trackActivity,
    getFrequentEntities,
    getFrequentPages,
    getAllActivities,
    getRecentRecords,
    getHomeData,
    flushQueue,
  };
};
