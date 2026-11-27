import api from './axios'

export const maintenancePlanApi = {
  get: (params = {}) => api.get('/maintenance-plan', { params }),
  apply: (items) => api.post('/maintenance-plan/apply', { items }),
}
