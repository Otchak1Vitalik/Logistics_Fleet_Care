import { tr } from '../i18n'
/**
 * Генерація попереднього перегляду номера документа (клієнтська сторона)
 */

const DOC_SERIES = {
  waybill: tr("ПЛ"),
  fault: tr("НС"),
  repair: tr("РМ"),
  fuel_invoice: tr("НП")
}

export function previewDocNumber(docType) {
  const series = DOC_SERIES[docType] || 'XX'
  return `${series}-******`
}

export function parseDocNumber(docNumber) {
  if (!docNumber || !docNumber.includes('-')) {
    return { series: null, number: null }
  }

  const [series, number] = docNumber.split('-')
  return { series, number }
}

export function getDocTypeLabel(docType) {
  const labels = {
    waybill: tr("Путівка"),
    fault: tr("Несправність"),
    repair: tr("Ремонт"),
    fuel_invoice: tr("Паливна накладна")
  }
  return labels[docType] || docType
}
