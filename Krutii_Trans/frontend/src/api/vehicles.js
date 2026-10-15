import api from './axios'

export const vehiclesApi = {
  getAll: (params = {}) =>
    api.get('/vehicles', { params }),

  getById: (id) =>
    api.get(`/vehicles/${id}`),

  create: (data) =>
    api.post('/vehicles', data),

  update: (id, data) =>
    api.put(`/vehicles/${id}`, data),

  updateOdometer: (id, odometer) =>
    api.put(`/vehicles/${id}/odometer`, { odometer }),

  getHistory: (id) =>
    api.get(`/vehicles/${id}/history`)
}
