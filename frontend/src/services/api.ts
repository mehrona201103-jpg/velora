import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('velora_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export default api

export interface User {
  id: number
  email?: string
  phone?: string
  full_name?: string
  role: string
  language: string
  device_type: string
  avatar_url?: string
  is_verified: boolean
  verification_status: string
  total_orders: number
  total_spent: number
  lock_type?: string
}

export interface Product {
  id: number
  sku: string
  name_ru: string
  description_ru?: string
  price: number
  discount_percent: number
  final_price: number
  stock: number
  images: { id: number; url: string; is_main: boolean }[]
  variants: { id: number; name: string; stock: number; price_modifier: number }[]
  delivery_days_min: number
  delivery_days_max: number
  rating_avg?: number
  rating_count?: number
}

export interface Cart {
  id: number
  items: {
    id: number
    product_id: number
    quantity: number
    product_name?: string
    unit_price?: number
    total_price?: number
    image_url?: string
  }[]
  subtotal: number
  items_count: number
}

export interface Order {
  id: number
  order_number: string
  status: string
  payment_status: string
  subtotal: number
  delivery_cost: number
  delivery_quote_status?: string
  payment_method_id?: number
  subtotal?: number
  total: number
  delivery_address: string
  delivery_city: string
  items: { product_name: string; quantity: number; unit_price: number; total_price: number }[]
  status_history: { status: string; comment?: string; created_at: string }[]
  payment_submissions?: { id: number; created_at: string; is_reviewed: boolean }[]
  created_at: string
  payment_rejection_reason?: string
}

export interface PaymentMethod {
  id: number
  code?: string
  name: string
  recipient_name: string
  account_number?: string
  instructions?: string
  tg_username?: string
  tg_deep_link?: string
  stars_per_usd?: number
}
