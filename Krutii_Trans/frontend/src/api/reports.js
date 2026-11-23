import api from './axios'

export const reportsApi = {
  getDashboard: () =>
    api.get('/reports/dashboard'),

  getFleetStatus: () =>
    api.get('/reports/fleet-status'),

  getFuelConsumption: (params = {}) =>
    api.get('/reports/fuel-consumption', { params }),

  getDriverPerformance: (params = {}) =>
    api.get('/reports/driver-performance', { params }),

  getMaintenanceSchedule: () =>
    api.get('/reports/maintenance-schedule'),

  getCostsSummary: (params = {}) =>
    api.get('/reports/costs-summary', { params })
}
