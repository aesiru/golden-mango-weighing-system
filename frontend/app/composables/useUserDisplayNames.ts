/**
 * useUserDisplayNames - Resolve user IDs to display names
 * ======================================================
 * Composable for resolving stored user.id values into human-readable display names.
 * Used for displaying created_by and last_modified_by fields in the UI.
 *
 * This composable provides:
 * - Batch resolution of user IDs to display names (full_name or username)
 * - Caching to avoid repeated API calls
 * - Simple interface for Vue components
 */

import { useApiFetch } from './useApiFetch'

interface UserDisplayNamesMap {
  [userId: string]: string
}

const displayNamesCache = new Map<string, UserDisplayNamesMap>()

export const useUserDisplayNames = () => {
  const { apiFetch } = useApiFetch()

  /**
   * Resolve user IDs to display names
   * @param userIds - Array of user IDs to resolve
   * @returns Promise mapping user IDs to display names
   */
  const resolveUserDisplayNames = async (userIds: string[]): Promise<UserDisplayNamesMap> => {
    if (!userIds || userIds.length === 0) {
      return {}
    }

    // Filter out null/undefined/empty values
    const validIds = userIds.filter(id => id && id.trim() !== '')
    if (validIds.length === 0) {
      return {}
    }

    // Create cache key from sorted IDs
    const cacheKey = validIds.sort().join(',')

    // Check cache
    if (displayNamesCache.has(cacheKey)) {
      return displayNamesCache.get(cacheKey)!
    }

    try {
      const response = await apiFetch('/system/users/resolve-display-names', {
        method: 'GET',
        params: {
          user_ids: validIds.join(',')
        }
      })

      if (response.status === 'success' && response.data) {
        // Cache the result
        displayNamesCache.set(cacheKey, response.data)
        return response.data
      }

      // Fallback: return IDs as-is
      const fallback: UserDisplayNamesMap = {}
      validIds.forEach(id => {
        fallback[id] = id
      })
      return fallback
    } catch (error) {
      console.error('Failed to resolve user display names:', error)
      // Fallback: return IDs as-is
      const fallback: UserDisplayNamesMap = {}
      validIds.forEach(id => {
        fallback[id] = id
      })
      return fallback
    }
  }

  /**
   * Resolve a single user ID to display name
   * @param userId - User ID to resolve
   * @returns Promise with display name or the ID if not found
   */
  const resolveSingleUserDisplayName = async (userId: string): Promise<string> => {
    if (!userId || userId.trim() === '') {
      return userId
    }

    const map = await resolveUserDisplayNames([userId])
    return map[userId] || userId
  }

  /**
   * Clear the display names cache
   * Call this when user data might have changed
   */
  const clearCache = () => {
    displayNamesCache.clear()
  }

  return {
    resolveUserDisplayNames,
    resolveSingleUserDisplayName,
    clearCache
  }
}
