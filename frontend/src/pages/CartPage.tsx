import React, { useEffect, useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import api, { Cart, PaymentMethod } from '../services/api'
import { mediaUrl } from '../services/media'
import { IconTruck, IconStore, IconBank, IconCard } from '../components/Icons'
import { useAuth } from '../App'

export default function CartPage() {
  const { user } = useAuth()
  const [cart, setCart] = useState<Cart | null>(null)
  const [zones, setZones] = useState<any[]>([])
  const [methods, setMethods] = useState<PaymentMethod[]>([])
  const [deliveryType, setDeliveryType] = useState<'home' | 'office' | null>(null)
  const [zoneId, setZoneId] = useState<number | ''>('')
  const [address, setAddress] = useState('')
  const [phone, setPhone] = useState('')
  const [orderNote, setOrderNote] = useState('')
  const [payId, setPayId] = useState<number | null>(null)
  const [step, setStep] = useState<'cart' | 'delivery' | 'pay'>('cart')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [promoCode, setPromoCode] = useState('')
  const [promoApplied, setPromoApplied] = useState<{ code: string; discount: number; message: string } | null>(null)
  const [promoChecking, setPromoChecking] = useState(false)
  const [promoError, setPromoError] = useState('')
  const [usePoints, setUsePoints] = useState(false)
  const navigate = useNavigate()

  const loyaltyPoints = Number((user as any)?.loyalty_points ?? 0)

  const load = () => api.get('/cart').then((r) => setCart(r.data)).catch(() => setCart(null))

  useEffect(() => {
    load()
    api.get('/orders/delivery-zones').then((r) => setZones(r.data))
    api.get('/orders/payment-methods').then((r) => {
      const list = (r.data || []).filter((m: any) => m.code === 'dc' || m.code === 'eskhata' || m.code === 'alif')
      setMethods(list)
      if (list.length === 1) setPayId(list[0].id)
    })
  }, [])

  const updateQty = async (itemId: number, quantity: number) => {
    if (quantity < 1) return
    await api.patch(`/cart/items/${itemId}?quantity=${quantity}`)
    load()
    setPromoApplied(null)
    setPromoError('')
  }

  const remove = async (itemId: number) => {
    await api.delete(`/cart/items/${itemId}`)
    load()
    setPromoApplied(null)
    setPromoError('')
  }

  const startCheckout = () => {
    if (!cart || cart.items.length === 0) return
    setStep('delivery')
    setError('')
  }

  const goPay = () => {
    if (!deliveryType) { setError('Выберите способ получения'); return }
    if (deliveryType === 'home' && (!address || !zoneId)) { setError('Укажите зону и адрес доставки'); return }
    setStep('pay')
    setError('')
  }

  const applyPromo = async () => {
    const code = promoCode.trim()
    if (!code) {
      setPromoError('Введите промокод')
      return
    }
    if (!cart) return
    setPromoChecking(true)
    setPromoError('')
    try {
      const r = await api.post('/promo/check', {
        code,
        subtotal: Number(cart.subtotal),
      })
      setPromoApplied({
        code: r.data.code,
        discount: Number(r.data.discount) || 0,
        message: r.data.message || `Скидка ${r.data.discount} TJS`,
      })
      setPromoError('')
    } catch (e: any) {
      setPromoApplied(null)
      setPromoError(e.response?.data?.detail || 'Промокод недействителен')
    } finally {
      setPromoChecking(false)
    }
  }

  const clearPromo = () => {
    setPromoCode('')
    setPromoApplied(null)
    setPromoError('')
  }

  const subtotal = cart ? Number(cart.subtotal) : 0
  const discount = promoApplied ? promoApplied.discount : 0
  const totalAfterPromo = Math.max(0, subtotal - discount)
  const canPayWithPoints = loyaltyPoints >= totalAfterPromo && totalAfterPromo > 0

  const checkout = async () => {
    if (usePoints) {
      if (!canPayWithPoints) {
        setError(`Недостаточно баллов. Нужно ${totalAfterPromo.toFixed(0)}, у вас ${loyaltyPoints}`)
        return
      }
    } else if (!payId) {
      setError('Выберите способ оплаты: DC, Эсхата или Алиф — или оплатите баллами')
      return
    }
    setLoading(true)
    setError('')
    try {
      const pay = methods.find((m) => m.id === payId)
      const body: any = {
        from_cart: true,
        delivery_type: deliveryType,
        delivery_address: deliveryType === 'home' ? address : undefined,
        delivery_zone_id: deliveryType === 'home' && zoneId ? zoneId : undefined,
        delivery_phone: phone || undefined,
        customer_comment: orderNote || undefined,
        payment_method_id: usePoints ? undefined : payId,
        payment_method_code: usePoints ? 'points' : (pay?.code || undefined),
        promo_code: promoApplied?.code || (promoCode.trim() || undefined),
        use_points: usePoints,
      }
      const r = await api.post('/orders', body)
      navigate(`/orders/${r.data.id}`)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Ошибка оформления')
    } finally {
      setLoading(false)
    }
  }

  const payIcon = (code?: string) => {
    if (code === 'dc') return <IconBank size={22} />
    if (code === 'eskhata') return <IconCard size={22} />
    if (code === 'alif') return <IconCard size={22} />
    return <IconCard size={22} />
  }

  if (!cart) return <p className="hint" style={{ padding: 40 }}>Загрузка...</p>
  if (cart.items.length === 0) {
    return (
      <div style={{ padding: '40px 16px', textAlign: 'center' }}>
        <p className="empty-state">Корзина пуста</p>
        <Link to="/" className="btn-accent" style={{ display: 'inline-block', marginTop: 16 }}>К каталогу</Link>
      </div>
    )
  }

  return (
    <div style={{ marginTop: 16, paddingBottom: 80 }}>
      <h1 style={{ color: 'var(--purple-deep)', marginBottom: 8 }}>Корзина</h1>
      <p className="hint" style={{ marginBottom: 16 }}>{cart.items_count} товар(ов) · {subtotal.toFixed(0)} TJS</p>

      {step === 'cart' && (
        <>
          <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
            {cart.items.map((i) => (
              <div
                key={i.id}
                style={{
                  display: 'flex',
                  gap: 12,
                  padding: '14px 16px',
                  borderBottom: '1px solid var(--border, #eee)',
                  alignItems: 'center',
                }}
              >
                {i.image_url && (
                  <img
                    src={mediaUrl(i.image_url)}
                    alt=""
                    style={{ width: 64, height: 64, objectFit: 'cover', borderRadius: 10, flexShrink: 0 }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 600, fontSize: '0.95rem' }}>{i.product_name}</div>
                  <div className="hint" style={{ marginTop: 2 }}>{Number(i.unit_price).toFixed(0)} TJS</div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                    <button
                      type="button"
                      className="btn-outline"
                      style={{ padding: '4px 10px', minWidth: 36 }}
                      onClick={() => updateQty(i.id, i.quantity - 1)}
                      disabled={i.quantity <= 1}
                    >
                      −
                    </button>
                    <span style={{ minWidth: 24, textAlign: 'center', fontWeight: 600 }}>{i.quantity}</span>
                    <button
                      type="button"
                      className="btn-outline"
                      style={{ padding: '4px 10px', minWidth: 36 }}
                      onClick={() => updateQty(i.id, i.quantity + 1)}
                    >
                      +
                    </button>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 700 }}>{Number(i.total_price).toFixed(0)} TJS</div>
                  <button type="button" className="link-btn" style={{ marginTop: 6, fontSize: '0.85rem' }} onClick={() => remove(i.id)}>
                    Удалить
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="glass-card sum-box" style={{ marginTop: 16 }}>
            <div>Товары: <strong>{subtotal.toFixed(0)} TJS</strong></div>
            <div className="hint">Доставка — после проверки оплаты (админ уточнит сумму)</div>
            <div className="sum-total">Итого сейчас: {subtotal.toFixed(0)} TJS</div>
          </div>

          <button className="btn-accent glow" style={{ marginTop: 16, width: '100%' }} onClick={startCheckout}>
            Оформить заказ
          </button>
        </>
      )}

      {step === 'delivery' && (
        <div className="glass-card order-box">
          <h3>Способ получения</h3>
          <div className="action-row">
            <button
              type="button"
              className={deliveryType === 'home' ? 'btn-accent' : 'btn-outline'}
              onClick={() => setDeliveryType('home')}
            >
              <IconTruck size={16} /> Доставка на дом
            </button>
            <button
              type="button"
              className={deliveryType === 'office' ? 'btn-accent' : 'btn-outline'}
              onClick={() => setDeliveryType('office')}
            >
              <IconStore size={16} /> Забрать в магазине
            </button>
          </div>
          <div className="form-group" style={{ marginTop: 12 }}>
            <label>Комментарий к заказу (цвет, размер…)</label>
            <textarea
              value={orderNote}
              onChange={(e) => setOrderNote(e.target.value)}
              rows={2}
              placeholder="Например: чёрный, размер 42"
            />
          </div>
          {deliveryType === 'home' && (
            <>
              <div className="form-group" style={{ marginTop: 12 }}>
                <label>Район доставки</label>
                <select value={zoneId} onChange={(e) => setZoneId(Number(e.target.value) || '')}>
                  <option value="">Выберите...</option>
                  {zones.map((z) => (
                    <option key={z.id} value={z.id}>{z.name}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Адрес</label>
                <input value={address} onChange={(e) => setAddress(e.target.value)} placeholder="Улица, дом, квартира" />
              </div>
              <div className="form-group">
                <label>Телефон</label>
                <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+992..." />
              </div>
            </>
          )}
          {error && <p className="error">{error}</p>}
          <button className="btn-accent" style={{ marginTop: 12, width: '100%' }} onClick={goPay}>
            Далее → Оплата
          </button>
          <button type="button" className="link-btn" onClick={() => setStep('cart')}>← Назад к корзине</button>
        </div>
      )}

      {step === 'pay' && (
        <div className="glass-card order-box">
          <h3>Способ оплаты</h3>
          <p className="hint">DC · Эсхата · Алиф · или баллами</p>
          {methods.length === 0 && !canPayWithPoints && (
            <p className="error">Способы оплаты не настроены. Админ добавит реквизиты.</p>
          )}

          {/* Promo code — две строки: ввод + кнопка */}
          <div className="form-group" style={{ marginTop: 12, marginBottom: 12 }}>
            <label>Промокод (необязательно)</label>
            <input
              value={promoCode}
              onChange={(e) => {
                setPromoCode(e.target.value.toUpperCase())
                if (promoApplied) {
                  setPromoApplied(null)
                  setPromoError('')
                }
              }}
              placeholder="Введите промокод"
              disabled={!!promoApplied}
              autoComplete="off"
              style={{
                width: '100%',
                boxSizing: 'border-box',
                padding: '12px 14px',
                borderRadius: 12,
                border: '1.5px solid var(--purple-mid, #7c3aed)',
                background: '#fff',
                color: '#1a1a1a',
                fontSize: 16,
                fontWeight: 600,
                letterSpacing: '0.04em',
              }}
            />
            {!promoApplied ? (
              <button
                type="button"
                className="btn-outline"
                style={{ width: '100%', marginTop: 8, padding: '12px 14px' }}
                onClick={applyPromo}
                disabled={promoChecking || !promoCode.trim()}
              >
                {promoChecking ? 'Проверяем…' : 'Применить'}
              </button>
            ) : (
              <button
                type="button"
                className="link-btn"
                style={{ marginTop: 8 }}
                onClick={clearPromo}
              >
                Сбросить промокод
              </button>
            )}
            {promoError && <p className="error" style={{ marginTop: 6 }}>{promoError}</p>}
            {promoApplied && (
              <p className="success" style={{ marginTop: 6 }}>
                ✓ {promoApplied.message} ({promoApplied.code})
              </p>
            )}
          </div>

          {/* Pay with points */}
          {loyaltyPoints > 0 && (
            <div
              className={`pay-card ${usePoints ? 'selected' : ''}`}
              style={{ marginBottom: 12, cursor: canPayWithPoints ? 'pointer' : 'not-allowed', opacity: canPayWithPoints ? 1 : 0.55 }}
              onClick={() => {
                if (!canPayWithPoints) return
                setUsePoints(true)
                setPayId(null)
              }}
            >
              <span className="pay-icon">⭐</span>
              <span className="pay-body">
                <strong>Оплатить баллами</strong>
                <small>
                  У вас {loyaltyPoints} баллов (1 балл = 1 TJS).
                  {canPayWithPoints
                    ? ` Хватит на этот заказ (${totalAfterPromo.toFixed(0)} TJS).`
                    : ` Нужно ещё ${(totalAfterPromo - loyaltyPoints).toFixed(0)} баллов.`}
                </small>
              </span>
              <span className="pay-check">{usePoints ? '✓' : ''}</span>
            </div>
          )}

          {!usePoints && (
            <div className="pay-list">
              {methods.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  className={`pay-card ${payId === m.id ? 'selected' : ''}`}
                  onClick={() => {
                    setPayId(m.id)
                    setUsePoints(false)
                  }}
                >
                  <span className="pay-icon">{payIcon(m.code)}</span>
                  <span className="pay-body">
                    <strong>{m.name}</strong>
                    <small>{m.instructions}</small>
                    {m.account_number && <small className="mono">{m.account_number}</small>}
                  </span>
                  <span className="pay-check">{payId === m.id ? '✓' : ''}</span>
                </button>
              ))}
            </div>
          )}

          {usePoints && (
            <button type="button" className="link-btn" style={{ marginBottom: 8 }} onClick={() => setUsePoints(false)}>
              ← Выбрать банковскую оплату
            </button>
          )}

          <div className="sum-box">
            <div>Товары: {subtotal.toFixed(0)} TJS</div>
            {discount > 0 && (
              <div style={{ color: 'var(--success, #1a7a4c)' }}>Скидка по промокоду: −{discount.toFixed(0)} TJS</div>
            )}
            <div className="hint">Доставка — после проверки оплаты (админ уточнит сумму)</div>
            <div className="sum-total">
              К оплате сейчас:{' '}
              {usePoints
                ? `${totalAfterPromo.toFixed(0)} баллов`
                : `${totalAfterPromo.toFixed(0)} TJS`}
            </div>
          </div>
          {error && <p className="error">{error}</p>}
          <button
            className="btn-accent glow"
            style={{ width: '100%' }}
            onClick={checkout}
            disabled={loading || (!usePoints && !payId)}
          >
            {loading
              ? 'Оформляем…'
              : usePoints
                ? `Оплатить ${totalAfterPromo.toFixed(0)} баллами`
                : 'Перейти к оплате'}
          </button>
          <button type="button" className="link-btn" onClick={() => setStep('delivery')}>← Назад</button>
        </div>
      )}
    </div>
  )
}
