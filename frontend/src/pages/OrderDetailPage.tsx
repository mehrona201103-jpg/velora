import { useEffect, useState, useRef } from 'react'
import { useParams, Link } from 'react-router-dom'
import api, { Order, PaymentMethod } from '../services/api'
import { IconCheck, IconCard, IconBank, IconStar } from '../components/Icons'

const statusRu: Record<string, string> = {
  awaiting_payment: 'Заявка',
  payment_review: 'Проверка чека',
  paid: 'Чек одобрен',
  processing: 'Упакован',
  ordered_from_supplier: 'Упакован',
  in_transit: 'У курьера',
  arrived_in_tajikistan: 'Упакован',
  ready_for_pickup: 'Упакован',
  out_for_delivery: 'У курьера',
  delivered: 'Доставлен',
  cancelled: 'Отменён',
  refunded: 'Возврат',
}

export default function OrderDetailPage() {
  const { id } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [methods, setMethods] = useState<PaymentMethod[]>([])
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [file, setFile] = useState<File | null>(null)
  const [msg, setMsg] = useState('')
  const [celebrate, setCelebrate] = useState(false)
  const celebShown = useRef(false)
  const [live, setLive] = useState(true)
  const lastStatus = useRef('')

  const load = () =>
    api.get(`/orders/${id}`).then((r) => {
      const o = r.data as Order
      if (lastStatus.current && lastStatus.current !== o.status) {
        setMsg(`Статус: ${statusRu[o.status] || o.status}`)
      }
      lastStatus.current = o.status
      setOrder(o)
    })

  useEffect(() => {
    load()
    api.get('/orders/payment-methods').then((r) => setMethods((r.data || []).filter((m: any) => m.code === 'dc' || m.code === 'eskhata' || m.code === 'alif')))
    api.get('/orders/settings/public').then((r) => setSettings(r.data)).catch(() => {})
  }, [id])

  useEffect(() => {
    if (!order) return
    const done = ['delivered', 'cancelled', 'refunded'].includes(order.status)
    if (done) { setLive(false); return }
    setLive(true)
    const t = setInterval(() => { load().catch(() => {}) }, 4000)
    return () => clearInterval(t)
  }, [order?.status, id])

  const upload = async () => {
    if (!file) return
    const fd = new FormData()
    fd.append('file', file)
    try {
      await api.post(`/orders/${id}/payment-receipt`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setMsg('Чек отправлен. Ждите проверки.')
      await load()
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Ошибка')
    }
  }

  const respondDelivery = async (accept: boolean) => {
    try {
      const r = await api.post(`/orders/${id}/delivery-response`, null, { params: { accept } })
      setMsg(r.data.message)
      await load()
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Ошибка')
    }
  }

  if (!order) return <p className="hint">Загрузка…</p>


  const TRACK = [
    { key: 'awaiting_payment', label: 'Заявка' },
    { key: 'payment_review', label: 'Проверка' },
    { key: 'paid', label: 'Одобрено' },
    { key: 'processing', label: 'Упакован' },
    { key: 'out_for_delivery', label: 'У курьера' },
    { key: 'delivered', label: 'Доставлен' },
  ]
  const trackIdx = Math.max(0, TRACK.findIndex((s) => s.key === order.status))


  const needPay = ['unpaid', 'rejected'].includes(order.payment_status)
  const isPaid = order.payment_status === 'paid'
  const method = methods.find((m) => m.id === order.payment_method_id) || methods[0]

  const payIcon = (code?: string) => {
    if (code === 'dc') return <IconBank size={22} />
    if (code === 'eskhata') return <IconCard size={22} />
    if (code === 'alif') return <IconCard size={22} />
    return <IconCard size={22} />
  }

  return (
    <div style={{ marginTop: 16, maxWidth: 640 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        {live && <span className="live-dot" />}
        <h1 style={{ color: 'var(--purple-deep)', fontSize: '1.15rem', margin: 0 }}>
          {order.order_number}
      {celebrate && (
        <div className="pay-success-overlay">
          <div className="pay-success-ring">
            <div className="pay-success-check">✓</div>
          </div>
          <div className="pay-success-text">Доставлено!</div>
        </div>
      )}
        </h1>
      </div>
      <p>Статус: <strong>{statusRu[order.status] || order.status}</strong></p>
      {order.status !== 'cancelled' && order.status !== 'refunded' && order.status !== 'delivered' && (
        <div className="track-bar">
          {TRACK.map((s, i) => (
            <div key={s.key} className={`track-step ${i <= trackIdx ? 'done' : ''} ${i === trackIdx ? 'current' : ''}`}>
              <div className="track-dot" />
              <div className="track-label">{s.label}</div>
            </div>
          ))}
        </div>
      )}
      <p>Оплата: <strong>{order.payment_status === 'unpaid' ? 'не оплачен' : order.payment_status === 'awaiting_review' ? 'на проверке' : order.payment_status === 'paid' ? 'оплачен' : order.payment_status}</strong></p>
      {order.payment_rejection_reason && <p className="error">{order.payment_rejection_reason}</p>}

      {isPaid && order.delivery_quote_status !== 'quoted' && (
        <div className="glass-card" style={{ margin: '14px 0', background: '#ecfdf5' }}>
          <p style={{ fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
            <IconCheck size={18} /> Оплата подтверждена
          </p>
          <p style={{ fontSize: '0.9rem', marginTop: 6 }}>Следите за статусом в приложении. Новости магазина — в Instagram.</p>
          {(settings.instagram_url || settings.telegram_channel_url) && (
            <a href={settings.instagram_url || settings.telegram_channel_url} target="_blank" rel="noreferrer" className="btn-accent" style={{ display: 'inline-block', marginTop: 10, width: 'auto', padding: '10px 18px' }}>
              Открыть Instagram
            </a>
          )}
        </div>
      )}

      {order.delivery_quote_status === 'quoted' && (
        <>
        <p className="hint">Админ указал сумму доставки. Подтвердите, чтобы заказ перешёл к упаковке.</p>

        <div className="glass-card" style={{ margin: '14px 0' }}>
          <h3>Сумма доставки</h3>
          <p style={{ fontSize: '1.2rem', fontWeight: 800 }}>{Number(order.delivery_cost).toFixed(0)} TJS</p>
          <p className="hint">Итого с доставкой: {Number(order.total).toFixed(0)} TJS</p>
          <div className="status-btns" style={{ marginTop: 12 }}>
            <button type="button" className="sbtn ok" onClick={() => respondDelivery(true)}>Согласен</button>
            <button type="button" className="sbtn bad" onClick={() => respondDelivery(false)}>Отказ</button>
          </div>
        </div>
        </>
      )}

      {order.delivery_quote_status === 'accepted' && (
        <p className="success">Доставка подтверждена. Заказ будет упакован и передан курьеру.</p>
      )}

      <h3 style={{ marginTop: 18 }}>Товары</h3>
      <ul style={{ margin: '8px 0', paddingLeft: 18 }}>
        {order.items.map((i, idx) => (
          <li key={idx}>{i.product_name} × {i.quantity} = {Number(i.total_price).toFixed(0)} TJS</li>
        ))}
      </ul>
      <p>
        Товары {Number(order.subtotal).toFixed(0)} TJS
        {Number(order.delivery_cost) > 0 && <> + доставка {Number(order.delivery_cost).toFixed(0)} TJS</>}
        {' = '}<strong>{Number(order.total).toFixed(0)} TJS</strong>
      </p>
      <p className="hint">{order.delivery_city}, {order.delivery_address}</p>

      {needPay && method && (
        <div className="glass-card" style={{ marginTop: 18 }}>
          <h3>Оплата {Number(order.subtotal).toFixed(0)} TJS</h3>
          <p className="hint">Доставка рассчитывается отдельно после проверки оплаты</p>
          <div className="pay-card selected" style={{ marginTop: 10, cursor: 'default' }}>
            <span className="pay-icon">{payIcon(method.code)}</span>
            <span className="pay-body">
              <strong>{method.name}</strong>
              {method.recipient_name && <small>Получатель: {method.recipient_name}</small>}
              {method.account_number && <small className="mono">{method.account_number}</small>}
              <small>{method.instructions}</small>
            </span>
          </div>
          <p className="hint" style={{ marginTop: 12 }}>Загрузите скриншот оплаты</p>
          <input type="file" accept="image/*,.pdf" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          <button className="btn-accent" style={{ marginTop: 12 }} onClick={upload} disabled={!file}>
            Подтвердить оплату
          </button>
        </div>
      )}

      {order.payment_status === 'awaiting_review' && (
        <p className="success" style={{ marginTop: 16 }}><span className="live-dot" /> Чек на проверке</p>
      )}

      {msg && <p className="success">{msg}</p>}
      {order.status === 'delivered' && (
        <div className="glass-card" style={{ marginTop: 16, textAlign: 'center' }}>
          <p className="success" style={{ marginBottom: 12 }}>Заказ получен. Спасибо за покупку!</p>
          <div className="action-row" style={{ justifyContent: 'center', gap: 10, flexWrap: 'wrap' }}>
            {(order.items || []).map((it: any) => it.product_id && (
              <Link key={it.product_id} to={`/product/${it.product_id}`} className="btn-accent" style={{ width: 'auto', padding: '10px 16px' }}>
                Смотреть товар
              </Link>
            ))}
            {(order.items || [])[0]?.product_id && (
              <Link to={`/product/${(order.items as any)[0].product_id}`} className="btn-outline" style={{ width: 'auto', padding: '10px 16px' }}>
                Купить снова
              </Link>
            )}
          </div>
        </div>
      )}
      {settings.telegram_admin_dm && (
        <a href={settings.telegram_admin_dm} target="_blank" rel="noreferrer" className="btn-outline" style={{ display: 'block', textAlign: 'center', marginTop: 16 }}>
          Написать в поддержку
        </a>
      )}

      <h3 style={{ marginTop: 22 }}>История</h3>
      {order.status_history?.map((h, i) => (
        <div key={i} className="timeline-item" style={{ fontSize: '0.88rem', marginBottom: 8 }}>
          {new Date(h.created_at).toLocaleString('ru')} — {statusRu[h.status] || h.status}
          {h.comment && <div className="hint">{h.comment}</div>}
        </div>
      ))}
    </div>
  )
}
