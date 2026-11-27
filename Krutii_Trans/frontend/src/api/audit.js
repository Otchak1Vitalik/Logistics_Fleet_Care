import api from './axios'

export const auditApi = {
  getAll: (params = {}) => api.get('/audit', { params }),
}
