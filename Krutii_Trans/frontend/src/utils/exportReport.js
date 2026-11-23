// Експорт табличних звітів у файл CSV, який коректно відкривається в Excel.
// - роздільник «;» і десяткова кома - стандарт Excel з українськими регіональними налаштуваннями;
// - на початку файлу BOM (\uFEFF), щоб Excel правильно розпізнав кирилицю (UTF-8).

function escapeCell(value) {
  if (value === null || value === undefined) return ''
  // Дробові числа - з комою, як очікує Excel з українськими регіональними налаштуваннями
  if (typeof value === 'number' && !Number.isInteger(value)) {
    return String(value).replace('.', ',')
  }
  let text = String(value)
  if (/[";\n\r]/.test(text)) {
    text = '"' + text.replace(/"/g, '""') + '"'
  }
  return text
}

export function buildCsv(headers, rows) {
  const lines = [headers.map(escapeCell).join(';')]
  rows.forEach((row) => lines.push(row.map(escapeCell).join(';')))
  return '\uFEFF' + lines.join('\r\n')
}

export function downloadCsv(filename, headers, rows) {
  const blob = new Blob([buildCsv(headers, rows)], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename.endsWith('.csv') ? filename : `${filename}.csv`
  document.body.appendChild(link)
  link.click()
  link.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

// Дата для назви файлу: 2026-11-22
export function fileDate(date = new Date()) {
  const pad = (n) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`
}
