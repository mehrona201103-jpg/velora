import { useEffect, useState, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import api, { Product } from '../services/api'
import { mediaUrl } from '../services/media'
import { IconCamera } from '../components/Icons'

type Banner = { type: string; url: string; title?: string; subtitle?: string }

export default function HomePage() {
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [params] = useSearchParams()
  const q = params.get('q') || ''
  const [vsHint, setVsHint] = useState('')
  const [vsLoading, setVsLoading] = useState(false)
  const [banners, setBanners] = useState<Banner[]>([])
  const [slide, setSlide] = useState(0)
  const [minPrice, setMinPrice] = useState('')
  const [maxPrice, setMaxPrice] = useState('')
  const [onlySale, setOnlySale] = useState(false)
  const touchX = useRef(0)

  useEffect(() => {
    setLoading(true)
    api.get('/products', { params: { q: q || undefined, page_size: 48 } })
      .then((r) => setProducts(r.data.items || []))
      .finally(() => setLoading(false))
  }, [q])

  useEffect(() => {
    api.get('/orders/banners').then((r) => setBanners(r.data || [])).catch(() => {
      setBanners([
        { type: 'image', url: 'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&q=80', title: 'VELORA', subtitle: 'Женская одежда · доставка по Таджикистану' },
        { type: 'image', url: 'https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=1200&q=80', title: 'Прозрачные заказы', subtitle: 'Статус и доставка под контролем' },
      ])
    })
  }, [])

  useEffect(() => {
    if (banners.length < 2) return
    const cur = banners[slide]
    if (cur && cur.type === 'video') return // видео крутит до конца, потом onEnded
    const t = setInterval(() => setSlide((s) => (s + 1) % banners.length), 5500)
    return () => clearInterval(t)
  }, [banners, slide])

  const onVisualSearch = async (file: File) => {
    setVsLoading(true)
    setVsHint('')
    try {
      const fd = new FormData()
      fd.append('file', file)
      const r = await api.post('/products/visual-search', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setProducts(r.data.items || [])
      setVsHint(r.data.hint || 'Результаты поиска по фото')
    } catch (e: any) {
      setVsHint(e.response?.data?.detail || 'Не удалось найти по фото')
    } finally {
      setVsLoading(false)
    }
  }

  const b = banners[slide]

  return (
    <>
      <div
        className="promo-slider"
        onTouchStart={(e) => { touchX.current = e.touches[0].clientX }}
        onTouchEnd={(e) => {
          const dx = e.changedTouches[0].clientX - touchX.current
          if (dx < -40) setSlide((s) => (s + 1) % banners.length)
          if (dx > 40) setSlide((s) => (s - 1 + banners.length) % banners.length)
        }}
      >
        {b && (
          <div className="promo-slide">
            {b.type === 'video' ? (
              <video
                key={b.url + String(slide)}
                src={b.url}
                className="promo-media"
                autoPlay
                muted
                playsInline
                controls={false}
                onEnded={() => setSlide((s) => (s + 1) % banners.length)}
              />
            ) : (
              <img
              src={b.url}
              alt={b.title || ''}
              className="promo-media"
              onError={(e) => {
                (e.target as HTMLImageElement).src =
                  'https://images.unsplash.com/photo-1607082348824-0a96f2a4b9da?w=1200&q=80'
              }}
            />
            )}
            <div className="promo-overlay">
              <div className="promo-title">{b.title || 'VELORA'}</div>
              {b.subtitle && <div className="promo-sub">{b.subtitle}</div>}
            </div>
          </div>
        )}
        <div className="promo-dots">
          {banners.map((_, i) => (
            <button key={i} type="button" className={i === slide ? 'on' : ''} onClick={() => setSlide(i)} />
          ))}
        </div>
      </div>

      <div className="filter-row">
        <input type="number" placeholder="Цена от" value={minPrice} onChange={(e) => setMinPrice(e.target.value)} />
        <input type="number" placeholder="до" value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} />
        <label className="chip" style={{ cursor: 'pointer' }}>
          <input type="checkbox" checked={onlySale} onChange={(e) => setOnlySale(e.target.checked)} style={{ marginRight: 4 }} />
          Скидки
        </label>
      </div>
      <div className="cat-chips">
        <label className="chip chip-cam">
          <IconCamera size={16} /> Поиск по фото
          <input
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) onVisualSearch(f)
            }}
          />
        </label>
      </div>

      <h2 className="section-title">
        {vsHint ? 'Похожие товары' : q ? `Поиск: ${q}` : 'Каталог'}
      </h2>
      {vsLoading && <p className="hint">Ищем по фото…</p>}
      {vsHint && !vsLoading && <p className="hint">{vsHint}</p>}

      {loading ? (
        <div className="product-grid">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div key={i} className="product-card skeleton" />
          ))}
        </div>
      ) : products.length === 0 ? (
        <p className="empty-state">Пока нет товаров</p>
      ) : (
        <div className="product-grid">
          {products.filter((p) => {
        const price = Number(p.final_price ?? p.price)
        if (minPrice && price < Number(minPrice)) return false
        if (maxPrice && price > Number(maxPrice)) return false
        if (onlySale && !(p.discount_percent > 0)) return false
        return true
      }).map((p) => (
            <Link to={`/product/${p.id}`} key={p.id} className="product-card">
              <div className="product-img-wrap">
                <img src={mediaUrl(p.images?.[0]?.url)} alt={p.name_ru} loading="lazy" decoding="async" />
                {p.discount_percent > 0 && <span className="badge">-{p.discount_percent}%</span>}
              </div>
              <div className="info">
                <div className="name">{p.name_ru}</div>
                <div className="price">
                  {Number(p.final_price).toFixed(0)} <small>TJS</small>
                  {p.discount_percent > 0 && <span className="old">{Number(p.price).toFixed(0)}</span>}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </>
  )
}
