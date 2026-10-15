import { useEffect, useState } from 'react'
import { vehiclesApi } from '../../api/vehicles'
import { fuelApi } from '../../api/fuel'
import Loader from '../../components/Loader'
import { formatNumber, formatOdometer } from '../../utils/formatters'
import { calculateFuelNorm, getSeasonCoefficient } from '../../utils/fuelCalc'

function ManagerFuelPlan() {
  const [vehicles, setVehicles] = useState([])
  const [loading, setLoading] = useState(true)
  const [plannedDistance, setPlannedDistance] = useState(1000)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const response = await vehiclesApi.getAll({ status: 'active' })
      setVehicles(response.data.vehicles)
    } catch (error) {
      // Помилка оброблена в interceptor
    } finally {
      setLoading(false)
    }
  }

  const seasonCoef = getSeasonCoefficient()

  const calculateTotal = () => {
    return vehicles.reduce((sum, v) => {
      const norm = calculateFuelNorm(plannedDistance, v.fuel_norm || 25)
      return sum + norm
    }, 0)
  }

  if (loading) {
    return <Loader text="Завантаження..." />
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Планування пального</h1>
      </div>

      <div className="card mb-lg">
        <h3>Параметри планування</h3>
        <div className="form-row mt-md">
          <div className="form-field">
            <label>Запланований пробіг на авто (км)</label>
            <input
              type="number"
              className="form-control"
              value={plannedDistance}
              onChange={(e) => setPlannedDistance(Number(e.target.value) || 0)}
              min={0}
            />
          </div>
          <div className="form-field">
            <label>Сезонний коефіцієнт</label>
            <input
              type="text"
              className="form-control"
              value={seasonCoef === 1.09 ? '1.09 (зима)' : '1.0 (літо)'}
              disabled
            />
          </div>
        </div>
      </div>

      <div className="dashboard-stats mb-lg">
        <div className="stat-card highlight">
          <div className="stat-value">{vehicles.length}</div>
          <div className="stat-label">Активних авто</div>
        </div>
        <div className="stat-card">
          <div className="stat-value">{formatNumber(plannedDistance * vehicles.length)} км</div>
          <div className="stat-label">Загальний пробіг</div>
        </div>
        <div className="stat-card warning">
          <div className="stat-value">{formatNumber(calculateTotal())} л</div>
          <div className="stat-label">Потрібно пального</div>
        </div>
      </div>

      <div className="card">
        <h3 className="mb-md">Розрахунок по транспорту</h3>
        <div className="table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th>Транспорт</th>
                <th>Пробіг</th>
                <th>Норма (л/100км)</th>
                <th>Запланований пробіг</th>
                <th>Потрібно пального</th>
              </tr>
            </thead>
            <tbody>
              {vehicles.map((v) => {
                const norm = v.fuel_norm || 25
                const fuelNeeded = calculateFuelNorm(plannedDistance, norm)
                return (
                  <tr key={v._id}>
                    <td>
                      <div className="font-medium">{v.plate_number}</div>
                      <div className="text-muted" style={{ fontSize: '0.8125rem' }}>
                        {v.brand} {v.model}
                      </div>
                    </td>
                    <td>{formatOdometer(v.odometer)}</td>
                    <td>{norm}</td>
                    <td>{formatNumber(plannedDistance)} км</td>
                    <td className="font-bold">{formatNumber(fuelNeeded)} л</td>
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr>
                <td colSpan={3}></td>
                <td className="font-bold">Разом:</td>
                <td className="font-bold">{formatNumber(calculateTotal())} л</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <div className="card mt-lg">
        <h3 className="mb-md">Зведення по типам пального</h3>
        <div className="info-grid">
          {['diesel', 'petrol', 'gas'].map((fuelType) => {
            const typeVehicles = vehicles.filter((v) => v.fuel_type === fuelType)
            const typeTotal = typeVehicles.reduce((sum, v) => {
              return sum + calculateFuelNorm(plannedDistance, v.fuel_norm || 25)
            }, 0)

            if (typeVehicles.length === 0) return null

            return (
              <div key={fuelType} className="info-row">
                <span className="label">
                  {{diesel: 'Дизель', petrol: 'Бензин', gas: 'Газ'}[fuelType]}
                  ({typeVehicles.length} авто)
                </span>
                <span className="value font-bold">{formatNumber(typeTotal)} л</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default ManagerFuelPlan
