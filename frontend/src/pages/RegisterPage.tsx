import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../App'

export default function RegisterPage() {
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [refCode, setRefCode] = useState('')
  const [device, setDevice] = useState<'phone' | 'tablet' | 'pc' | ''>('')
  const [error, setError] = useState('')
  const { setUser } = useAuth()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!device) {
      setError('Выберите устройство — без этого регистрация невозможна')
      return
    }
    if (!email && !phone) {
      setError('Укажите email или телефон')
      return
    }
    try {
      const r = await api.post('/auth/register', {
        email: email || undefined,
        phone: phone || undefined,
        password,
        full_name: fullName || undefined,
        device_type: device,
        referral_code: refCode.trim() || undefined,
      })
      localStorage.setItem('velora_token', r.data.access_token)
      localStorage.setItem('velora_device', device)
      document.body.classList.remove('device-phone', 'device-tablet', 'device-pc')
      document.body.classList.add(`device-${device}`)
      setUser(r.data.user)
      navigate('/')
    } catch (err: any) {
      const d = err.response?.data?.detail
      if (typeof d === 'string') setError(d)
      else if (Array.isArray(d)) setError(d.map((x: any) => x.msg || JSON.stringify(x)).join('; '))
      else setError('Ошибка регистрации. Возможно email или телефон уже заняты.')
    }
  }

  return (
    <div className="form-card">
      <h1>Регистрация VELORA</h1>
      <form onSubmit={submit}>
        <div className="form-group">
          <label>Имя</label>
          <input value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Как к вам обращаться" />
        </div>
        <div className="form-group">
          <label>Email</label>
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div className="form-group">
          <label>Телефон</label>
          <input value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+992..." />
        </div>
        <div className="form-group">
          <label>Пароль (мин. 6 символов)</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
        </div>
        <div className="form-group">
          <label>На каком устройстве будете пользоваться? *</label>
          <div className="device-picker">
            {([
              ['phone', '📱', 'Телефон'],
              ['tablet', '📲', 'Планшет'],
              ['pc', '💻', 'ПК'],
            ] as const).map(([id, icon, label]) => (
              <button
                key={id}
                type="button"
                className={`device-option ${device === id ? 'selected' : ''}`}
                onClick={() => setDevice(id)}
              >
                <span>{icon}</span>
                {label}
              </button>
            ))}
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        <div className="form-group">
          <label>Реферальный код (если есть)</label>
          <input value={refCode} onChange={(e) => setRefCode(e.target.value)} placeholder="Необязательно" />
        </div>
        <button type="submit" className="btn-accent" style={{ marginTop: 12 }} disabled={!device}>
          Создать аккаунт
        </button>
      </form>
      <p style={{ marginTop: 16, textAlign: 'center', fontSize: '0.9rem' }}>
        Уже есть аккаунт? <Link to="/login">Войти</Link>
      </p>
    </div>
  )
}
