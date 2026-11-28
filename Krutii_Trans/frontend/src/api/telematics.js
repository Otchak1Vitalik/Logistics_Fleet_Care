import api from './axios'

export const telematicsApi = {
  fleet: () => api.get('/telematics/fleet'),
  vehicle: (id, hours = 3) => api.get(`/telematics/vehicle/${id}`, { params: { hours } }),
  provision: (id) => api.post(`/telematics/devices/${id}`),
}
