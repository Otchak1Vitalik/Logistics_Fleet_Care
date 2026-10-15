import { create } from 'zustand'
import { waybillsApi } from '../api/waybills'

export const useWaybillStore = create((set, get) => ({
  waybills: [],
  currentWaybill: null,
  activeWaybill: null,
  isLoading: false,
  error: null,

  fetchWaybills: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await waybillsApi.getAll(params)
      set({
        waybills: response.data.waybills,
        isLoading: false
      })
    } catch (error) {
      set({
        isLoading: false,
        error: error.response?.data?.error || 'Помилка завантаження'
      })
    }
  },

  fetchWaybill: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const response = await waybillsApi.getById(id)
      set({
        currentWaybill: response.data.waybill,
        isLoading: false
      })
      return response.data.waybill
    } catch (error) {
      set({
        isLoading: false,
        error: error.response?.data?.error || 'Помилка завантаження'
      })
      return null
    }
  },

  fetchActiveWaybill: async () => {
    try {
      const response = await waybillsApi.getActive()
      set({ activeWaybill: response.data.waybill })
      return response.data.waybill
    } catch (error) {
      set({ activeWaybill: null })
      return null
    }
  },

  createWaybill: async (data) => {
    try {
      const response = await waybillsApi.create(data)
      set((state) => ({
        waybills: [response.data.waybill, ...state.waybills]
      }))
      return { success: true, waybill: response.data.waybill }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Помилка створення'
      }
    }
  },

  updateWaybill: async (id, data) => {
    try {
      const response = await waybillsApi.update(id, data)
      const updated = response.data.waybill
      set((state) => ({
        waybills: state.waybills.map((w) => (w._id === id ? updated : w)),
        currentWaybill:
          state.currentWaybill?._id === id ? updated : state.currentWaybill,
        activeWaybill:
          state.activeWaybill?._id === id ? updated : state.activeWaybill
      }))
      return { success: true, waybill: updated }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Помилка оновлення'
      }
    }
  },

  cancelWaybill: async (id, reason) => {
    try {
      await waybillsApi.cancel(id, reason)
      set((state) => ({
        waybills: state.waybills.map((w) =>
          w._id === id ? { ...w, status: 'cancelled' } : w
        )
      }))
      return { success: true }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Помилка скасування'
      }
    }
  },

  clearCurrent: () => {
    set({ currentWaybill: null })
  }
}))
