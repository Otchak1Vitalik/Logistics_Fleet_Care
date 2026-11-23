import { format, parseISO, isValid } from 'date-fns'
import { uk, enUS } from 'date-fns/locale'
import { tr, lang } from '../i18n'

const dateLocale = lang === 'en' ? enUS : uk
const numberLocale = lang === 'en' ? 'en-US' : 'uk-UA'

// Сервер повертає дати як у форматі ISO, так і у форматі HTTP-date
// ("Wed, 22 Nov 2026 00:00:00 GMT"), тому розбираємо обидва варіанти
function parseDate(date) {
  if (typeof date !== 'string') return date
  const iso = parseISO(date)
  return isValid(iso) ? iso : new Date(date)
}

export function formatDate(date, formatStr = 'dd.MM.yyyy') {
  if (!date) return '-'
  const parsed = parseDate(date)
  if (!isValid(parsed)) return '-'
  return format(parsed, formatStr, { locale: dateLocale })
}

export function formatDateTime(date, formatStr = 'dd.MM.yyyy HH:mm') {
  if (!date) return '-'
  const parsed = parseDate(date)
  if (!isValid(parsed)) return '-'
  return format(parsed, formatStr, { locale: dateLocale })
}

export function formatNumber(value, decimals = 0) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat(numberLocale, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value)
}

export function formatCurrency(value) {
  if (value === null || value === undefined) return '-'
  return new Intl.NumberFormat(numberLocale, {
    style: 'currency',
    currency: 'UAH',
    minimumFractionDigits: 2
  }).format(value)
}

export function formatOdometer(value) {
  if (value === null || value === undefined) return '-'
  return tr("{0} км", formatNumber(value))
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
  // Приклад: pluralize(5, [tr("день"), tr("дні"), tr("днів")])
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
    return tr("{0} {1} тому", days, pluralize(days, [tr("день"), tr("дні"), tr("днів")]))
  }
  if (hours > 0) {
    return tr("{0} {1} тому", hours, pluralize(hours, [tr("година"), tr("години"), tr("годин")]))
  }
  if (minutes > 0) {
    return tr("{0} {1} тому", minutes, pluralize(minutes, [tr("хвилина"), tr("хвилини"), tr("хвилин")]))
  }
  return tr("Щойно")
}
