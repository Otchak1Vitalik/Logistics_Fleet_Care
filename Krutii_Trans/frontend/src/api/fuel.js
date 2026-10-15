import api from './axios'

export const fuelApi = {
  // Накладні
  getInvoices: (params = {}) =>
    api.get('/fuel/invoices', { params }),

  getInvoiceById: (id) =>
    api.get(`/fuel/invoices/${id}`),

  createInvoice: (data) =>
    api.post('/fuel/invoices', data),

  // Записи видачі
  getRecords: (params = {}) =>
    api.get('/fuel/records', { params }),

  createRecord: (data) =>
    api.post('/fuel/records', data),

  // Аналітика
  analyze: (vehicleId) =>
    api.get(`/fuel/analysis/${vehicleId}`),

  getSummary: () =>
    api.get('/fuel/summary')
}
