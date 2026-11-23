import { create } from 'zustand'
import { alertsApi } from '../api/alerts'

export const useAlertStore = create((set, get) => ({
  alerts: [],
  unreadCount: 0,
  isLoading: false,

  fetchAlerts: async (unreadOnly = false) => {
    set({ isLoading: true })
    try {
      const response = await alertsApi.getAll({ unread_only: unreadOnly })
      set({
        alerts: response.data.alerts,
        isLoading: false
      })
    } catch (error) {
      set({ isLoading: false })
    }
  },

  fetchUnreadCount: async () => {
    try {
      const response = await alertsApi.getUnreadCount()
      set({ unreadCount: response.data.count })
    } catch (error) {
      // Ігноруємо
    }
  },

  markAsRead: async (id) => {
    try {
      await alertsApi.markAsRead(id)
      set((state) => ({
        alerts: state.alerts.map((a) =>
          a._id === id ? { ...a, is_read: true } : a
        ),
        unreadCount: Math.max(0, state.unreadCount - 1)
      }))
    } catch (error) {
      // Ігноруємо
    }
  },

  markAllAsRead: async () => {
    try {
      await alertsApi.markAllAsRead()
      set((state) => ({
        alerts: state.alerts.map((a) => ({ ...a, is_read: true })),
        unreadCount: 0
      }))
    } catch (error) {
      // Ігноруємо
    }
  },

  dismiss: async (id) => {
    try {
      await alertsApi.dismiss(id)
      set((state) => ({
        alerts: state.alerts.filter((a) => a._id !== id)
      }))
    } catch (error) {
      // Ігноруємо
    }
  }
}))
