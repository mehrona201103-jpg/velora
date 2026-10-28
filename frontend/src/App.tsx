import { Routes, Route, Link, useNavigate, Navigate, useLocation } from 'react-router-dom'
import { useState, useEffect, createContext, useContext, useCallback, useMemo } from 'react'
import api, { User } from './services/api'
import { hasBiometricRegistered, verifyBiometric } from './services/biometric'
import { IconHome, IconUser, IconCart, IconAdmin, IconLogout, IconLock, IconFingerprint, IconSearch, IconPackage } from './components/Icons'
import HomePage from './pages/HomePage'
import ProductPage from './pages/ProductPage'
import CartPage from './pages/CartPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import OrdersPage from './pages/OrdersPage'
import OrderDetailPage from './pages/OrderDetailPage'
import AdminPage from './pages/AdminPage'
import ProfilePage from './pages/ProfilePage'
import { I18nProvider, useI18n } from './i18n'
import PolicyPage from './pages/PolicyPage'

interface AuthCtx {
  user: User | null
  setUser: (u: User | null) => void
  logout: () => void
}

const AuthContext = createContext<AuthCtx>({ user: null, setUser: () => {}, logout: () => {} })
export const useAuth = () => useContext(AuthContext)

function isStaff(u: User | null) {
  return !!u && (u.role === 'owner' || u.role === 'admin')
}

function applyDevice(device?: string) {
  document.body.classList.remove('device-phone', 'device-tablet', 'device-pc')
  const d = device || localStorage.getItem('velora_device') || 'phone'
  document.body.classList.add(`device-${d}`)
  localStorage.setItem('velora_device', d)
}

function CustomerHeader() {
  const { user, logout } = useAuth()
  const { t, toggle, lang } = useI18n()
  const [supportUrl, setSupportUrl] = useState('')
  const [dark, setDark] = useState(() => localStorage.getItem('velora_theme') === 'dark')
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light')
    localStorage.setItem('velora_theme', dark ? 'dark' : 'light')
  }, [dark])
  useEffect(() => {
    api.get('/orders/settings/public').then((r) => {
      setSupportUrl(r.data.telegram_admin_dm || r.data.telegram_channel_url || '')
    }).catch(() => {})
  }, [])
  const [q, setQ] = useState('')
  const navigate = useNavigate()

  return (
    <header className="header">
      <div className="container header-inner">
        <Link to="/" className="logo logo-brand">
          <img src="/logo.png" alt="VELORA" className="logo-mark" />
          <span className="logo-text">VELORA</span>
        </Link>
        <form className="search-form" onSubmit={(e) => { e.preventDefault(); navigate(`/?q=${encodeURIComponent(q)}`) }}>
          <input type="search" placeholder={t("search")} value={q} onChange={(e) => setQ(e.target.value)} enterKeyHint="search" />
          <button type="submit" aria-label="Поиск"><IconSearch size={18} /></button>
        </form>
        <div className="nav-actions nav-desktop">
          <button type="button" className="theme-btn" onClick={() => setDark((d) => !d)} title="Тема">{dark ? '☀️' : '🌙'}</button>
          <button type="button" className="theme-btn" onClick={toggle} title="Язык">{lang === 'ru' ? 'TJ' : 'RU'}</button>
          {user ? (
            <>
              <Link to="/profile"><IconUser size={16} /> Профиль</Link>
              <Link to="/cart"><IconCart size={16} /> Корзина</Link>
              <button onClick={logout}><IconLogout size={16} /></button>
            </>
          ) : (
            <>
              <Link to="/login">Вход</Link>
              <Link to="/register" className="btn-primary">Регистрация</Link>
            </>
          )}
        </div>
      </div>
    </header>
  )
}

function AdminHeader() {
  const { logout } = useAuth()
  return (
    <header className="header admin-header">
      <div className="container header-inner">
        <Link to="/admin" className="logo logo-brand">
          <img src="/logo.png" alt="VELORA" className="logo-mark" />
          <span className="logo-text">VELORA</span>
          <small className="admin-tag">Админ</small>
        </Link>
        <div className="nav-actions">
          <button onClick={logout}><IconLogout size={16} /> Выход</button>
        </div>
      </div>
    </header>
  )
}

