/**
 * Генерація попереднього перегляду номера документа (клієнтська сторона)
 */

const DOC_SERIES = {
  waybill: 'ПЛ',
  fault: 'НС',
  repair: 'РМ',
  fuel_invoice: 'НП'
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
    waybill: 'Путівка',
    fault: 'Несправність',
    repair: 'Ремонт',
    fuel_invoice: 'Паливна накладна'
  }
  return labels[docType] || docType
}
