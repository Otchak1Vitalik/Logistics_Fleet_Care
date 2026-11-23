import { Outlet } from 'react-router-dom'
import TopBar from '../components/TopBar'
import SideBar from '../components/SideBar'
import { tr } from '../i18n'

const navItems = [
  { to: '/mechanic', label: tr("Головна"), icon: 'home', end: true },
  { to: '/mechanic/fleet', label: tr("Автопарк"), icon: 'truck' },
  { to: '/mechanic/faults', label: tr("Несправності"), icon: 'warning' },
  { to: '/mechanic/repairs', label: tr("Ремонти"), icon: 'wrench' },
  { to: '/mechanic/parts', label: tr("Склад"), icon: 'box' },
  { to: '/mechanic/calendar', label: tr("Календар ТО"), icon: 'calendar' },
  { to: '/mechanic/alerts', label: tr("Сповіщення"), icon: 'bell' }
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
