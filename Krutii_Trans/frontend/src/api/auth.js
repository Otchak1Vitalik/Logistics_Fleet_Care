import api from './axios'

export const authApi = {
  login: (username, password) =>
    api.post('/auth/login', { username, password }),

  // Вхід за кодом з пошти (помилки показує сам екран коду)
  requestEmailCode: (username, lang) =>
    api.post('/auth/email-code/request', { username, lang }, { silent: true }),

  verifyEmailCode: (username, code) =>
    api.post('/auth/email-code/verify', { username, code }, { silent: true }),

  logout: () =>
    api.post('/auth/logout'),

  me: () =>
    api.get('/auth/me'),

  updateMe: (data) =>
    api.put('/auth/me', data),

  changePassword: (currentPassword, newPassword) =>
    api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
}
