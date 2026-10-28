import { Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { mediaUrl } from '../services/media'
import api, { User, Product } from '../services/api'
import { useAuth } from '../App'
import { isBiometricAvailable, registerBiometric, clearBiometric, hasBiometricRegistered } from '../services/biometric'
import { IconPackage, IconCart, IconLock, IconFingerprint, IconLogout, IconUser } from '../components/Icons'

export default function ProfilePage() {
  const { user, setUser, logout } = useAuth()
  const [settings, setSettings] = useState<Record<string, string>>({})
  const [showVerify, setShowVerify] = useState(false)
  const [showPin, setShowPin] = useState(false)
  const [fullName, setFullName] = useState('')
  const [selfie, setSelfie] = useState<File | null>(null)
  const [front, setFront] = useState<File | null>(null)
  const [msg, setMsg] = useState('')
  const [avatarFile, setAvatarFile] = useState<File | null>(null)
  const [favorites, setFavorites] = useState<Product[]>([])
  const [pin, setPin] = useState('')
  const [pin2, setPin2] = useState('')
  const [bioOk, setBioOk] = useState(false)

  useEffect(() => {
    api.get('/orders/settings/public').then((r) => setSettings(r.data)).catch(() => {})
    api.get('/auth/me').then((r) => setUser(r.data)).catch(() => {})
    api.get('/favorites').then((r) => setFavorites(r.data)).catch(() => {})
    isBiometricAvailable().then(setBioOk)
  }, [])

  if (!user) return null

  const uploadAvatar = async () => {
    if (!avatarFile) return
    const fd = new FormData()
    fd.append('file', avatarFile)
    const r = await api.post('/auth/me/avatar', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
    setUser(r.data)
    setMsg('Аватар обновлён')
  }

  const submitVerify = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selfie || !front) { setMsg('Загрузите оба фото'); return }
    const fd = new FormData()
    fd.append('full_name', fullName)
    fd.append('age_confirmed', 'true')
    fd.append('passport_selfie', selfie)
    fd.append('passport_front', front)
    try {
      await api.post('/auth/me/verification', fd, { headers: { 'Content-Type': 'multipart/form-data' } })
      setMsg('Заявка отправлена')
      setShowVerify(false)
      const r = await api.get('/auth/me')
      setUser(r.data)
    } catch (err: any) {
      setMsg(err.response?.data?.detail || 'Ошибка')
    }
  }

  const savePin = async () => {
    if (pin.length !== 4 || !/^\d{4}$/.test(pin)) { setMsg('PIN: 4 цифры'); return }
    if (pin !== pin2) { setMsg('PIN не совпадает'); return }
    localStorage.setItem('velora_pin', pin)
    await api.patch('/auth/me', { lock_type: 'pin' })
    setMsg('PIN установлен')
    setShowPin(false)
    const r = await api.get('/auth/me')
    setUser(r.data)
  }

  const enableBio = async () => {
    const ok = await registerBiometric(String(user.id), user.email || user.phone || 'velora')
    if (ok) {
      await api.patch('/auth/me', { lock_type: 'biometric' })
      setMsg('Face ID / Touch ID включён')
      const r = await api.get('/auth/me')
      setUser(r.data)
    } else {
      setMsg('Устройство не поддерживает или отменено')
    }
  }

  const disableBio = async () => {
    clearBiometric()
    await api.patch('/auth/me', { lock_type: 'none' })
    setMsg('Биометрия отключена')
  }

  return (
    <div>
      <div className="profile-header">
        <img
          className="avatar"
          src={mediaUrl(user.avatar_url)}
          alt=""
        />
        <div>
          <div style={{ fontWeight: 700, fontSize: '1.15rem', display: 'flex', alignItems: 'center', gap: 6 }}>
            {user.full_name || user.email || user.phone}
            {user.is_verified && <span className="verified-badge" title="Проверен">✓</span>}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--muted)' }}>
            {user.is_verified ? 'Идентифицирован' :
              user.verification_status === 'pending' ? 'На проверке' :
              user.verification_status === 'rejected' ? 'Отклонено' : 'Не идентифицирован'}
          </div>
          <div style={{ marginTop: 8 }}>
            <input type="file" accept="image/*" onChange={(e) => setAvatarFile(e.target.files?.[0] || null)} />
            {avatarFile && (
              <button className="btn-accent" style={{ marginTop: 6, padding: '8px 12px', width: 'auto' }} onClick={uploadAvatar}>
                Сохранить
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="profile-stats">
        <div className="stat-card">
          <div className="num">{user.total_orders || 0}</div>
          <div className="lbl">Заказов</div>
        </div>
        <div className="stat-card">
          <div className="num">{Number(user.total_spent || 0).toFixed(0)}</div>
          <div className="lbl">Потрачено TJS</div>
        </div>
      </div>

      {msg && <p className="success">{msg}</p>}

      <div className="menu-list" style={{ marginTop: 12 }}>
        <Link to="/orders"><IconPackage size={18} /> Мои заказы</Link>
        <Link to="/cart"><IconCart size={18} /> Корзина</Link>
        {user.is_verified ? (
          <div className="menu-static"><IconUser size={18} /> Идентификация пройдена ✓</div>
        ) : user.verification_status === 'pending' ? (
          <div className="menu-static"><IconUser size={18} /> Идентификация на проверке…</div>
        ) : (
          <button type="button" onClick={() => setShowVerify(true)}><IconUser size={18} /> Пройти идентификацию (18+)</button>
        )}
        <button onClick={() => setShowPin(true)}><IconLock size={18} /> PIN-код (4 цифры)</button>
        {bioOk && !hasBiometricRegistered() && (
          <button onClick={enableBio}><IconFingerprint size={18} /> Включить Face ID / Touch ID</button>
        )}
        {hasBiometricRegistered() && (
          <button onClick={disableBio}><IconFingerprint size={18} /> Отключить биометрию</button>
        )}
        {(settings.instagram_url || settings.telegram_channel_url) && (
          <a href={settings.instagram_url || settings.telegram_channel_url} target="_blank" rel="noreferrer">Instagram @_velora_shop.tj</a>
        )}
        <button onClick={logout}><IconLogout size={18} /> Выйти</button>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap' }}>
          <div>
            <div className="hint">Бонусы</div>
            <div style={{ fontWeight: 800, fontSize: '1.2rem', color: 'var(--purple-deep)' }}>{(user as any).loyalty_points ?? 0} баллов</div>
          </div>
          <div>
            <div className="hint">Реферальный код</div>
            <div style={{ fontWeight: 700 }}>{(user as any).referral_code || '—'}</div>
            <button type="button" className="link-btn" onClick={() => {
              const c = (user as any).referral_code
              if (c) navigator.clipboard?.writeText(c)
            }}>Копировать</button>
          </div>
        </div>
        <p className="hint" style={{ marginTop: 8 }}>1 балл ≈ за каждые 100 TJS оплаченных товаров. Друг по вашему коду — приятный бонус вам обоим (на старте).</p>
      </div>

      <div className="glass-card" style={{ marginBottom: 14 }}>
        <h3 style={{ marginTop: 0 }}>Telegram-уведомления</h3>
        {(user as any).telegram_chat_id ? (
          <p className="success">Подключено</p>
        ) : (
          <p className="hint">1) Откройте <a href="https://t.me/velorashoping_bot" target="_blank" rel="noreferrer">@velorashoping_bot</a> и нажмите <b>Start</b> / напишите /start<br/>2) Вставьте сюда ваш Telegram Chat ID и сохраните</p>
        )}
        <div className="form-group">
          <input id="tg-chat" placeholder="Telegram Chat ID" defaultValue={(user as any).telegram_chat_id || ''} />
        </div>
        <button type="button" className="btn-outline" style={{ width: 'auto', padding: '8px 14px' }} onClick={async () => {
          const el = document.getElementById('tg-chat') as HTMLInputElement
          try {
            const r = await api.patch('/auth/me', { telegram_chat_id: el?.value || null })
            setUser(r.data)
            setMsg(el?.value ? 'Сохранено. Бот пришлёт подтверждение в Telegram.' : 'Telegram отвязан')
          } catch (e: any) {
            setMsg(e.response?.data?.detail || 'Ошибка')
          }
        }}>Сохранить</button>
      </div>

      <Link to="/policy" className="btn-outline" style={{ display: 'block', textAlign: 'center', marginBottom: 14 }}>Правила и возврат</Link>

      <h3>Избранное</h3>
      {favorites.length === 0 ? (
        <p className="hint">Пока пусто — добавьте сердечком на товаре</p>
      ) : (
        <div className="product-grid">
          {favorites.map((p) => (
            <Link to={`/product/${p.id}`} key={p.id} className="product-card">
              <img src={mediaUrl(p.images?.[0]?.url)} alt={p.name_ru} loading="lazy" />
              <div className="info">
                <div className="name">{p.name_ru}</div>
                <div className="price">{Number(p.final_price).toFixed(0)} TJS</div>
              </div>
            </Link>
          ))}
        </div>
      )}

      {showVerify && (
        <div className="form-card" style={{ marginTop: 20 }}>
          <h1 style={{ fontSize: '1.1rem' }}>Идентификация</h1>
          <form onSubmit={submitVerify}>
            <div className="form-group">
              <label>ФИО как в паспорте</label>
              <input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
            </div>
            <div className="form-group">
              <label>Селфи с паспортом</label>
              <input type="file" accept="image/*" required onChange={(e) => setSelfie(e.target.files?.[0] || null)} />
            </div>
            <div className="form-group">
              <label>Лицевая сторона паспорта</label>
              <input type="file" accept="image/*" required onChange={(e) => setFront(e.target.files?.[0] || null)} />
            </div>
            <label style={{ fontSize: '0.85rem', display: 'flex', gap: 8, marginBottom: 12 }}>
              <input type="checkbox" required /> Мне есть 18 лет
            </label>
            <button type="submit" className="btn-accent">Отправить</button>
            <button type="button" className="link-btn" onClick={() => setShowVerify(false)}>Отмена</button>
          </form>
        </div>
      )}

      {showPin && (
        <div className="form-card" style={{ marginTop: 20 }}>
          <h1 style={{ fontSize: '1.1rem' }}>PIN-код</h1>
          <div className="form-group">
            <label>PIN</label>
            <input type="password" inputMode="numeric" maxLength={4} value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} />
          </div>
          <div className="form-group">
            <label>Повтор</label>
            <input type="password" inputMode="numeric" maxLength={4} value={pin2} onChange={(e) => setPin2(e.target.value.replace(/\D/g, ''))} />
          </div>
          <button className="btn-accent" onClick={savePin}>Сохранить</button>
          <button type="button" className="link-btn" onClick={() => setShowPin(false)}>Отмена</button>
        </div>
      )}

      {settings.about_text && (
        <div className="glass-card" style={{ marginTop: 20, fontSize: '0.9rem', color: 'var(--muted)' }}>
          <strong style={{ color: 'var(--purple-deep)' }}>О нас</strong>
          <p style={{ marginTop: 6 }}>{settings.about_text}</p>
        </div>
      )}
    </div>
  )
}
