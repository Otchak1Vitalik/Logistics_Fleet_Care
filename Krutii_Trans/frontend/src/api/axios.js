import axios from 'axios'
import toast from 'react-hot-toast'

const api = axios.create({
  baseURL: '/api',
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Флаг для запобігання множинним редиректам
let isRedirecting = false

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.error || 'Сталася помилка'
    const status = error.response?.status
    const url = error.config?.url || ''

    // Якщо 401 і це не запит на авторизацію
    if (status === 401) {
      // Ігноруємо 401 для запитів авторизації
      if (url.includes('/auth/')) {
        return Promise.reject(error)
      }

      // Запобігаємо множинним редиректам
      if (!isRedirecting) {
        isRedirecting = true

        // Затримка перед редиректом, щоб уникнути гонки
        setTimeout(() => {
          localStorage.removeItem('auth-storage')
          isRedirecting = false  // Скидаємо флаг для наступного логіну
          window.location.href = '/login'
        }, 100)
      }

      return Promise.reject(error)
    }

    // Показуємо помилку для інших статусів
    if (status !== 401 && status !== 403) {
      toast.error(message)
    } else if (status === 403) {
      toast.error('Доступ заборонено')
    }

    return Promise.reject(error)
  }
)

export default api
