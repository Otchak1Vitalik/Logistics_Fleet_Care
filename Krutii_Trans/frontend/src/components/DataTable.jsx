import { useMemo, useState } from 'react'
import { tr } from '../i18n'

// Значення клітинки для сортування й пошуку (без оформлення)
function plainValue(row, col) {
  if (col.sortValue) return col.sortValue(row)
  const v = row[col.key]
  if (v && typeof v === 'object') return v.plate_number || v.full_name || v.name || v.number || ''
  return v
}

// Текст рядка для пошуку: значення колонок і поширені вкладені поля
function rowText(row, columns) {
  const parts = columns.map((c) => plainValue(row, c))
  ;['vehicle', 'driver', 'mechanic', 'reporter'].forEach((k) => {
    const o = row[k]
    if (o && typeof o === 'object') parts.push(o.plate_number, o.brand, o.model, o.full_name)
  })
  parts.push(row.brand, row.model, row.number, row.plate_number, row.full_name, row.username, row.article)
  return parts.filter((p) => p !== null && p !== undefined).join(' ').toLowerCase()
}

const DATE_RE = /^\d{4}-\d{2}-\d{2}|^\w{3}, \d{2} \w{3} \d{4}/

function compare(a, b) {
  const empty = (x) => x === null || x === undefined || x === ''
  if (empty(a) && empty(b)) return 0
  if (empty(a)) return 1
  if (empty(b)) return -1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  if (typeof a === 'string' && typeof b === 'string' && DATE_RE.test(a) && DATE_RE.test(b)) {
    return new Date(a) - new Date(b)
  }
  return String(a).localeCompare(String(b), undefined, { numeric: true, sensitivity: 'base' })
}

function DataTable({
  columns,
  data,
  onRowClick,
  emptyMessage = tr("Немає даних"),
  isLoading = false,
  searchable = true,
  sortable = true,
  searchPlaceholder = tr("Пошук..."),
}) {
  const [query, setQuery] = useState('')
  const [sort, setSort] = useState({ key: null, dir: 'asc' })

  const rows = useMemo(() => {
    let list = data || []
    const q = query.trim().toLowerCase()
    if (q) list = list.filter((row) => rowText(row, columns).includes(q))
    if (sort.key) {
      const col = columns.find((c) => c.key === sort.key)
      if (col) {
        list = [...list].sort((a, b) => compare(plainValue(a, col), plainValue(b, col)) * (sort.dir === 'asc' ? 1 : -1))
      }
    }
    return list
  }, [data, columns, query, sort])

  if (isLoading) {
    return (
      <div className="table-loading">
        <div className="loader"></div>
        <span>{tr("Завантаження...")}</span>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return <div className="table-empty">{emptyMessage}</div>
  }

  const toggleSort = (col) => {
    if (!sortable || col.sortable === false) return
    setSort((s) => (s.key !== col.key ? { key: col.key, dir: 'asc' }
      : s.dir === 'asc' ? { key: col.key, dir: 'desc' } : { key: null, dir: 'asc' }))
  }

  return (
    <div className="table-block">
      {searchable && (
        <div className="table-toolbar no-print">
          <input
            type="search"
            className="form-control table-search"
            placeholder={searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            aria-label={searchPlaceholder}
          />
          {query && (
            <span className="table-count">{tr("Знайдено: {0} з {1}", rows.length, data.length)}</span>
          )}
        </div>
      )}
      {rows.length === 0 ? (
        <div className="table-empty">{tr("Нічого не знайдено")}</div>
      ) : (
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                {columns.map((col) => {
                  const canSort = sortable && col.sortable !== false
                  const active = sort.key === col.key
                  return (
                    <th
                      key={col.key}
                      style={{ width: col.width }}
                      className={canSort ? `sortable ${active ? 'sorted' : ''}` : ''}
                      onClick={() => toggleSort(col)}
                      aria-sort={active ? (sort.dir === 'asc' ? 'ascending' : 'descending') : undefined}
                      title={canSort ? tr("Сортувати") : undefined}
                    >
                      {col.label}
                      {canSort && <span className="sort-icon">{active ? (sort.dir === 'asc' ? '▲' : '▼') : '↕'}</span>}
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, idx) => (
                <tr
                  key={row._id || idx}
                  onClick={() => onRowClick?.(row)}
                  className={onRowClick ? 'clickable' : ''}
                >
                  {columns.map((col) => (
                    <td key={col.key}>
                      {col.render ? col.render(row[col.key], row) : row[col.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default DataTable
