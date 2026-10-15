import { create } from 'zustand'
import { vehiclesApi } from '../api/vehicles'

export const useVehicleStore = create((set, get) => ({
  vehicles: [],
  currentVehicle: null,
  isLoading: false,
  error: null,

  fetchVehicles: async (params = {}) => {
    set({ isLoading: true, error: null })
    try {
      const response = await vehiclesApi.getAll(params)
      set({
        vehicles: response.data.vehicles,
        isLoading: false
      })
    } catch (error) {
      set({
        isLoading: false,
        error: error.response?.data?.error || 'Помилка завантаження'
      })
    }
  },

  fetchVehicle: async (id) => {
    set({ isLoading: true, error: null })
    try {
      const response = await vehiclesApi.getById(id)
      set({
        currentVehicle: response.data.vehicle,
        isLoading: false
      })
      return response.data.vehicle
    } catch (error) {
      set({
        isLoading: false,
        error: error.response?.data?.error || 'Помилка завантаження'
      })
      return null
    }
  },

  createVehicle: async (data) => {
    try {
      const response = await vehiclesApi.create(data)
      set((state) => ({
        vehicles: [...state.vehicles, response.data.vehicle]
      }))
      return { success: true, vehicle: response.data.vehicle }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Помилка створення'
      }
    }
  },

  updateVehicle: async (id, data) => {
    try {
      const response = await vehiclesApi.update(id, data)
      set((state) => ({
        vehicles: state.vehicles.map((v) =>
          v._id === id ? response.data.vehicle : v
        ),
        currentVehicle:
          state.currentVehicle?._id === id
            ? response.data.vehicle
            : state.currentVehicle
      }))
      return { success: true, vehicle: response.data.vehicle }
    } catch (error) {
      return {
        success: false,
        error: error.response?.data?.error || 'Помилка оновлення'
      }
    }
  },

  clearCurrent: () => {
    set({ currentVehicle: null })
  }
}))
