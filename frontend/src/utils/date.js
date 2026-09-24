/**
 * Formats a Date as a local YYYY-MM-DD string. Deliberately not
 * `toISOString()`, which converts to UTC first and can shift the date
 * across a day boundary depending on the viewer's timezone.
 */
export function toDateKey(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function todayDateKey() {
  return toDateKey(new Date())
}

/**
 * Parses a 'YYYY-MM-DD' key into a local Date at midnight. Deliberately not
 * `new Date(dateKey)`, which parses as UTC midnight and can shift the date
 * across a day boundary depending on the viewer's timezone -- same reason
 * toDateKey() avoids toISOString().
 */
export function parseDateKey(dateKey) {
  const [year, month, day] = dateKey.split('-').map(Number)
  return new Date(year, month - 1, day)
}

export function addDaysToDateKey(dateKey, days) {
  const date = parseDateKey(dateKey)
  date.setDate(date.getDate() + days)
  return toDateKey(date)
}

/** Monday of the week containing dateKey (ISO-style week start). */
export function startOfWeekDateKey(dateKey) {
  const date = parseDateKey(dateKey)
  const day = date.getDay() // 0 = Sunday ... 6 = Saturday
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  return toDateKey(date)
}

/** Every date key from startKey to endKey, inclusive. */
export function eachDateKeyInRange(startKey, endKey) {
  const end = parseDateKey(endKey)
  const cursor = parseDateKey(startKey)
  const keys = []
  while (cursor <= end) {
    keys.push(toDateKey(cursor))
    cursor.setDate(cursor.getDate() + 1)
  }
  return keys
}

/** "Feb 2 – Feb 8, 2026" (same year) or "Dec 29, 2025 – Jan 4, 2026" (crossing years). */
export function formatWeekRange(startKey, endKey) {
  const start = parseDateKey(startKey)
  const end = parseDateKey(endKey)
  const sameYear = start.getFullYear() === end.getFullYear()

  const startLabel = start.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: sameYear ? undefined : 'numeric'
  })
  const endLabel = end.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
  return `${startLabel} – ${endLabel}`
}
