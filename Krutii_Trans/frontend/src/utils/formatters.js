import { format, parseISO, isValid } from 'date-fns'
import { uk } from 'date-fns/locale'

export function formatDate(date, formatStr = 'dd.MM.yyyy') {
  if (!date) return '-'
  const parsed = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(parsed)) return '-'
  return format(parsed, formatStr, { locale: uk })
}

export function formatDateTime(date, formatStr = 'dd.MM.yyyy HH:mm') {
  if (!date) return '-'
  const parsed = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(parsed)) return '-'
  return format(parsed, formatStr, { locale: uk })
}

export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('uk-UA', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value)
}

export function formatCurrency(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat('uk-UA', {
    style: 'currency',
    currency: 'UAH',
    minimumFractionDigits: 2
  }).format(value)
}

export function formatOdometer(value) {
  if (value === null || value === undefined) return '-'
  return `${formatNumber(value)} км`
}

export function formatPhone(phone) {
  if (!phone) return '-'
  // Простий формат: +380 50 123 45 67
  const cleaned = phone.replace(/\D/g, '')
  if (cleaned.length === 12) {
    return `+${cleaned.slice(0, 3)} ${cleaned.slice(3, 5)} ${cleaned.slice(5, 8)} ${cleaned.slice(8, 10)} ${cleaned.slice(10)}`
  }
  return phone
}

export function pluralize(count, forms) {
  // forms = [одна, дві-чотири, багато]
  // Приклад: pluralize(5, ['день', 'дні', 'днів'])
  const cases = [2, 0, 1, 1, 1, 2]
  const idx = count % 100 > 4 && count % 100 < 20
    ? 2
    : cases[Math.min(count % 10, 5)]
  return forms[idx]
}

export function timeAgo(date) {
  if (!date) return ''

  const parsed = typeof date === 'string' ? parseISO(date) : date
  if (!isValid(parsed)) return ''

  const now = new Date()
  const diff = now - parsed
  const seconds = Math.floor(diff / 1000)
  const minutes = Math.floor(seconds / 60)
  const hours = Math.floor(minutes / 60)
  const days = Math.floor(hours / 24)

  if (days > 0) {
    return `${days} ${pluralize(days, ['день', 'дні', 'днів'])} тому`
  }
  if (hours > 0) {
    return `${hours} ${pluralize(hours, ['година', 'години', 'годин'])} тому`
  }
  if (minutes > 0) {
    return `${minutes} ${pluralize(minutes, ['хвилина', 'хвилини', 'хвилин'])} тому`
  }
  return 'Щойно'
}
