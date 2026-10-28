import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api, { Order } from '../services/api'
import { useI18n } from '../i18n'

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

export default function OrdersPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const navigate = useNavigate()
  const { t } = useI18n()

  const load = () => api.get('/orders').then((r) => setOrders(r.data)).catch(() => {})
  useEffect(() => {
    load()
    const id = setInterval(load, 4000)
    return () => clearInterval(id)
  }, [])

  const buyAgain = async (o: Order) => {
    const item = o.items?.[0]
    if (!item?.product_id) {
      // items may not expose product_id in type - try any
      const pid = (item as any)?.product_id
      if (!pid) return
      navigate(`/product/${pid}`)
      return
    }
    navigate(`/product/${item.product_id}`)
  }

  return (
    <div style={{ marginTop: 16 }}>
      <h1 className="section-title" style={{ marginTop: 0 }}>{t('orders')}</h1>
      {orders.length === 0 ? (
        <p className="empty-state">{t('noOrders')}</p>
      ) : (
        <div className="order-cards">
          {orders.map((o) => {
            const delivered = o.status === 'delivered'
            const name = o.items?.[0]?.product_name || o.order_number
            if (delivered) {
              return (
                <div key={o.id} className="order-card order-card-compact">
                  <div className="order-card-top">
                    <span className="order-num" style={{ fontSize: '0.9rem' }}>{name}</span>
                    <span className="status-pill status-delivered">{t('delivered')}</span>
                  </div>
                  <div className="order-card-meta">
                    <span className="order-sum">{Number(o.total).toFixed(0)} TJS</span>
                    <span className="hint">{o.order_number}</span>
                  </div>
                  <div className="compact-actions">
                    <Link to={`/orders/${o.id}`} className="link-btn">{t('review')}</Link>
                    <button type="button" className="link-btn" onClick={() => {
                      const pid = (o.items?.[0] as any)?.product_id
                      if (pid) navigate(`/product/${pid}`)
                      else navigate(`/orders/${o.id}`)
                    }}>{t('buyAgain')}</button>
                  </div>
                </div>
              )
            }
            return (
              <Link to={`/orders/${o.id}`} key={o.id} className="order-card">
                <div className="order-card-top">
                  <span className="order-num">{o.order_number}</span>
                  <span className={`status-pill status-${o.status}`}>{statusRu[o.status] || o.status}</span>
                </div>
                <div className="order-card-meta">
                  <span>{new Date(o.created_at).toLocaleDateString('ru')}</span>
                  <span className="order-sum">{Number(o.total).toFixed(0)} TJS</span>
                </div>
                <div className="order-card-action">Открыть →</div>
              </Link>
            )
          })}
        </div>
      )}
    </div>
  )
}