function InstagramFab() {
  const [url, setUrl] = useState('https://instagram.com/_velora_shop.tj')
  useEffect(() => {
    api.get('/orders/settings/public').then((r) => {
      setUrl(r.data.instagram_url || r.data.telegram_channel_url || 'https://instagram.com/_velora_shop.tj')
    }).catch(() => {})
  }, [])
  return (
    <a href={url} target="_blank" rel="noreferrer" className="ig-fab ig-fab-bottom" title="Instagram @_velora_shop.tj" aria-label="Instagram">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
        <path d="M12 2.163c3.204 0 3.584.012 4.85.07 3.252.148 4.771 1.691 4.919 4.919.058 1.265.069 1.645.069 4.849 0 3.205-.012 3.584-.069 4.849-.149 3.225-1.664 4.771-4.919 4.919-1.266.058-1.644.07-4.85.07-3.204 0-3.584-.012-4.849-.07-3.26-.149-4.771-1.699-4.919-4.92-.058-1.265-.07-1.644-.07-4.849 0-3.204.013-3.583.07-4.849.149-3.227 1.664-4.771 4.919-4.919 1.266-.057 1.645-.069 4.849-.069zM12 0C8.741 0 8.333.014 7.053.072 2.695.272.273 2.69.073 7.052.014 8.333 0 8.741 0 12c0 3.259.014 3.668.072 4.948.2 4.358 2.618 6.78 6.98 6.98C8.333 23.986 8.741 24 12 24c3.259 0 3.668-.014 4.948-.072 4.354-.2 6.782-2.618 6.979-6.98.059-1.28.073-1.689.073-4.948 0-3.259-.014-3.667-.072-4.947-.196-4.354-2.617-6.78-6.979-6.98C15.668.014 15.259 0 12 0zm0 5.838a6.162 6.162 0 100 12.324 6.162 6.162 0 000-12.324zM12 16a4 4 0 110-8 4 4 0 010 8zm6.406-11.845a1.44 1.44 0 100 2.881 1.44 1.44 0 000-2.881z" />
      </svg>
    </a>
  )
}

function BottomNav() {
  const { user } = useAuth()
  const loc = useLocation()
  const navigate = useNavigate()
  const on = (path: string) => loc.pathname === path || (path !== '/' && loc.pathname.startsWith(path))
  const onVisual = (file: File) => {
    const fd = new FormData()
    fd.append('file', file)
    api.post('/products/visual-search', fd).then((r) => {
      const items = r.data?.items || []
      if (items[0]) navigate(`/product/${items[0].id}`)
      else alert(r.data?.hint || 'Ничего не найдено')
    }).catch(() => alert('Поиск по фото не удался'))
  }
  return (
    <nav className="bottom-nav">
      <Link to="/" className={on('/') && !on('/product') ? 'active' : ''}><IconHome size={22} /><span>Главная</span></Link>
      <Link to="/cart" className={on('/cart') ? 'active' : ''}><IconCart size={22} /><span>Корзина</span></Link>
      <label className="nav-cam">
        <IconSearch size={22} />
        <span>Фото</span>
        <input type="file" accept="image/*" capture="environment" hidden onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) onVisual(f)
        }} />
      </label>
      <Link to="/orders" className={on('/orders') ? 'active' : ''}><IconPackage size={22} /><span>Заказы</span></Link>
      <Link to={user ? '/profile' : '/login'} className={on('/profile') || on('/login') ? 'active' : ''}><IconUser size={22} /><span>Профиль</span></Link>
    </nav>
  )
}

function SplashScreen({ onDone }: { onDone: () => void }) {
  const [pct, setPct] = useState(0)
  useEffect(() => {
    const start = Date.now()
    const dur = 1200
    let raf = 0
    const tick = () => {
      const p = Math.min(100, Math.round(((Date.now() - start) / dur) * 100))
      setPct(p)
      if (p >= 100) setTimeout(onDone, 150)
      else raf = requestAnimationFrame(tick)
    }
    raf = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(raf)
  }, [onDone])
  return (
    <div className="splash-screen">
      <img src="/logo.png" alt="" className="splash-logo-img" />
      <div className="splash-logo">VELORA</div>
      <div className="splash-tag">женская одежда</div>
      <div className="splash-track">
        <div className="splash-bar" style={{ width: pct + '%' }} />
        <div className="splash-truck" style={{ left: `calc(${pct}% - 14px)` }}>👠</div>
      </div>
      <div className="splash-pct">{pct}%</div>
    </div>
  )
}

