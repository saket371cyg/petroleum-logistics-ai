import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

export const authApi = {
  login: (email, password) => api.post('/auth/login', { email, password }),
}

export const inventoryApi = {
  get: (dealerId) => api.get(`/inventory/${dealerId}`),
  getRisk: (dealerId) => api.get(`/inventory/${dealerId}/risk`),
}

export const forecastApi = {
  get: (dealerId, fuelType, horizonDays = 7) =>
    api.get(`/forecast/${dealerId}`, { params: { fuel_type: fuelType, horizon_days: horizonDays } }),
}

export const ordersApi = {
  list: (dealerId) => api.get(`/orders/${dealerId}`),
  create: (fuelType, quantityL) => api.post('/orders', { fuel_type: fuelType, quantity_l: quantityL }),
  recommend: (orderId, fuelType) => api.post(`/orders/${orderId}/recommend`, null, { params: { fuel_type: fuelType } }),
  approve: (orderId) => api.post(`/orders/${orderId}/approve`),
}

export const fleetApi = {
  available: () => api.get('/fleet/available'),
  tankers: (dealerId) => api.get(`/fleet/${dealerId}`),
  drivers: (dealerId) => api.get(`/fleet/${dealerId}/drivers`),
}

export const refineryApi = {
  slots: () => api.get('/refinery-slots'),
}

export const dispatchApi = {
  optimize: (orderId, deadlineHours = 6) => api.post('/dispatch/optimize', { order_id: orderId, deadline_hours: deadlineHours }),
  list: (dealerId) => api.get(`/dispatch/${dealerId}`),
  approve: (dispatchId) => api.post(`/dispatch/${dispatchId}/approve`),
  complete: (dispatchId) => api.post(`/dispatch/${dispatchId}/complete`),
}

export const complianceApi = {
  alerts: (dealerId) => api.get(`/compliance/${dealerId}`),
}

export const maintenanceApi = {
  alerts: (dealerId) => api.get(`/maintenance/${dealerId}`),
}

export const analyticsApi = {
  get: (dealerId) => api.get(`/analytics/${dealerId}`),
  dashboard: () => api.get('/dashboard'),
}

export const aiApi = {
  query: (question) => api.post('/ai/query', { question }),
}

export default api
