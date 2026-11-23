import { Outlet } from 'react-router-dom'
import TopBar from '../components/TopBar'
import SideBar from '../components/SideBar'

const navItems = [
  { to: '/manager', label: 'Головна', icon: 'home', end: true },
  { to: '/manager/users', label: 'Користувачі', icon: 'users' },
  { to: '/manager/vehicles', label: 'Автопарк', icon: 'truck' },
  { to: '/manager/waybills', label: 'Путівки', icon: 'document' },
  { to: '/manager/fuel', label: 'Паливо', icon: 'fuel' },
  { to: '/manager/reports', label: 'Звіти', icon: 'chart' },
  { to: '/manager/alerts', label: 'Сповіщення', icon: 'bell' },
  { to: '/manager/settings', label: 'Налаштування', icon: 'settings' }
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
