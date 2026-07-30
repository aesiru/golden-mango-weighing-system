/**
 * Convert a date string to a relative time string.
 * Examples: "1m", "5m", "2h", "3d", "1w", "2M", "1y"
 */
export function timeAgo(dateStr: string | null | undefined): string {
  if (!dateStr) return '-'

  // Check if the date string has timezone info
  const hasTimezone = dateStr.includes('Z') || dateStr.includes('+00:00') || dateStr.includes('.000Z')
  
  let date: Date
  
  if (hasTimezone) {
    // Timezone-aware date: parse normally
    date = new Date(dateStr)
  } else {
    // Naive UTC date: append 'Z' to treat it as UTC
    date = new Date(dateStr + 'Z')
  }
  
  if (isNaN(date.getTime())) return '-'

  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSec = Math.floor(diffMs / 1000)
  const diffMin = Math.floor(diffSec / 60)
  const diffHr = Math.floor(diffMin / 60)
  const diffDay = Math.floor(diffHr / 24)
  const diffWeek = Math.floor(diffDay / 7)
  const diffMonth = Math.floor(diffDay / 30)
  const diffYear = Math.floor(diffDay / 365)

  if (diffSec < 60) return 'just now'
  if (diffMin < 60) return `${diffMin}m`
  if (diffHr < 24) return `${diffHr}h`
  if (diffDay < 7) return `${diffDay}d`
  if (diffWeek < 5) return `${diffWeek}w`
  if (diffMonth < 12) return `${diffMonth}M`
  return `${diffYear}y`
}
