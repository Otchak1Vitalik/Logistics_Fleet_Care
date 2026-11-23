import api from './axios'

export const repairsApi = {
  getAll: (params = {}) =>
    api.get('/repairs', { params }),

  getById: (id) =>
    api.get(`/repairs/${id}`),

  create: (data) =>
    api.post('/repairs', data),

  update: (id, data) =>
    api.put(`/repairs/${id}`, data),

  getScheduled: () =>
    api.get('/repairs/scheduled'),

  getStatistics: () =>
    api.get('/repairs/statistics')
}
