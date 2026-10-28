import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api, { Cart } from '../services/api'

export default function CartPage() {
  const [cart, setCart] = useState<Cart | null>(null)
  const [zones, setZones] = useState<any[]>([])
  const [methods, setMethods] = useState<any[]>([])
  const [zoneId, setZoneId] = useState<number | ''>('')
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [methodId, setMethodId] = useState<number | ''>('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const load = () => api.get('/cart').then((r) => setCart(r.data))

  useEffect(() => {
    load()
    api.get('/orders/delivery-zones').then((r) => setZones(r.data))
    api.get('/orders/payment-methods').then((r) => setMethods(r.data))
  }, [])

  const updateQty = async (itemId: number, quantity: number) => {
    await api.patch(`/cart/items/${itemId}?quantity=${quantity}`)
    load()
  }

  const remove = async (itemId: number) => {
    await api.delete(`/cart/items/${itemId}`)
    load()
  }

  const checkout = async () => {
    if (!address || !zoneId) {
      setError('Укажите адрес и зону доставки')
      return
    }
    setLoading(true)
    setError('')
    try {
      const r = await api.post('/orders', {
        delivery_address: address,
        delivery_zone_id: zoneId,
        delivery_phone: phone || undefined,
        payment_method_id: methodId || undefined,
      })
      navigate(`/orders/${r.data.id}`)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка оформления')
    } finally {
      setLoading(false)
    }
  }

  if (!cart) return <p>Загрузка...</p>
  if (cart.items.length === 0) return <p style={{ padding: 40 }}>Корзина пуста</p>

  const selectedZone = zones.find((z) => z.id === zoneId)
  let delivery = selectedZone ? Number(selectedZone.base_price) : 0
  if (selectedZone?.free_from_amount && cart.subtotal >= selectedZone.free_from_amount) delivery = 0
  const total = Number(cart.subtotal) + delivery

  return (
    <div style={{ marginTop: 24 }}>
      <h1 style={{ color: 'var(--purple-deep)' }}>Корзина</h1>
      <table className="table" style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th>Товар</th>
            <th>Цена</th>
            <th>Кол-во</th>
            <th>Сумма</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {cart.items.map((i) => (
            <tr key={i.id}>
              <td>{i.product_name}</td>
              <td>{Number(i.unit_price).toFixed(0)} TJS</td>
              <td>
                <input
                  type="number"
                  min={1}
                  value={i.quantity}
                  onChange={(e) => updateQty(i.id, Number(e.target.value))}
                  style={{ width: 60 }}
                />
              </td>
              <td>{Number(i.total_price).toFixed(0)} TJS</td>
              <td><button onClick={() => remove(i.id)}>✕</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 24, maxWidth: 480 }}>
        <h3>Оформление заказа</h3>
        <div className="form-group">
          <label>Город / зона доставки</label>
          <select value={zoneId} onChange={(e) => setZoneId(Number(e.target.value) || '')}>
            <option value="">Выберите...</option>
            {zones.map((z) => (
              <option key={z.id} value={z.id}>
                {z.name} ({z.city}) — {Number(z.base_price)} TJS
              </option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Полный адрес</label>
          <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Улица, дом, квартира" />
        </div>
        <div className="form-group">
          <label>Телефон</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+992..." />
        </div>
        <div className="form-group">
          <label>Способ оплаты</label>
          <select value={methodId} onChange={(e) => setMethodId(Number(e.target.value) || '')}>
            <option value="">Выберите...</option>
            {methods.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>

        <div style={{ background: 'white', padding: 16, borderRadius: 12, marginTop: 16 }}>
          <div>Товары: <strong>{Number(cart.subtotal).toFixed(0)} TJS</strong></div>
          <div>Доставка: <strong>{delivery.toFixed(0)} TJS</strong></div>
          <div style={{ fontSize: '1.2rem', marginTop: 8 }}>Итого: <strong>{total.toFixed(0)} TJS</strong></div>
        </div>

        {error && <p className="error">{error}</p>}
        <button className="btn-accent" style={{ marginTop: 16, width: '100%' }} onClick={checkout} disabled={loading}>
          {loading ? 'Оформляем...' : 'Оформить заказ'}
        </button>
      </div>
    </div>
  )
}