export default function App() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)
  const needsLock = !!(localStorage.getItem('velora_pin') || hasBiometricRegistered())
  const [unlocked, setUnlocked] = useState(!needsLock)
  const [splashDone, setSplashDone] = useState(() => sessionStorage.getItem('velora_splash') === '1')
  const [broadcast, setBroadcast] = useState<{ id: number; text: string } | null>(null)
  const [pinTry, setPinTry] = useState('')
  const [pinError, setPinError] = useState('')
  const [bioLoading, setBioLoading] = useState(false)

  useEffect(() => {
    applyDevice()
    document.documentElement.style.touchAction = 'manipulation'
    const token = localStorage.getItem('velora_token')
    if (token) {
      api.get('/auth/me')
        .then((r) => {
          setUser(r.data)
          applyDevice(r.data.device_type)
        })
        .catch(() => localStorage.removeItem('velora_token'))
        .finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (!unlocked && hasBiometricRegistered()) {
      setBioLoading(true)
      verifyBiometric()
        .then((ok) => { if (ok) setUnlocked(true) })
        .finally(() => setBioLoading(false))
    }
  }, [unlocked])

  const logout = useCallback(() => {
    localStorage.removeItem('velora_token')
    setUser(null)
  }, [])

  const authValue = useMemo(() => ({ user, setUser, logout }), [user, logout])
  const staff = isStaff(user)

  useEffect(() => {
    if (staff) return
    const poll = () => {
      api.get('/orders/settings/public').then((r) => {
        const raw = r.data?.live_broadcast
        if (!raw) return
        try {
          const b = typeof raw === 'string' ? JSON.parse(raw) : raw
          if (!b?.id || !b?.text) return
          const seen = localStorage.getItem('velora_bc_seen')
          if (seen === String(b.id)) return
          setBroadcast({ id: b.id, text: b.text })
        } catch {}
      }).catch(() => {})
    }
    poll()
    const id = setInterval(poll, 4000)
    return () => clearInterval(id)
  }, [staff])

  if (!splashDone) {
    return <SplashScreen onDone={() => { sessionStorage.setItem('velora_splash', '1'); setSplashDone(true) }} />
  }

  if (loading) {
    return <div className="boot-screen"><div className="boot-logo">VELORA</div><div className="boot-spin" /></div>
  }

  if (!unlocked) {
    return (
      <div className="lock-screen">
        <div className="lock-card">
          <div className="lock-icon"><IconLock size={36} /></div>
          <h1>VELORA</h1>
          <p className="hint">Разблокируйте приложение</p>
          {hasBiometricRegistered() && (
            <button className="btn-accent" disabled={bioLoading} onClick={async () => {
              setBioLoading(true)
              const ok = await verifyBiometric()
              setBioLoading(false)
              if (ok) setUnlocked(true)
              else setPinError('Биометрия не подтверждена')
            }}>
              <IconFingerprint size={18} /> {bioLoading ? 'Проверка…' : 'Face ID / Touch ID'}
            </button>
          )}
          {localStorage.getItem('velora_pin') && (
            <>
              <input type="password" inputMode="numeric" maxLength={4} value={pinTry}
                placeholder="PIN" autoComplete="one-time-code"
                onChange={(e) => setPinTry(e.target.value.replace(/\D/g, ''))}
                className="pin-input" />
              {pinError && <p className="error">{pinError}</p>}
              <button className="btn-accent" onClick={() => {
                if (pinTry === localStorage.getItem('velora_pin')) setUnlocked(true)
                else { setPinError('Неверный PIN'); setPinTry('') }
              }}>Разблокировать</button>
            </>
          )}
        </div>
      </div>
    )
  }

  // ========== ADMIN-ONLY SHELL ==========
  if (staff) {
    return (
      <AuthContext.Provider value={authValue}>
        <AdminHeader />
        <main className="container page-bottom-admin">
          <Routes>
            <Route path="/admin/*" element={<AdminPage />} />
            <Route path="/login" element={<Navigate to="/admin" replace />} />
            <Route path="*" element={<Navigate to="/admin" replace />} />
          </Routes>
        </main>
      </AuthContext.Provider>
    )
  }

  // ========== CUSTOMER APP ==========
  return (
    <AuthContext.Provider value={authValue}>
      <CustomerHeader />
      <main className="container page-bottom">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/product/:id" element={<ProductPage />} />
          <Route path="/cart" element={user ? <CartPage /> : <Navigate to="/login" />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/orders" element={user ? <OrdersPage /> : <Navigate to="/login" />} />
          <Route path="/policy" element={<PolicyPage />} />
          <Route path="/orders/:id" element={user ? <OrderDetailPage /> : <Navigate to="/login" />} />
          <Route path="/profile" element={user ? <ProfilePage /> : <Navigate to="/login" />} />
          <Route path="/admin/*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
      {broadcast && (
        <div className="broadcast-modal">
          <div className="broadcast-card">
            <h3>Сообщение VELORA</h3>
            <p>{broadcast.text}</p>
            <button type="button" className="btn-accent" onClick={() => {
              localStorage.setItem('velora_bc_seen', String(broadcast.id))
              setBroadcast(null)
            }}>Закрыть</button>
          </div>
        </div>
      )}
      <InstagramFab />
      <BottomNav />
      <footer>
        <div className="container"><strong>VELORA</strong> — женская одежда · Таджикистан</div>
      </footer>
    </AuthContext.Provider>
  )
}
