import api from './axios'

export const predictiveApi = {
  risk: (params = {}) => api.get('/predictive/risk', { params }),
  model: () => api.get('/predictive/model'),
  retrain: () => api.post('/predictive/retrain'),
  scania: () => api.get('/predictive/scania'),
}
