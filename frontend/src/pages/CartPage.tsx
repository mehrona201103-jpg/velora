import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { getCart, removeCartItem, updateCartItem, checkout, Cart } from '../services/api'

export default function CartPage() {
  const navigate = useNavigate()
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState(false)
  const [error, setError] = useState('')
  const [deliveryType, setDeliveryType] = useState<'PICKUP' | 'DELIVERY'>('PICKUP')
  const [address, setAddress] = useState('')

  useEffect(() => {
    loadCart()
  }, [])

  async function loadCart() {
    try {
      const data = await getCart()
      setCart(data)
    } catch {
      setCart(null)
    } finally {
      setLoading(false)
    }
  }

  async function handleRemove(id: number) {
    const data = await removeCartItem(id)
    setCart(data)
  }

  async function handleQty(id: number, qty: number) {
    const data = await updateCartItem(id, qty)
    setCart(data)
  }

  async function handleCheckout() {
    setError('')
    setCheckoutLoading(true)
    try {
      const order = await checkout({
        delivery_type: deliveryType,
        address: deliveryType === 'DELIVERY' ? address : undefined,
        idempotency_key: `checkout-${Date.now()}`,
      })
      navigate(`/profile`)
      alert(`Заказ ${order.order_number} создан! Статус: ${order.status}`)
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка оформления')
    } finally {
      setCheckoutLoading(false)
    }
  }

  if (loading) {
    return <div className="px-4 pt-10 text-center text-charcoal/50">Загрузка...</div>
  }

  if (!cart || cart.items_count === 0) {
    return (
      <div className="px-4 pt-6">
        <h1 className="text-xl font-light mb-6">Корзина</h1>
        <div className="text-center py-16">
          <p className="text-charcoal/50">Корзина пуста</p>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-6 pb-8">
      <h1 className="text-xl font-light mb-6">Корзина</h1>

      <div className="space-y-4 mb-8">
        {cart.items.map((item) => (
          <div key={item.id} className="bg-cream rounded-sm p-4 flex justify-between items-start">
            <div>
              <p className="font-medium text-sm">{item.product_name || 'Товар'}</p>
              <p className="text-xs text-charcoal/50 mt-1">{item.sku}</p>
              <p className="text-sm text-gold mt-2">{item.unit_price} TJS</p>
              <div className="flex items-center gap-3 mt-2">
                <button
                  onClick={() => handleQty(item.id, Math.max(0, item.quantity - 1))}
                  className="w-8 h-8 border border-beige rounded-sm text-sm"
                >
                  −
                </button>
                <span className="text-sm">{item.quantity}</span>
                <button
                  onClick={() => handleQty(item.id, item.quantity + 1)}
                  className="w-8 h-8 border border-beige rounded-sm text-sm"
                >
                  +
                </button>
              </div>
            </div>
            <div className="text-right">
              <p className="text-sm font-medium">{item.total_price} TJS</p>
              <button
                onClick={() => handleRemove(item.id)}
                className="text-xs text-charcoal/40 mt-2 underline"
              >
                Удалить
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="border-t border-beige pt-4 mb-6">
        <div className="flex justify-between text-sm mb-4">
          <span>Итого</span>
          <span className="font-medium text-gold">{cart.subtotal} TJS</span>
        </div>

        <div className="space-y-3 mb-4">
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={deliveryType === 'PICKUP'}
              onChange={() => setDeliveryType('PICKUP')}
            />
            Самовывоз
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="radio"
              checked={deliveryType === 'DELIVERY'}
              onChange={() => setDeliveryType('DELIVERY')}
            />
            Доставка
          </label>
          {deliveryType === 'DELIVERY' && (
            <input
              type="text"
              placeholder="Адрес доставки"
              value={address}
              onChange={(e) => setAddress(e.target.value)}
              className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold text-sm"
            />
          )}
        </div>

        {error && <p className="text-red-600 text-sm mb-3">{error}</p>}

        <button
          onClick={handleCheckout}
          disabled={checkoutLoading}
          className="btn-primary w-full"
        >
          {checkoutLoading ? 'Оформление...' : 'Оформить заказ'}
        </button>
      </div>
    </div>
  )
}
