import { useEffect, useState } from 'react'
import api, { Order } from '../services/api'

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

// Simplified flow: заявка/чек → сумма доставки → упакован → у курьера → доставлено
const STATUS_FLOW = [
  { key: 'processing', label: 'Упакован' },
  { key: 'out_for_delivery', label: 'У курьера' },
  { key: 'delivered', label: 'Доставлен' },
]

export default function AdminPage() {
  const [orders, setOrders] = useState<Order[]>([])
  const [tab, setTab] = useState('orders')
  const [zones, setZones] = useState<any[]>([])
  const [methods, setMethods] = useState<any[]>([])
  const [verifs, setVerifs] = useState<any[]>([])
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [msg, setMsg] = useState('')
  const [analytics, setAnalytics] = useState<any>(null)
  const [receipts, setReceipts] = useState<any[]>([])
  const [viewOrderId, setViewOrderId] = useState<number | null>(null)
  const [receiptPreview, setReceiptPreview] = useState<string | null>(null)

  const [sku, setSku] = useState('')
  const [name, setName] = useState('')
  const [price, setPrice] = useState('')
  const [discount, setDiscount] = useState('0')
  const [purchasePrice, setPurchasePrice] = useState('')
  const [stock, setStock] = useState('10')
  const [desc, setDesc] = useState('')
  const [imgUrls, setImgUrls] = useState('')
  const [productFiles, setProductFiles] = useState<FileList | null>(null)
  const [categories, setCategories] = useState<any[]>([])
  const [categoryId, setCategoryId] = useState('')
  const [productsList, setProductsList] = useState<any[]>([])

  const [zName, setZName] = useState('')
  const [zCity, setZCity] = useState('')
  const [zPrice, setZPrice] = useState('0')

  const [editPm, setEditPm] = useState<Record<number, any>>({})
  const [deliveryQuote, setDeliveryQuote] = useState<Record<number, string>>({})
  const [users, setUsers] = useState<any[]>([])
  const [userQuery, setUserQuery] = useState('')
  const [promos, setPromos] = useState<any[]>([])
  const [promoForm, setPromoForm] = useState({ code: '', discount_percent: '10', discount_fixed: '0', max_uses: '0' })
  const [orderSearch, setOrderSearch] = useState('')
  const [payUnlocked, setPayUnlocked] = useState(false)
  const [payPin, setPayPin] = useState('')
  const [bannerFiles, setBannerFiles] = useState<FileList | null>(null)
  const [broadcastText, setBroadcastText] = useState('')
  const lastAwaitRef = useState(0)[0]
  const awaitRef = (window as any).__veloraAwait || { n: -1 }
  ;(window as any).__veloraAwait = awaitRef

  const loadOrders = () => api.get('/admin/orders', { params: { q: orderSearch || undefined } }).then((r) => {
      const list = (r.data || []).filter((o: any) => orderSearch ? true : o.status !== 'cancelled')
      const awaiting = list.filter((o: any) => o.payment_status === 'awaiting_review').length
      if (awaitRef.n >= 0 && awaiting > awaitRef.n) {
        try {
          const ctx = new (window.AudioContext || (window as any).webkitAudioContext)()
          const o = ctx.createOscillator(); const g = ctx.createGain()
          o.connect(g); g.connect(ctx.destination)
          o.frequency.value = 880; g.gain.value = 0.05; o.start(); o.stop(ctx.currentTime + 0.15)
        } catch {}
      }
      awaitRef.n = awaiting
      setOrders(list)
    }).catch(() => {})
  const loadZones = () => api.get('/admin/delivery-zones').then((r) => setZones(r.data)).catch(() => {})
  const loadMethods = () => api.get('/admin/payment-methods').then((r) => {
    const list = (r.data || []).filter((m: any) => m.code === 'dc' || m.code === 'eskhata' || m.code === 'alif')
    setMethods(list)
    const map: Record<number, any> = {}
    list.forEach((m: any) => {
      map[m.id] = {
        recipient_name: m.recipient_name || '',
        account_number: m.account_number || '',
        instructions: m.instructions || '',
        tg_deep_link: m.tg_deep_link || '',
        tg_username: m.tg_username || '',
        stars_per_usd: m.stars_per_usd || 100,
      }
    })
    setEditPm(map)
  }).catch(() => {})
  const loadVerifs = () => api.get('/admin/verifications').then((r) => setVerifs(r.data)).catch(() => {})
  const loadSettings = () => api.get('/admin/settings').then((r) => setSettings(r.data)).catch(() => {})
  const loadAnalytics = () => api.get('/admin/analytics/dashboard').then((r) => setAnalytics(r.data)).catch(() => {})
  const loadPromos = () => api.get('/promo/admin/list').then((r) => setPromos(r.data)).catch(() => {})
  const loadUsers = () => api.get('/admin/users').then((r) => setUsers(r.data)).catch(() => {})
  const loadProducts = () => api.get('/products', { params: { page_size: 100 } }).then((r) => setProductsList(r.data.items || [])).catch(() => {})
  const loadCategories = () => api.get('/products/categories').then((r) => setCategories(r.data || [])).catch(() => {})

  useEffect(() => {
    loadOrders(); loadZones(); loadMethods(); loadVerifs(); loadSettings(); loadAnalytics(); loadProducts(); loadCategories(); loadUsers(); loadPromos()
  }, [])

  // Live updates without refresh
  useEffect(() => {
    const tick = () => {
      if (tab === 'orders' || tab === 'stats') loadOrders()
      if (tab === 'stats') loadAnalytics()
      if (tab === 'users') loadUsers()
      if (tab === 'verif') loadVerifs()
    }
    const id = setInterval(tick, 2000)
    return () => clearInterval(id)
  }, [tab])

  const openReceipts = async (orderId: number) => {
    setViewOrderId(orderId)
    setReceiptPreview(null)
    const r = await api.get(`/admin/orders/${orderId}/receipts`)
    setReceipts(r.data)
    if (r.data && r.data[0]) {
      try {
        const br = await api.get(`/admin/receipts/${r.data[0].id}`, { responseType: 'blob' })
        setReceiptPreview(URL.createObjectURL(br.data))
      } catch { setMsg('Не удалось открыть чек') }
    }
  }

  const viewReceipt = async (submissionId: number) => {
    try {
      const r = await api.get(`/admin/receipts/${submissionId}`, { responseType: 'blob' })
      const url = URL.createObjectURL(r.data)
      setReceiptPreview(url)
    } catch {
      setMsg('Не удалось открыть чек')
    }
  }

  const review = async (orderId: number, approve: boolean) => {
    const reason = approve ? undefined : prompt('Причина отклонения:') || 'Отклонено'
    const r = await api.post(`/admin/orders/${orderId}/review-payment`, { approve, reason })
    setMsg(r.data.message || (approve ? 'Оплата подтверждена' : 'Отклонено'))
    loadOrders()
    setViewOrderId(null)
  }

  const setStatus = async (orderId: number, status: string) => {
    await api.post(`/admin/orders/${orderId}/status`, { status })
    setMsg('Статус обновлён')
    loadOrders()
  }

  const sendDeliveryQuote = async (orderId: number) => {
    const amount = Number(deliveryQuote[orderId] || 0)
    if (isNaN(amount) || amount < 0) { setMsg('Укажите сумму доставки'); return }
    try {
      const r = await api.post(`/admin/orders/${orderId}/delivery-quote`, { amount })
      setMsg(r.data.message || `Доставка ${amount} TJS отправлена клиенту`)
      setDeliveryQuote({ ...deliveryQuote, [orderId]: '' })
      loadOrders()
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Не удалось отправить сумму доставки')
    }
  }

  const cancelOrder = async (orderId: number) => {
    if (!confirm('Отменить заказ? Товар вернётся на склад.')) return
    try {
      await api.post(`/admin/orders/${orderId}/status`, { status: 'cancelled' })
      setMsg('Заказ отменён')
      loadOrders()
    } catch (e: any) {
      setMsg(e.response?.data?.detail || 'Ошибка отмены')
    }
  }

  const savePm = async (id: number) => {
    const data = editPm[id]
    await api.patch(`/admin/payment-methods/${id}`, data)
    setMsg('Реквизиты сохранены')
    loadMethods()
  }

  const createProduct = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const r = await api.post('/admin/products', {
        sku, name_ru: name, description_ru: desc,
        price: Number(price),
        purchase_price: purchasePrice ? Number(purchasePrice) : 0,
        discount_percent: Number(discount) || 0,
        stock: Number(stock) || 0,
        is_published: true,
        image_urls: imgUrls.split('\n').map((s) => s.trim()).filter(Boolean).slice(0, 10),
        category_id: categoryId ? Number(categoryId) : null,
      })
      const pid = r.data.id
      if (productFiles && productFiles.length > 0) {
        const fd = new FormData()
        Array.from(productFiles).slice(0, 10).forEach((f) => fd.append('files', f))
        await api.post(`/admin/products/${pid}/images`, fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      }
      setDiscount('0'); setPurchasePrice(''); setStock('10'); loadProducts()
      setMsg('Товар опубликован')
      setSku(''); setName(''); setPrice(''); setDesc(''); setImgUrls(''); setProductFiles(null); setCategoryId('')
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'Ошибка')
    }
  }

  const createZone = async (e: React.FormEvent) => {
    e.preventDefault()
    await api.post('/admin/delivery-zones', { name: zName, city: zCity || zName, base_price: Number(zPrice) || 0 })
    setMsg('Район добавлен'); loadZones(); setZName(''); setZCity('')
  }

  const saveSettingKey = async (key: string, value: string) => {
    await api.post('/admin/settings', { key, value })
    setMsg('Сохранено')
    loadSettings()
  }

  const reviewVerif = async (userId: number, approve: boolean) => {
    const reason = approve ? undefined : prompt('Причина:') || 'Отклонено'
    await api.post(`/admin/verifications/${userId}`, { approve, reason })
    setMsg(approve ? 'Подтверждено' : 'Отклонено')
    loadVerifs()
  }

  const tabs = [
    ['orders', 'Заказы'],
    ['stats', 'Статистика'],
    ['products', 'Товары'],
    ['pay', 'Оплата'],
    ['zones', 'Районы'],
    ['verif', 'Идентификация'],
    ['promo', 'Промокоды'],
    ['users', 'Пользователи'],
    ['broadcast', 'Рассылка'],
    ['settings', 'Настройки'],
  ]

  return (
    <div className="admin-layout">
      <nav className="admin-nav">
        {tabs.map(([id, label]) => (
          <a key={id} href="#" className={tab === id ? 'active' : ''} onClick={(e) => { e.preventDefault(); setTab(id) }}>{label}</a>
        ))}
      </nav>
      <div>
        <h1 style={{ color: 'var(--purple-deep)', fontSize: '1.3rem' }}>Админ VELORA</h1>
        {msg && <p className="success">{msg}</p>}

        {tab === 'stats' && analytics && (
          <div>
            <div className="stats-grid">
              <div className="stat-card"><div className="num">{analytics.total_products}</div><div className="lbl">Товаров</div></div>
              <div className="stat-card"><div className="num">{analytics.orders_paid}</div><div className="lbl">Оплачено (всё время)</div></div>
              <div className="stat-card"><div className="num">{Number(analytics.revenue_tjs || 0).toFixed(0)}</div><div className="lbl">Выручка (цена)</div></div>
              <div className="stat-card"><div className="num">{Number(analytics.cost_tjs || 0).toFixed(0)}</div><div className="lbl">Закупка</div></div>
              <div className="stat-card"><div className="num">{Number(analytics.profit_tjs || 0).toFixed(0)}</div><div className="lbl">Прибыль</div></div>
              <div className="stat-card"><div className="num">{Number(analytics.month_revenue_tjs || 0).toFixed(0)}</div><div className="lbl">Выручка {analytics.month_label || ''}</div></div>
              <div className="stat-card"><div className="num">{Number(analytics.month_profit_tjs || 0).toFixed(0)}</div><div className="lbl">Прибыль {analytics.month_label || ''}</div></div>
              <div className="stat-card"><div className="num">{analytics.orders_awaiting_review}</div><div className="lbl">Ждут чек</div></div>
              <div className="stat-card"><div className="num">{analytics.total_customers}</div><div className="lbl">Клиентов</div></div>
              <div className="stat-card"><div className="num">{analytics.orders_total}</div><div className="lbl">Всего заказов</div></div>
            </div>
            <div style={{ margin: '12px 0 20px' }}>
              <button type="button" className="sbtn ok" onClick={async () => {
                try {
                  const r = await api.get('/admin/analytics/month-report')
                  const d = r.data
                  const w = window.open('', '_blank')
                  if (!w) return
                  const rows = (d.orders || []).map((o: any) => {
                    const items = (o.items || []).map((i: any) => i.name + (i.variant ? ' ' + i.variant : '') + '×' + i.qty).join('; ')
                    const dt = o.created_at ? new Date(o.created_at).toLocaleString('ru') : ''
                    return '<tr><td>' + o.order_number + '</td><td>' + o.total + '</td><td>' + items + '</td><td>' + dt + '</td></tr>'
                  }).join('')
                  const html = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>VELORA ' + d.period + '</title>' +
                    '<style>body{font-family:system-ui;padding:24px}h1{letter-spacing:.2em}table{width:100%;border-collapse:collapse;margin-top:16px}td,th{border:1px solid #ddd;padding:8px;font-size:13px;text-align:left}.s{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}.s div{background:#faf8f6;padding:12px 16px;border-radius:10px}</style></head>' +
                    '<body><h1>VELORA</h1><p>Отчёт за <b>' + d.period + '</b></p>' +
                    '<div class="s"><div>Оплачено: <b>' + d.orders_paid + '</b></div><div>Выручка: <b>' + Number(d.revenue_tjs).toFixed(0) + ' TJS</b></div>' +
                    '<div>Закупка: <b>' + Number(d.cost_tjs).toFixed(0) + ' TJS</b></div><div>Прибыль: <b>' + Number(d.profit_tjs).toFixed(0) + ' TJS</b></div></div>' +
                    '<table><thead><tr><th>Заказ</th><th>Сумма</th><th>Товары</th><th>Дата</th></tr></thead><tbody>' + rows + '</tbody></table>' +
                    '<p style="margin-top:24px;color:#888">Ctrl+P → Сохранить как PDF</p></body></html>'
                  w.document.write(html)
                  w.document.close()
                  setTimeout(() => { try { w.print() } catch(e) {} }, 400)
                } catch { setMsg('Не удалось загрузить отчёт') }
              }}>Скачать PDF за текущий месяц</button>
              <p className="hint">Месяц с 1-го числа. В печати выберите «Сохранить как PDF».</p>
            </div>

            <div className="charts-row">
              <div className="chart-card">
                <h3>Статусы заказов</h3>
                <div className="pie-wrap">
                  <svg viewBox="0 0 32 32" className="pie-svg">
                    {(() => {
                      const entries = Object.entries(analytics.orders_by_status || {})
                      const total = entries.reduce((s, [, c]) => s + Number(c), 0) || 1
                      const colors = ['#7c3aed', '#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#14b8a6', '#ec4899']
                      let offset = 0
                      return entries.map(([name, count], i) => {
                        const val = (Number(count) / total) * 100
                        const circ = 2 * Math.PI * 10
                        const dash = (val / 100) * circ
                        const el = (
                          <circle key={name} r="10" cx="16" cy="16" fill="transparent"
                            stroke={colors[i % colors.length]} strokeWidth="4"
                            strokeDasharray={`${dash} ${circ - dash}`}
                            strokeDashoffset={-offset}
                            style={{ transform: 'rotate(-90deg)', transformOrigin: '16px 16px' }}
                          />
                        )
                        offset += dash
                        return el
                      })
                    })()}
                  </svg>
                  <div className="pie-legend">
                    {Object.entries(analytics.orders_by_status || {}).map(([name, count], i) => {
                      const colors = ['#7c3aed', '#10b981', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#14b8a6', '#ec4899']
                      return (
                        <div key={name}><span className="dot" style={{ background: colors[i % colors.length] }} />{name}: {count as number}</div>
                      )
                    })}
                  </div>
                </div>
              </div>

              <div className="chart-card">
                <h3>Регистрации за 7 дней</h3>
                <div className="bar-chart">
                  {(analytics.registrations_7d || []).map((d: any) => {
                    const max = Math.max(...(analytics.registrations_7d || []).map((x: any) => x.count), 1)
                    return (
                      <div className="bar-row" key={d.day}>
                        <span>{d.day}</span>
                        <div className="bar-track"><div className="bar-fill" style={{ width: `${(d.count / max) * 100}%` }} /></div>
                        <span>{d.count}</span>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>

            <h3 style={{ marginTop: 16 }}>Топ продаж</h3>
            <div className="bar-chart">
              {(analytics.top_products || []).map((p: any) => {
                const max = Math.max(...(analytics.top_products.map((x: any) => x.qty) || [1]), 1)
                return (
                  <div className="bar-row" key={p.name}>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.name}</span>
                    <div className="bar-track"><div className="bar-fill" style={{ width: `${(p.qty / max) * 100}%` }} /></div>
                    <span>{p.qty}</span>
                  </div>
                )
              })}
            </div>
            <button className="btn-outline" style={{ marginTop: 16, width: 'auto', padding: '8px 16px' }} onClick={loadAnalytics}>Обновить</button>
          </div>
        )}
        {tab === 'stats' && !analytics && <p className="hint">Загрузка статистики...</p>}

        {tab === 'orders' && (
          <div className="admin-order-list">
            <div className="form-group" style={{ marginBottom: 12 }}>
              <input
                placeholder="Поиск: VL-… / ID / адрес / товар"
                value={orderSearch}
                onChange={(e) => setOrderSearch(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') loadOrders() }}
              />
              <button type="button" className="sbtn" style={{ marginTop: 8 }} onClick={() => loadOrders()}>Найти</button>
              <p className="hint">Доставленные скрыты — найдите по номеру заказа</p>
            </div>
            {orders.map((o) => (
              <div key={o.id} className="admin-order-card">
                <div className="order-card-top">
                  <strong>{o.order_number}</strong>
                  <span className="status-pill">{statusRu[o.status] || o.status}</span>
                </div>
                <div className="order-card-meta">
                  <span>Товары: {Number(o.subtotal).toFixed(0)} TJS</span>
                  <span>Доставка: {Number(o.delivery_cost).toFixed(0)} TJS</span>
                  <span className="order-sum">{Number(o.total).toFixed(0)} TJS</span>
                </div>
                <p className="hint" style={{ margin: '6px 0' }}>
                  Оплата: {o.payment_status}
                  {o.delivery_quote_status && o.delivery_quote_status !== 'none' && ` · Доставка: ${o.delivery_quote_status}`}
                </p>
                <p className="hint">{o.delivery_city} · {o.delivery_address}</p>
                {(o.items || []).length > 0 && (
                  <ul className="hint" style={{ margin: '6px 0', paddingLeft: 18 }}>
                    {(o.items || []).map((it: any, i: number) => (
                      <li key={i}>{it.product_name}{it.variant_name ? ` (${it.variant_name})` : ''} × {it.quantity}</li>
                    ))}
                  </ul>
                )}
                {o.customer_comment && (
                  <p style={{ margin: '8px 0', padding: '8px 10px', background: '#fff8f0', borderRadius: 10, border: '1px solid #f0e0d0', fontSize: '0.9rem' }}>
                    <strong>Пожелания клиента:</strong> {o.customer_comment}
                  </p>
                )}

                <div className="status-btns">
                  <button type="button" className="sbtn" onClick={() => openReceipts(o.id)}>Чек</button>
                  {o.payment_status === 'awaiting_review' && (
                    <>
                      <button type="button" className="sbtn ok" onClick={() => review(o.id, true)}>Одобрить оплату</button>
                      <button type="button" className="sbtn bad" onClick={() => review(o.id, false)}>Отклонить</button>
                    </>
                  )}
                  {o.status !== 'cancelled' && o.status !== 'refunded' && o.payment_status === 'paid' && (
                    <div className="quote-row">
                      <input
                        type="number"
                        placeholder="Доставка TJS"
                        value={deliveryQuote[o.id] || ''}
                        onChange={(e) => setDeliveryQuote({ ...deliveryQuote, [o.id]: e.target.value })}
                        style={{ width: 110 }}
                      />
                      <button type="button" className="sbtn ok" onClick={() => sendDeliveryQuote(o.id)}>Отправить сумму доставки</button>
                    </div>
                  )}
                  {o.delivery_quote_status === 'quoted' && (
                    <span className="hint">Ждём согласия клиента на доставку {Number(o.delivery_cost).toFixed(0)} TJS</span>
                  )}
                  {o.delivery_quote_status === 'rejected' && (
                    <span className="error">Клиент отказался — верните оплату</span>
                  )}
                  {STATUS_FLOW.filter(s => s.key !== 'cancelled').map((s) => (
                    <button key={s.key} type="button" className={`sbtn ${o.status === s.key ? 'active' : ''}`} onClick={() => setStatus(o.id, s.key)}>
                      {s.label}
                    </button>
                  ))}
                  {o.status !== 'cancelled' && (
                    <button type="button" className="sbtn bad" onClick={() => cancelOrder(o.id)}>Отменить заказ</button>
                  )}
                </div>
              </div>
            ))}
            {orders.length === 0 && <p className="hint">Заказов нет</p>}

            {viewOrderId && (
              <div className="glass-card" style={{ marginTop: 16 }}>
                <h3>Чеки заказа #{viewOrderId}</h3>
                {receipts.length === 0 ? <p>Нет чеков</p> : receipts.map((r) => (
                  <div key={r.id} style={{ margin: '10px 0', display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                    <button type="button" className="sbtn ok" onClick={() => viewReceipt(r.id)}>Смотреть чек</button>
                    <span className="hint">{r.original_filename || r.id} · {r.created_at ? new Date(r.created_at).toLocaleString('ru') : ''}</span>
                  </div>
                ))}
                {receiptPreview && (
                  <div style={{ marginTop: 12 }}>
                    <img src={receiptPreview} alt="Чек" style={{ maxWidth: '100%', borderRadius: 12, border: '1px solid var(--border)' }} />
                  </div>
                )}
                <button type="button" className="link-btn" onClick={() => { setViewOrderId(null); setReceiptPreview(null) }}>Закрыть</button>
              </div>
            )}
          </div>
        )}

        {tab === 'pay' && !payUnlocked && (
          <div className="glass-card" style={{ maxWidth: 360 }}>
            <h3>Реквизиты оплаты</h3>
            <p className="hint">Введите код доступа</p>
            <input type="password" inputMode="numeric" value={payPin} onChange={(e) => setPayPin(e.target.value)} placeholder="Код" />
            <button type="button" className="btn-accent" style={{ marginTop: 12 }} onClick={() => {
              if (payPin === '1810') { setPayUnlocked(true); setPayPin('') }
              else setMsg('Неверный код')
            }}>Открыть</button>
          </div>
        )}
        {tab === 'pay' && payUnlocked && (
          <div>
            <p className="hint">Способы: DC, Эсхата (карта), Алиф. Укажите реальные реквизиты.</p>
            {methods.map((m) => (
              <div key={m.id} className="glass-card" style={{ marginBottom: 14 }}>
                <h3 style={{ color: 'var(--purple-deep)' }}>{m.name}</h3>
                <div className="form-group">
                  <label>Получатель</label>
                  <input
                    value={editPm[m.id]?.recipient_name || ''}
                    onChange={(e) => setEditPm({ ...editPm, [m.id]: { ...editPm[m.id], recipient_name: e.target.value } })}
                  />
                </div>
                <div className="form-group">
                    <label>Номер карты / счёта</label>
                    <input
                      value={editPm[m.id]?.account_number || ''}
                      onChange={(e) => setEditPm({ ...editPm, [m.id]: { ...editPm[m.id], account_number: e.target.value } })}
                    />
                  </div>
                <div className="form-group">
                  <label>Инструкция для клиента</label>
                  <textarea
                    rows={2}
                    value={editPm[m.id]?.instructions || ''}
                    onChange={(e) => setEditPm({ ...editPm, [m.id]: { ...editPm[m.id], instructions: e.target.value } })}
                  />
                </div>
                <button type="button" className="btn-accent" style={{ width: 'auto', padding: '10px 18px' }} onClick={() => savePm(m.id)}>
                  Сохранить
                </button>
              </div>
            ))}
          </div>
        )}

        {tab === 'zones' && (
          <div>
            <p className="hint">Районы доставки (сумму доставки указывает админ после проверки оплаты)</p>
            <ul style={{ margin: '12px 0' }}>
              {zones.map((z) => (
                <li key={z.id} style={{ marginBottom: 6 }}>{z.name} ({z.city})</li>
              ))}
            </ul>
            <form onSubmit={createZone} style={{ maxWidth: 400 }}>
              <div className="form-group"><label>Название района</label><input value={zName} onChange={(e) => setZName(e.target.value)} required /></div>
              <div className="form-group"><label>Город</label><input value={zCity} onChange={(e) => setZCity(e.target.value)} placeholder="как название" /></div>
              <button className="btn-accent" type="submit">Добавить</button>
            </form>
          </div>
        )}

        {tab === 'products' && (
          <div>
            <form onSubmit={createProduct} style={{ maxWidth: 480 }}>
              <div className="form-group"><label>SKU</label><input value={sku} onChange={(e) => setSku(e.target.value)} required /></div>
              <div className="form-group"><label>Название</label><input value={name} onChange={(e) => setName(e.target.value)} required /></div>
              <div className="form-group"><label>Каталог</label>
                <select value={categoryId} onChange={(e) => setCategoryId(e.target.value)} required>
                  <option value="">Выберите каталог</option>
                  {categories.map((c) => <option key={c.id} value={c.id}>{c.name_ru}</option>)}
                </select>
              </div>
              <div className="form-group"><label>Описание</label><textarea value={desc} onChange={(e) => setDesc(e.target.value)} rows={3} /></div>
              <div className="form-group"><label>Цена товара (для клиента) TJS</label><input type="number" value={price} onChange={(e) => setPrice(e.target.value)} required /></div>
              <div className="form-group"><label>Закупка / себестоимость TJS</label><input type="number" value={purchasePrice} onChange={(e) => setPurchasePrice(e.target.value)} /><p className="hint">Для расчёта прибыли: выручка − закупка</p></div>
              <div className="form-group"><label>Скидка %</label><input type="number" min={0} max={90} value={discount} onChange={(e) => setDiscount(e.target.value)} /></div>
              <div className="form-group"><label>Остаток</label><input type="number" min={0} value={stock} onChange={(e) => setStock(e.target.value)} /></div>
              <div className="form-group"><label>URL фото (с новой строки)</label><textarea value={imgUrls} onChange={(e) => setImgUrls(e.target.value)} rows={3} /></div>
              <div className="form-group"><label>Или файлы (до 10)</label><input type="file" accept="image/*" multiple onChange={(e) => setProductFiles(e.target.files)} /></div>
              <button className="btn-accent" type="submit">Опубликовать</button>
            </form>
            <h3 style={{ marginTop: 24 }}>Каталог</h3>
            <div className="admin-product-list">
              {productsList.map((p: any) => (
                <div key={p.id} className="admin-product-row">
                  <div className="admin-product-info">
                    <strong>#{p.id} · {p.name_ru}</strong>
                    <span>SKU {p.sku} · {Number(p.final_price ?? p.price).toFixed(0)} TJS · скидка {p.discount_percent || 0}%</span>
                  </div>
                  <div className="admin-product-actions">
                    <input type="number" min={0} max={90} defaultValue={p.discount_percent || 0} id={`disc-${p.id}`} style={{ width: 64 }} />
                    <button type="button" className="sbtn" onClick={async () => {
                      const el = document.getElementById(`disc-${p.id}`) as HTMLInputElement
                      await api.patch(`/admin/products/${p.id}`, { discount_percent: Number(el?.value) || 0 })
                      setMsg('Скидка сохранена'); loadProducts()
                    }}>Скидка</button>
                    <button type="button" className="sbtn" onClick={async () => {
                      await api.patch(`/admin/products/${p.id}`, { is_published: !p.is_published })
                      loadProducts()
                    }}>{p.is_published ? 'Скрыть' : 'Показать'}</button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'verif' && (
          <div>
            {verifs.length === 0 ? <p className="hint">Нет заявок</p> : verifs.map((v) => (
              <div key={v.id} className="glass-card" style={{ marginBottom: 10 }}>
                <strong>{v.verification_full_name || v.full_name}</strong>
                <div className="status-btns" style={{ marginTop: 8 }}>
                  <button type="button" className="sbtn ok" onClick={() => reviewVerif(v.id, true)}>Подтвердить</button>
                  <button type="button" className="sbtn bad" onClick={() => reviewVerif(v.id, false)}>Отклонить</button>
                </div>
              </div>
            ))}
          </div>
        )}

        {tab === 'promo' && (
          <div>
            <form onSubmit={async (e) => {
              e.preventDefault()
              try {
                await api.post('/promo/admin', {
                  code: promoForm.code,
                  discount_percent: Number(promoForm.discount_percent) || 0,
                  discount_fixed: Number(promoForm.discount_fixed) || 0,
                  max_uses: Number(promoForm.max_uses) || 0,
                })
                setMsg('Промокод создан'); setPromoForm({ code: '', discount_percent: '10', discount_fixed: '0', max_uses: '0' }); loadPromos()
              } catch (err: any) {
                setMsg(err.response?.data?.detail || 'Ошибка')
              }
            }} style={{ maxWidth: 400 }}>
              <div className="form-group"><label>Код</label><input value={promoForm.code} onChange={(e) => setPromoForm({ ...promoForm, code: e.target.value })} required /></div>
              <div className="form-group"><label>Скидка %</label><input type="number" value={promoForm.discount_percent} onChange={(e) => setPromoForm({ ...promoForm, discount_percent: e.target.value })} /></div>
              <div className="form-group"><label>Или фикс. TJS</label><input type="number" value={promoForm.discount_fixed} onChange={(e) => setPromoForm({ ...promoForm, discount_fixed: e.target.value })} /></div>
              <div className="form-group"><label>Макс. использований (0 = ∞)</label><input type="number" value={promoForm.max_uses} onChange={(e) => setPromoForm({ ...promoForm, max_uses: e.target.value })} /></div>
              <button className="btn-accent" type="submit">Создать</button>
            </form>
            <div className="admin-order-list" style={{ marginTop: 16 }}>
              {promos.map((p) => (
                <div key={p.id} className="admin-order-card">
                  <strong>{p.code}</strong> — {p.discount_percent}% / {Number(p.discount_fixed)} TJS
                  <span className="hint"> · использовано {p.used_count}/{p.max_uses || '∞'}</span>
                  <button type="button" className="sbtn bad" style={{ marginLeft: 8 }} onClick={async () => {
                    await api.delete(`/promo/admin/${p.id}`); loadPromos()
                  }}>Удалить</button>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'users' && (
          <div>
            <div className="form-group">
              <input
                placeholder="Поиск: имя, почта, телефон..."
                value={userQuery}
                onChange={(e) => setUserQuery(e.target.value)}
              />
            </div>
            <p className="hint">Найдено: {users.filter((u) => {
              const q = userQuery.trim().toLowerCase()
              if (!q) return true
              return [u.full_name, u.email, u.phone, String(u.id)].filter(Boolean).some((x) => String(x).toLowerCase().includes(q))
            }).length}</p>
            <div className="admin-order-list">
              {users.filter((u) => {
                const q = userQuery.trim().toLowerCase()
                if (!q) return true
                return [u.full_name, u.email, u.phone, String(u.id)].filter(Boolean).some((x) => String(x).toLowerCase().includes(q))
              }).map((u) => (
                <div key={u.id} className="admin-order-card">
                  <div className="order-card-top">
                    <strong>{u.full_name || 'Без имени'}</strong>
                    <span className="status-pill">{u.role}</span>
                  </div>
                  <p style={{ margin: '8px 0' }}>
                    {u.phone ? (
                      <a href={`tel:${String(u.phone).replace(/\s/g, '')}`} className="user-contact">📞 {u.phone}</a>
                    ) : <span className="hint">нет телефона</span>}
                    {' · '}
                    {u.email ? (
                      <a href={`mailto:${u.email}`} className="user-contact">✉ {u.email}</a>
                    ) : null}
                  </p>
                  <p className="hint">
                    ID {u.id}
                    {u.verification_status ? ` · верификация: ${u.verification_status}` : ''}
                    {u.device_type ? ` · ${u.device_type}` : ''}
                    {u.created_at ? ` · ${new Date(u.created_at).toLocaleDateString('ru')}` : ''}
                  </p>
                </div>
              ))}
            </div>
          </div>
        )}

        {tab === 'broadcast' && (
          <div className="glass-card" style={{ maxWidth: 480 }}>
            <h3>Рассылка клиентам</h3>
            <p className="hint">Сообщение увидят пользователи онлайн (всплывающее окно).</p>
            <textarea value={broadcastText} onChange={(e) => setBroadcastText(e.target.value)} rows={4} placeholder="Текст объявления..." />
            <button type="button" className="btn-accent" style={{ marginTop: 10 }} onClick={async () => {
              try {
                await api.post('/admin/broadcast', { text: broadcastText })
                setMsg('Рассылка отправлена'); setBroadcastText('')
              } catch (e: any) {
                setMsg(e.response?.data?.detail || 'Ошибка')
              }
            }}>Отправить всем</button>
          </div>
        )}

        {tab === 'settings' && (
          <div style={{ maxWidth: 480 }}>
            {[
              ['instagram_url', 'Instagram (основная ссылка)'],
              ['telegram_channel_url', 'Доп. ссылка (можно Instagram)'],
              ['telegram_admin_dm', 'WhatsApp / поддержка'],
              ['office_address', 'Адрес магазина'],
              ['about_text', 'О нас'],
              ['home_banners', 'Баннеры (JSON: [{type,url,title,subtitle}])'],
            ].map(([key, label]) => (
              <div key={key} className="form-group">
                <label>{label}</label>
                <input
                  defaultValue={settings[key] || ''}
                  id={`set-${key}`}
                  onBlur={(e) => {
                    if (e.target.value !== (settings[key] || '')) saveSettingKey(key, e.target.value)
                  }}
                />
              </div>
            ))}
            <p className="hint">Сохраняется при уходе с поля</p>
            <div className="glass-card" style={{ marginTop: 16 }}>
              <h3>Баннеры с устройства (до 5 фото/видео)</h3>
              <input type="file" accept="image/*,video/*" multiple onChange={(e) => setBannerFiles(e.target.files)} />
              <button type="button" className="btn-accent" style={{ marginTop: 10 }} onClick={async () => {
                if (!bannerFiles || !bannerFiles.length) { setMsg('Выберите файлы'); return }
                const fd = new FormData()
                Array.from(bannerFiles).slice(0, 5).forEach((f) => fd.append('files', f))
                try {
                  await api.post('/admin/banners/upload', fd)
                  setMsg('Баннеры обновлены'); setBannerFiles(null); loadSettings()
                } catch (e: any) {
                  setMsg(e.response?.data?.detail || 'Ошибка загрузки баннеров')
                }
              }}>Загрузить баннеры</button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
