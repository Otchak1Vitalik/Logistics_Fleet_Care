import { Outlet } from 'react-router-dom'
import TopBar from '../components/TopBar'
import SideBar from '../components/SideBar'
import { tr } from '../i18n'

const navItems = [
  { to: '/manager', label: tr("Головна"), icon: 'home', end: true },
  { to: '/manager/users', label: tr("Користувачі"), icon: 'users' },
  { to: '/manager/vehicles', label: tr("Автопарк"), icon: 'truck' },
  { to: '/manager/waybills', label: tr("Путівки"), icon: 'document' },
  { to: '/manager/faults', label: tr("Несправності"), icon: 'warning' },
  { to: '/manager/repairs', label: tr("Ремонти"), icon: 'wrench' },
  { to: '/manager/parts', label: tr("Склад"), icon: 'box' },
  { to: '/manager/fuel', label: tr("Паливо"), icon: 'fuel' },
  { to: '/manager/calendar', label: tr("Календар ТО"), icon: 'calendar' },
  { to: '/manager/predictive', label: tr("Прогноз несправностей"), icon: 'pulse' },
  { to: '/manager/reports', label: tr("Звіти"), icon: 'chart' },
  { to: '/manager/alerts', label: tr("Сповіщення"), icon: 'bell' },
  { to: '/manager/audit', label: tr("Журнал дій"), icon: 'shield' },
  { to: '/manager/settings', label: tr("Налаштування"), icon: 'settings' }
]

function ManagerLayout() {
  return (
    <div className="app-layout">
      <SideBar items={navItems} role="manager" />
      <div className="main-area">
        <TopBar />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default ManagerLayout
