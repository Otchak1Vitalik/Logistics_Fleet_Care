import { useEffect, useState } from 'react'
import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  PieChart, Pie, Cell,
} from 'recharts'
import { reportsApi } from '../api/reports'
import { useThemeStore } from '../store/themeStore'
import { formatCurrency } from '../utils/formatters'
import { tr } from '../i18n'

// Кольори серій підібрані так, щоб читатися і на світлому, і на темному фоні
const COLORS = {
  repairs: '#6366f1',
  fuel: '#f59e0b',
  faults: '#f97316',
  diesel: '#6366f1',
  petrol: '#f59e0b',
  gas: '#10b981',
}

const thousands = (value) => (value >= 1000 ? tr("{0} тис.", Math.round(value / 1000)) : value)

function DashboardCharts() {
  const theme = useThemeStore((s) => s.theme)
  const [data, setData] = useState(null)

  useEffect(() => {
    reportsApi.getAnalytics({ months: 6 })
      .then((res) => setData(res.data.analytics))
      .catch(() => setData(null))
  }, [])

  if (!data) return null

  const axis = theme === 'dark' ? '#9aa4b2' : '#6b7280'
  const grid = theme === 'dark' ? '#263044' : '#e5e7eb'
  const tooltipStyle = {
    background: 'var(--color-surface)',
    border: '1px solid var(--color-gray-200)',
    borderRadius: 8,
    color: 'var(--color-gray-900)',
  }
  const totalVehicles = data.fleet_by_fuel.reduce((sum, r) => sum + r.count, 0)

  return (
    <div className="charts-grid">
      <div className="card chart-card chart-wide">
        <h3>{tr("Витрати по місяцях, грн")}</h3>
        <p className="text-muted chart-subtitle">{tr("Завершені ремонти й ТО та закупівля пального за останні 6 місяців")}</p>
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data.monthly_costs} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={grid} vertical={false} />
            <XAxis dataKey="month" tick={{ fill: axis, fontSize: 12 }} axisLine={{ stroke: grid }} tickLine={false} />
            <YAxis tickFormatter={thousands} tick={{ fill: axis, fontSize: 12 }} axisLine={false} tickLine={false} width={64} />
            <Tooltip formatter={(v) => formatCurrency(v)} contentStyle={tooltipStyle} cursor={{ fill: grid, opacity: 0.4 }} />
            <Legend wrapperStyle={{ fontSize: 13, color: axis }} />
            <Bar dataKey="repairs" name={tr("Ремонти і ТО")} stackId="c" fill={COLORS.repairs} />
            <Bar dataKey="fuel" name={tr("Пальне")} stackId="c" fill={COLORS.fuel} radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="card chart-card">
        <h3>{tr("Несправності за категоріями")}</h3>
        <p className="text-muted chart-subtitle">{tr("За останні 6 місяців")}</p>
        {data.faults_by_category.length === 0 ? (
          <div className="empty-state small">{tr("Несправностей не зареєстровано")}</div>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.faults_by_category} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={grid} horizontal={false} />
              <XAxis type="number" allowDecimals={false} tick={{ fill: axis, fontSize: 12 }} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="label" tick={{ fill: axis, fontSize: 12 }} axisLine={false} tickLine={false} width={90} />
              <Tooltip formatter={(v) => [v, tr("Кількість")]} contentStyle={tooltipStyle} cursor={{ fill: grid, opacity: 0.4 }} />
              <Bar dataKey="count" name={tr("Кількість")} fill={COLORS.faults} radius={[0, 4, 4, 0]} barSize={18} />
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="card chart-card">
        <h3>{tr("Автопарк за типом пального")}</h3>
        <p className="text-muted chart-subtitle">{tr("Усього:")}{' '}{totalVehicles}{' '}{tr("од.")}</p>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={data.fleet_by_fuel} dataKey="count" nameKey="label" innerRadius={60} outerRadius={95}
              paddingAngle={2} stroke="none">
              {data.fleet_by_fuel.map((row) => (
                <Cell key={row.fuel_type} fill={COLORS[row.fuel_type] || '#9ca3af'} />
              ))}
            </Pie>
            <Tooltip formatter={(v, name) => [tr("{0} од.", v), name]} contentStyle={tooltipStyle} />
            <Legend wrapperStyle={{ fontSize: 13, color: axis }} />
          </PieChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export default DashboardCharts
