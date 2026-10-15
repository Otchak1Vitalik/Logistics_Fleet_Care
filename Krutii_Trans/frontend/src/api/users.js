import api from './axios'

export const usersApi = {
  getAll: (params = {}) =>
    api.get('/users', { params }),

  getById: (id) =>
    api.get(`/users/${id}`),

  create: (data) =>
    api.post('/users', data),

  update: (id, data) =>
    api.put(`/users/${id}`, data),

  resetPassword: (id, newPassword) =>
    api.post(`/users/${id}/reset-password`, { new_password: newPassword }),

  getDrivers: () =>
    api.get('/users/drivers'),

  getMechanics: () =>
    api.get('/users/mechanics')
}
