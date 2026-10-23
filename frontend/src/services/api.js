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
  update: (dealerId, fuelType, data) => api.put(`/inventory/${dealerId}/${fuelType}`, data),
  simulateConsumption: (dealerId, data = { days: 1.0 }) =>
    api.post(`/inventory/${dealerId}/simulate-consumption`, data),
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
  cancel: (orderId) => api.post(`/orders/${orderId}/cancel`),
}

export const fleetApi = {
  available: () => api.get('/fleet/available'),
  tankers: (dealerId) => api.get(`/fleet/${dealerId}`),
  drivers: (dealerId) => api.get(`/fleet/${dealerId}/drivers`),
  createTanker: (data) => api.post('/fleet/tankers', data),
  updateTanker: (tankerId, data) => api.patch(`/fleet/tankers/${tankerId}`, data),
  deleteTanker: (tankerId) => api.delete(`/fleet/tankers/${tankerId}`),
  createDriver: (data) => api.post('/fleet/drivers', data),
  updateDriver: (driverId, data) => api.patch(`/fleet/drivers/${driverId}`, data),
  deleteDriver: (driverId) => api.delete(`/fleet/drivers/${driverId}`),
}

export const refineryApi = {
  slots: () => api.get('/refinery-slots'),
  refineries: () => api.get('/refinery-slots/refineries'),
  createSlot: (data) => api.post('/refinery-slots', data),
}

export const dispatchApi = {
  optimize: (orderId, deadlineHours = 6) => api.post('/dispatch/optimize', { order_id: orderId, deadline_hours: deadlineHours }),
  list: (dealerId) => api.get(`/dispatch/${dealerId}`),
  approve: (dispatchId) => api.post(`/dispatch/${dispatchId}/approve`),
  complete: (dispatchId) => api.post(`/dispatch/${dispatchId}/complete`),
}

export const complianceApi = {
  alerts: (dealerId) => api.get(`/compliance/${dealerId}`),
  renew: (data) => api.post('/compliance/renew', data),
  create: (data) => api.post('/compliance', data),
}

export const maintenanceApi = {
  alerts: (dealerId) => api.get(`/maintenance/${dealerId}`),
  log: (data) => api.post('/maintenance/log', data),
}

export const analyticsApi = {
  get: (dealerId) => api.get(`/analytics/${dealerId}`),
  dashboard: () => api.get('/dashboard'),
}

export const aiApi = {
  query: (question) => api.post('/ai/query', { question }),
}

export default api
