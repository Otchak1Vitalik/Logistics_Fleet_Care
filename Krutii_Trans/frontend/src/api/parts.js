import api from './axios'

export const partsApi = {
  getAll: (params = {}) => api.get('/parts', { params }),
  create: (data) => api.post('/parts', data),
  update: (id, data) => api.put(`/parts/${id}`, data),
  receive: (id, data) => api.post(`/parts/${id}/receive`, data),
  getMovements: (id) => api.get(`/parts/${id}/movements`),
}
