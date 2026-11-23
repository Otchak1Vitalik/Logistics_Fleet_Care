const STATUS_COLORS = {
  // Путівки
  issued: 'blue',
  active: 'green',
  completed: 'gray',
  cancelled: 'red',

  // Ремонти
  planned: 'yellow',
  in_progress: 'blue',
  // completed - gray (вже є)
  // cancelled - red (вже є)

  // Несправності
  new: 'yellow',
  acknowledged: 'blue',
  in_repair: 'orange',
  resolved: 'green',
  rejected: 'red',

  // Транспорт
  // active - green (вже є)
  repair: 'yellow',
  inspection: 'blue',
  decommissioned: 'gray',

  // Сповіщення
  info: 'blue',
  warning: 'yellow',
  critical: 'red'
}

const STATUS_LABELS = {
  // Путівки
  issued: 'Видано',
  active: 'Активна',
  completed: 'Завершена',
  cancelled: 'Скасована',

  // Ремонти
  planned: 'Заплановано',
  in_progress: 'В роботі',
  // completed - Завершено (дублюється)

  // Несправності
  new: 'Нова',
  acknowledged: 'Прийнято',
  in_repair: 'В ремонті',
  resolved: 'Вирішено',
  rejected: 'Відхилено',

  // Транспорт
  repair: 'В ремонті',
  inspection: 'На огляді',
  decommissioned: 'Списано',

  // Сповіщення
  info: 'Інформація',
  warning: 'Попередження',
  critical: 'Критично'
}

function StatusBadge({ status, customLabel }) {
  const color = STATUS_COLORS[status] || 'gray'
  const label = customLabel || STATUS_LABELS[status] || status

  return <span className={`status-badge status-${color}`}>{label}</span>
}

export default StatusBadge
