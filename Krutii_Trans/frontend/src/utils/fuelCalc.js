/**
 * Розрахунки витрат пального (клієнтська сторона)
 */

const WINTER_MONTHS = [11, 12, 1, 2, 3]
const WINTER_COEFFICIENT = 1.09

export function getSeasonCoefficient(date = new Date()) {
  const month = date.getMonth() + 1
  return WINTER_MONTHS.includes(month) ? WINTER_COEFFICIENT : 1.0
}

export function calculateFuelNorm(distanceKm, baseNorm, date = new Date()) {
  if (distanceKm <= 0) return 0
  const coefficient = getSeasonCoefficient(date)
  return (distanceKm / 100) * baseNorm * coefficient
}

export function calculateConsumption(distanceKm, fuelUsed) {
  if (distanceKm <= 0) return 0
  return (fuelUsed / distanceKm) * 100
}

export function checkOverspend(actualConsumption, baseNorm, threshold = 10) {
  if (baseNorm <= 0) {
    return {
      isOverspend: false,
      deviation: 0,
      deviationPercent: 0,
      message: 'Норма не встановлена'
    }
  }

  const deviation = actualConsumption - baseNorm
  const deviationPercent = (deviation / baseNorm) * 100
  const isOverspend = deviationPercent > threshold

  let message
  if (isOverspend) {
    message = `Перевитрата ${deviationPercent.toFixed(1)}%`
  } else if (deviationPercent > 0) {
    message = `Незначне перевищення ${deviationPercent.toFixed(1)}%`
  } else if (deviationPercent < -5) {
    message = `Економія ${Math.abs(deviationPercent).toFixed(1)}%`
  } else {
    message = 'В межах норми'
  }

  return {
    isOverspend,
    deviation: Math.round(deviation * 100) / 100,
    deviationPercent: Math.round(deviationPercent * 100) / 100,
    message
  }
}

export function formatFuel(value, decimals = 1) {
  if (value === null || value === undefined) return '-'
  return `${value.toFixed(decimals)} л`
}

export function formatConsumption(value) {
  if (value === null || value === undefined) return '-'
  return `${value.toFixed(1)} л/100км`
}
