import { Outlet } from 'react-router-dom'
import TopBar from '../components/TopBar'
import SideBar from '../components/SideBar'

const navItems = [
  { to: '/mechanic', label: 'Головна', icon: 'home', end: true },
  { to: '/mechanic/fleet', label: 'Автопарк', icon: 'truck' },
  { to: '/mechanic/faults', label: 'Несправності', icon: 'warning' },
  { to: '/mechanic/repairs', label: 'Ремонти', icon: 'wrench' },
  { to: '/mechanic/alerts', label: 'Сповіщення', icon: 'bell' }
]

function MechanicLayout() {
  return (
    <div className="app-layout">
      <SideBar items={navItems} role="mechanic" />
      <div className="main-area">
        <TopBar />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default MechanicLayout
