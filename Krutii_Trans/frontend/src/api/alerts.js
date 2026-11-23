import api from './axios'

export const alertsApi = {
  getAll: (params = {}) =>
    api.get('/alerts', { params }),

  getUnreadCount: () =>
    api.get('/alerts/unread-count'),

  markAsRead: (id) =>
    api.post(`/alerts/${id}/read`),

  markAllAsRead: () =>
    api.post('/alerts/mark-all-read'),

  dismiss: (id) =>
    api.post(`/alerts/${id}/dismiss`),

  getAllSystem: (params = {}) =>
    api.get('/alerts/all', { params }),

  getStatistics: () =>
    api.get('/alerts/statistics')
}
