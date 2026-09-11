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
