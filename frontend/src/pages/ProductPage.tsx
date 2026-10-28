import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { mediaUrl } from '../services/media'
import api, { Product, PaymentMethod } from '../services/api'
import { useAuth } from '../App'
import { IconHeart, IconHeartFill, IconTruck, IconStore, IconBank, IconCard, IconStar, IconCheck, IconArrow } from '../components/Icons'

export default function ProductPage() {
  const { id } = useParams()
  const [product, setProduct] = useState<Product | null>(null)
  const [variantId, setVariantId] = useState<number | null>(null)
  const [qty, setQty] = useState(1)
  const [deliveryType, setDeliveryType] = useState<'home' | 'office' | null>(null)
  const [address, setAddress] = useState('')
  const [orderNote, setOrderNote] = useState('')
  const [zoneId, setZoneId] = useState<number | ''>('')
  const [zones, setZones] = useState<any[]>([])
  const [methods, setMethods] = useState<PaymentMethod[]>([])
  const [payId, setPayId] = useState<number | null>(null)
  const [step, setStep] = useState<'view' | 'delivery' | 'pay'>('view')
  const [msg, setMsg] = useState('')
  const [loading, setLoading] = useState(false)
  const [loadingProduct, setLoadingProduct] = useState(true)
  const [favorited, setFavorited] = useState(false)
  const [reviews, setReviews] = useState<any[]>([])
  const [comments, setComments] = useState<any[]>([])
  const [commentText, setCommentText] = useState('')
  const [rating, setRating] = useState(5)
  const [reviewFile, setReviewFile] = useState<File | null>(null)
  const [promoCode, setPromoCode] = useState('')
  const [promoDiscount, setPromoDiscount] = useState(0)
  const [promoMsg, setPromoMsg] = useState('')
  const [reviewText, setReviewText] = useState('')
  const [imgIdx, setImgIdx] = useState(0)
  const { user } = useAuth()
  const navigate = useNavigate()

  const loadExtra = () => {
    api.get(`/products/${id}/reviews`).then((r) => setReviews(r.data)).catch(() => {})
    api.get(`/products/${id}/comments`).then((r) => setComments(r.data)).catch(() => {})
    if (user) api.get(`/favorites/${id}/status`).then((r) => setFavorited(r.data.favorited)).catch(() => {})
  }

  useEffect(() => {
    api.get(`/products/${id}`).then((r) => setProduct(r.data)).catch(() => setProduct(null)).finally(() => setLoadingProduct(false))
    api.get('/orders/delivery-zones').then((r) => setZones(r.data))
    api.get('/orders/payment-methods').then((r) => {
      const list = (r.data || []).filter((m: any) => m.code === 'dc' || m.code === 'eskhata' || m.code === 'alif')
      setMethods(list)
      // auto-select first if only one
      if (list.length === 1) setPayId(list[0].id)
    })
    loadExtra()
  }, [id, user])

  if (loadingProduct) return <p className="hint">Загрузка…</p>
  if (!product) return <p className="empty-state">Товар не найден</p>

  const selectedVariant = product.variants?.find((v) => v.id === variantId)
  const unitPrice = Number(product.final_price) + (selectedVariant ? Number(selectedVariant.price_modifier) : 0)
  const zone = zones.find((z) => z.id === zoneId)
  const deliveryCost = 0  // сумму доставки укажет админ после оплаты
  const total = unitPrice * qty
  const images = product.images?.length ? product.images.map((im: any) => ({ ...im, url: mediaUrl(im.url) })) : [{ url: mediaUrl(null) }]
  const selectedPay = methods.find((m) => m.id === payId)

  const startOrder = () => {
    if (!user) { navigate('/login'); return }
    setStep('delivery')
    setMsg('')
  }

  const goPay = () => {
    if (!deliveryType) { setMsg('Выберите способ получения'); return }
    if (deliveryType === 'home' && (!address || !zoneId)) { setMsg('Укажите зону и адрес доставки'); return }
    setStep('pay')
    setMsg('')
  }

  const toggleFav = async () => {
    if (!user) { navigate('/login'); return }
    if (favorited) { await api.delete(`/favorites/${id}`); setFavorited(false) }
    else { await api.post(`/favorites/${id}`); setFavorited(true) }
  }

  const applyPromo = async () => {
    try {
      const sub = unitPrice * qty
      const r = await api.post('/promo/check', { code: promoCode, subtotal: sub })
      setPromoDiscount(r.data.discount || 0)
      setPromoMsg(r.data.message || 'OK')
    } catch (e: any) {
      setPromoDiscount(0)
      setPromoMsg(e.response?.data?.detail || 'Промокод недействителен')
    }
  }

  const placeOrder = async () => {
    if (!payId) { setMsg('Выберите способ оплаты: DC, Эсхата или TG Звёзды'); return }
    setLoading(true); setMsg('')
    try {
      const pay = methods.find((m) => m.id === payId)
      const r = await api.post('/orders', {
        product_id: product.id,
        variant_id: variantId || undefined,
        quantity: qty,
        delivery_type: deliveryType,
        delivery_address: deliveryType === 'home' ? address : undefined,
        delivery_zone_id: deliveryType === 'home' && zoneId ? zoneId : undefined,
        customer_comment: orderNote || undefined,
        payment_method_id: payId,
        payment_method_code: pay?.code || undefined,
        promo_code: promoCode || undefined,
        from_cart: false,
      })
      navigate(`/orders/${r.data.id}`)
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Ошибка оформления')
    } finally {
      setLoading(false)
    }
  }

  const sendComment = async () => {
    if (!user) { navigate('/login'); return }
    if (!commentText.trim()) return
    await api.post(`/products/${id}/comments`, { text: commentText.trim() })
    setCommentText(''); loadExtra()
  }

  const sendReview = async () => {
    if (!user) { navigate('/login'); return }
    try {
      if (reviewFile) {
        const fd = new FormData()
        fd.append('rating', String(rating))
        fd.append('text', reviewText || '')
        fd.append('file', reviewFile)
        await api.post(`/products/${id}/reviews/with-photo`, fd)
      } else {
        await api.post(`/products/${id}/reviews`, { rating, text: reviewText || undefined })
      }
      setReviewText(''); setReviewFile(null); setMsg('Отзыв добавлен'); loadExtra()
      const r = await api.get(`/products/${id}`); setProduct(r.data)
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Не удалось оставить отзыв')
    }
  }

  const payIcon = (code?: string) => {
    if (code === 'dc') return <IconBank size={22} />
    if (code === 'eskhata') return <IconCard size={22} />
    if (code === 'alif') return <IconCard size={22} />
    return <IconCard size={22} />
  }

  return (
    <div>
      <div className="product-detail">
        <div>
          <div className="glass-card" style={{ padding: 0, overflow: 'hidden' }}>
            <img src={images[imgIdx]?.url || images[0].url} alt={product.name_ru}
              style={{ width: '100%', aspectRatio: '1', objectFit: 'cover', background: '#eee' }} />
          </div>
          {images.length > 1 && (
            <div className="thumb-row">
              {images.map((im: any, i: number) => (
                <img key={i} src={im.url} alt="" onClick={() => setImgIdx(i)}
                  className={`thumb ${i === imgIdx ? 'active' : ''}`} />
              ))}
            </div>
          )}
          {(product.rating_count || 0) > 0 && (
            <p className="rating-line">⭐ <strong>{Number(product.rating_avg).toFixed(1)}</strong>
              <span> · {product.rating_count} отзывов</span></p>
          )}
        </div>

        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
            <h1 className="product-title">{product.name_ru}</h1>
            <button type="button" className="fav-btn" onClick={toggleFav}>{favorited ? <IconHeartFill size={22} /> : <IconHeart size={22} />}</button>
          </div>
          <div className="price-lg">
            {unitPrice.toFixed(0)} <span className="currency">TJS</span>
            {product.discount_percent > 0 && <span className="old">{Number(product.price).toFixed(0)}</span>}
          </div>
          {product.discount_percent > 0 && <span className="badge">🔥 -{product.discount_percent}%</span>}
          <p className="desc">{product.description_ru || 'Описание скоро появится'}</p>
          <p className="meta">📦 В наличии: {product.stock} шт.</p>

          {product.variants?.length > 0 && (
            <>
              <p className="label-sm">Вариант</p>
              <div className="variant-chips">
                {product.variants.map((v) => (
                  <button key={v.id} type="button" className={`chip ${variantId === v.id ? 'active' : ''}`}
                    onClick={() => setVariantId(v.id)}>{v.name}</button>
                ))}
              </div>
            </>
          )}

          <div className="form-group" style={{ maxWidth: 100, marginTop: 12 }}>
            <label>Кол-во</label>
            <input type="number" min={1} max={product.stock} value={qty}
              onChange={(e) => setQty(Number(e.target.value))} />
          </div>

          {step === 'view' && (
            <button className="btn-accent glow" style={{ marginTop: 16 }} onClick={startOrder} disabled={product.stock < 1}>
              Заказать
            </button>
          )}

          {step === 'delivery' && (
            <div className="glass-card order-box">
              <h3>Способ получения</h3>
              <div className="action-row">
                <button type="button" className={deliveryType === 'home' ? 'btn-accent' : 'btn-outline'}
                  onClick={() => setDeliveryType('home')}><> <IconTruck size={16}/> Доставка на дом </></button>
                <button type="button" className={deliveryType === 'office' ? 'btn-accent' : 'btn-outline'}
                  onClick={() => setDeliveryType('office')}><> <IconStore size={16}/> Забрать в магазине </></button>
              </div>
              <div className="form-group">
                <label>Что нужно (цвет, размер, модель…)</label>
                <textarea value={orderNote} onChange={(e) => setOrderNote(e.target.value)}
                  rows={3} placeholder="Например: чёрный, размер 42, без коробки" />
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
                </>
              )}
              {msg && <p className="error">{msg}</p>}
              <button className="btn-accent" style={{ marginTop: 12 }} onClick={goPay}>Далее → Оплата</button>
              <button type="button" className="link-btn" onClick={() => setStep('view')}>← Назад</button>
            </div>
          )}

          {step === 'pay' && (
            <div className="glass-card order-box">
              <h3>Способ оплаты</h3>
              <p className="hint">DC · Эсхата · Алиф</p>
              {methods.length === 0 && <p className="error">Способы оплаты не настроены. Админ добавит реквизиты.</p>}
              <div className="pay-list">
                {methods.map((m) => (
                  <button
                    key={m.id}
                    type="button"
                    className={`pay-card ${payId === m.id ? 'selected' : ''}`}
                    onClick={() => setPayId(m.id)}
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

              <div className="sum-box">
                <div>Товар: {(unitPrice * qty).toFixed(0)} TJS</div>
                <div className="hint">Доставка — после проверки оплаты (админ уточнит сумму)</div>
                <div className="sum-total">К оплате сейчас: {total.toFixed(0)} TJS</div>
              </div>
              {msg && <p className="error">{msg}</p>}
              <button className="btn-accent glow" onClick={placeOrder} disabled={loading || !payId}>
                {loading ? 'Оформляем…' : 'Перейти к оплате'}
              </button>
              <button type="button" className="link-btn" onClick={() => setStep('delivery')}>← Назад</button>
            </div>
          )}
        </div>
      </div>

      <h2 className="section-title">Обсуждение</h2>
      <div className="glass-card">
        <div className="chat-scroll">
          {comments.length === 0 && <p className="hint">Пока тихо — напишите первым ✨</p>}
          {comments.map((c) => (
            <div key={c.id} className="chat-item">
              <div className="chat-head">
                <strong>{c.user_name}</strong>
                {c.is_verified && <span className="v-badge">✓</span>}
                {c.is_staff && <span className="badge">VELORA</span>}
                <span className="chat-date">{c.created_at ? new Date(c.created_at).toLocaleDateString('ru') : ''}</span>
              </div>
              <p>{c.text}</p>
            </div>
          ))}
        </div>
        <div className="chat-input-row">
          <input placeholder={user ? 'Написать...' : 'Войдите, чтобы писать'} value={commentText}
            onChange={(e) => setCommentText(e.target.value)} disabled={!user}
            onKeyDown={(e) => e.key === 'Enter' && sendComment()} />
          <button className="btn-accent" style={{ width: 'auto', padding: '10px 16px' }} onClick={sendComment} disabled={!user}>➤</button>
        </div>
      </div>

      <h2 className="section-title">Отзывы</h2>
      <div className="glass-card">
        {reviews.length === 0 && <p className="hint">Отзывов пока нет</p>}
        {reviews.map((r) => (
          <div key={r.id} className="review-item">
            <div className="chat-head">
              <span className="stars">{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
              {r.image_url && <img src={r.image_url} alt="" className="review-img" />}
              <strong>{r.user_name}</strong>
              {r.is_verified_buyer && <span className="badge">Покупатель</span>}
            </div>
            {r.text && <p>{r.text}</p>}
          </div>
        ))}
        {user && (
          <div className="review-form">
            <p className="label-sm">Ваша оценка</p>
            <div className="star-pick">
              {[1, 2, 3, 4, 5].map((n) => (
                <button key={n} type="button" onClick={() => setRating(n)} className={n <= rating ? 'on' : ''}>★</button>
              ))}
            </div>
            <input type="file" accept="image/*" onChange={(e) => setReviewFile(e.target.files?.[0] || null)} />
            <textarea value={reviewText} onChange={(e) => setReviewText(e.target.value)}
              placeholder="Как вам товар? (после оплаченного заказа)" rows={3} />
            <button className="btn-accent" style={{ width: 'auto', padding: '10px 18px', marginTop: 8 }} onClick={sendReview}>
              Отправить отзыв
            </button>
          </div>
        )}
        {msg && step === 'view' && <p className="success">{msg}</p>}
      </div>
    </div>
  )
}
