import api from './axios'

export const faultsApi = {
  getAll: (params = {}) =>
    api.get('/faults', { params }),

  getById: (id) =>
    api.get(`/faults/${id}`),

  create: (data) =>
    api.post('/faults', data),

  update: (id, data) =>
    api.put(`/faults/${id}`, data),

  getPending: () =>
    api.get('/faults/pending'),

  getStatistics: () =>
    api.get('/faults/statistics'),

  // Завантаження фото (файл)
  uploadPhoto: (id, file) => {
    const formData = new FormData()
    formData.append('photo', file)
    return api.post(`/faults/${id}/photos`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // Додавання фото по URL
  addPhotoUrl: (id, url) =>
    api.post(`/faults/${id}/photos`, { url }),

  // Видалення фото
  deletePhoto: (id, photoIndex) =>
    api.delete(`/faults/${id}/photos/${photoIndex}`)
}
