import api from './axios'

export const waybillsApi = {
  getAll: (params = {}) =>
    api.get('/waybills', { params }),

  getById: (id) =>
    api.get(`/waybills/${id}`),

  create: (data) =>
    api.post('/waybills', data),

  update: (id, data) =>
    api.put(`/waybills/${id}`, data),

  cancel: (id, reason) =>
    api.post(`/waybills/${id}/cancel`, { reason }),

  getActive: () =>
    api.get('/waybills/active')
}
