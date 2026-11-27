import api from './axios'

export const fuelAnomaliesApi = {
  getAll: (params = {}) => api.get('/fuel/anomalies', { params }),
  run: () => api.post('/fuel/anomalies/run'),
  review: (id, status, comment) => api.put(`/fuel/anomalies/${id}`, { status, comment }),
  evaluation: () => api.get('/fuel/anomalies/evaluation'),
  vehicleHistory: (vehicleId) => api.get(`/fuel/anomalies/vehicle/${vehicleId}`),
}
