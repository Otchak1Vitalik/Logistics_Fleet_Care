import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { authApi } from '../api/auth'

export const useAuthStore = create(
  persist(
    (set, get) => ({
      user: null,
      isAuthenticated: false,
      isLoading: false,
      _hasHydrated: false,

      setHasHydrated: (state) => {
        set({ _hasHydrated: state })
      },

      login: async (username, password) => {
        set({ isLoading: true })
        try {
          const response = await authApi.login(username, password)
          const { user } = response.data
          set({
            user,
            isAuthenticated: true,
            isLoading: false
          })
          return { success: true, user }
        } catch (error) {
          set({ isLoading: false })
          return {
            success: false,
            error: error.response?.data?.error || 'Помилка входу'
          }
        }
      },

      logout: async () => {
        try {
          await authApi.logout()
        } catch (error) {
          // Ігноруємо помилки при виході
        }
        set({
          user: null,
          isAuthenticated: false
        })
      },

      checkAuth: async () => {
        try {
          const response = await authApi.me()
          const { user } = response.data
          set({
            user,
            isAuthenticated: true
          })
          return true
        } catch (error) {
          set({
            user: null,
            isAuthenticated: false
          })
          return false
        }
      },

      updateUser: (userData) => {
        set({ user: { ...get().user, ...userData } })
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated
      }),
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true)
      }
    }
  )
)
