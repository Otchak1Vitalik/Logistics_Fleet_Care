import { Outlet, NavLink } from 'react-router-dom'
import TopBar from '../components/TopBar'
import SideBar from '../components/SideBar'
import { tr } from '../i18n'

const navItems = [
  { to: '/driver', label: tr("Головна"), icon: 'home', end: true },
  { to: '/driver/waybills', label: tr("Путівки"), icon: 'document' },
  { to: '/driver/faults', label: tr("Несправності"), icon: 'warning' },
  { to: '/driver/fuel', label: tr("Паливо"), icon: 'fuel' }
]

function DriverLayout() {
  return (
    <div className="app-layout">
      <SideBar items={navItems} role="driver" />
      <div className="main-area">
        <TopBar />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default DriverLayout
