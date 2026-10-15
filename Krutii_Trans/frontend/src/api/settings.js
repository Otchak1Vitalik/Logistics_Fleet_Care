import api from './axios'

export const settingsApi = {
  get: () =>
    api.get('/settings'),

  update: (data) =>
    api.put('/settings', data),

  reset: () =>
    api.post('/settings/reset'),

  getFuelTypes: () =>
    api.get('/settings/fuel-types'),

  getCategories: () =>
    api.get('/settings/categories')
}
