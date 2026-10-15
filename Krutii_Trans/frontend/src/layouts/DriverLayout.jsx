import { Outlet, NavLink } from 'react-router-dom'
import TopBar from '../components/TopBar'
import SideBar from '../components/SideBar'

const navItems = [
  { to: '/driver', label: 'Головна', icon: 'home', end: true },
  { to: '/driver/waybills', label: 'Путівки', icon: 'document' },
  { to: '/driver/faults', label: 'Несправності', icon: 'warning' },
  { to: '/driver/fuel', label: 'Паливо', icon: 'fuel' }
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
