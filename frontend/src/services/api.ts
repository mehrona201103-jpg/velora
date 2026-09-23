import axios from 'axios'

const API_URL = import.meta.env.VITE_API_URL || ''

export const api = axios.create({
  baseURL: API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface UserMe {
  id: number
  first_name: string
  last_name: string
  phone: string
  email: string | null
  language: string
  roles: string[]
  balance: string
}

export async function login(phone: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/login', { phone, password })
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  return data
}

export async function register(payload: {
  first_name: string
  last_name: string
  phone: string
  password: string
  password_confirm: string
}): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/register', payload)
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  return data
}

export async function getMe(): Promise<UserMe> {
  const { data } = await api.get<UserMe>('/users/me')
  return data
}

export function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
}

// Cart
export interface CartItem {
  id: number
  variant_id: number
  quantity: number
  product_name: string | null
  sku: string | null
  unit_price: string | null
  total_price: string | null
  available: number | null
}

export interface Cart {
  id: number
  items: CartItem[]
  subtotal: string
  items_count: number
}

export async function getCart(): Promise<Cart> {
  const { data } = await api.get<Cart>('/cart')
  return data
}

export async function addToCart(variant_id: number, quantity = 1): Promise<Cart> {
  const { data } = await api.post<Cart>('/cart/items', { variant_id, quantity })
  return data
}

export async function updateCartItem(item_id: number, quantity: number): Promise<Cart> {
  const { data } = await api.patch<Cart>(`/cart/items/${item_id}`, { quantity })
  return data
}

export async function removeCartItem(item_id: number): Promise<Cart> {
  const { data } = await api.delete<Cart>(`/cart/items/${item_id}`)
  return data
}

// Orders
export interface OrderItem {
  id: number
  product_name: string
  sku: string
  quantity: number
  unit_price: string
  total_price: string
}

export interface Order {
  id: number
  order_number: string
  status: string
  delivery_type: string
  subtotal: string
  delivery_fee: string
  discount: string
  total: string
  currency: string
  city: string | null
  address: string | null
  phone: string | null
  qr_code: string | null
  pickup_expires_at: string | null
  created_at: string
  items: OrderItem[]
}

export async function checkout(payload: {
  delivery_type: 'PICKUP' | 'DELIVERY'
  city?: string
  district?: string
  address?: string
  phone?: string
  comment?: string
  idempotency_key?: string
}): Promise<Order> {
  const { data } = await api.post<Order>('/orders/checkout', payload)
  return data
}

export async function getMyOrders(): Promise<{ items: Order[]; total: number }> {
  const { data } = await api.get('/orders')
  return data
}
