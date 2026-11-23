import { tr } from '../i18n'
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
  issued: tr("Видано"),
  active: tr("Активна"),
  completed: tr("Завершена"),
  cancelled: tr("Скасована"),

  // Ремонти
  planned: tr("Заплановано"),
  in_progress: tr("В роботі"),
  // completed - Завершено (дублюється)

  // Несправності
  new: tr("Нова"),
  acknowledged: tr("Прийнято"),
  in_repair: tr("В ремонті"),
  resolved: tr("Вирішено"),
  rejected: tr("Відхилено"),

  // Транспорт
  repair: tr("В ремонті"),
  inspection: tr("На огляді"),
  decommissioned: tr("Списано"),

  // Сповіщення
  info: tr("Інформація"),
  warning: tr("Попередження"),
  critical: tr("Критично")
}

function StatusBadge({ status, customLabel }) {
  const color = STATUS_COLORS[status] || 'gray'
  const label = customLabel || STATUS_LABELS[status] || status

  return <span className={`status-badge status-${color}`}>{label}</span>
}

export default StatusBadge
