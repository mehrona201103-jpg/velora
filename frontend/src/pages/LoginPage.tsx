import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../services/api'
import { useAuth } from '../App'

export default function LoginPage() {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { setUser } = useAuth()
  const navigate = useNavigate()

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      const r = await api.post('/auth/login', { login, password })
      localStorage.setItem('velora_token', r.data.access_token)
      if (r.data.user.device_type) {
        localStorage.setItem('velora_device', r.data.user.device_type)
        document.body.classList.remove('device-phone', 'device-tablet', 'device-pc')
        document.body.classList.add(`device-${r.data.user.device_type}`)
      }
      setUser(r.data.user)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Ошибка входа')
    }
  }

  return (
    <div className="form-card">
      <h1>Вход в VELORA</h1>
      <form onSubmit={submit}>
        <div className="form-group">
          <label>Email или телефон</label>
          <input value={login} onChange={(e) => setLogin(e.target.value)} required autoComplete="username" />
        </div>
        <div className="form-group">
          <label>Пароль</label>
          <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required autoComplete="current-password" />
        </div>
        {error && <p className="error">{error}</p>}
        <button type="submit" className="btn-accent" style={{ marginTop: 8 }}>Войти</button>
      </form>
      <p style={{ marginTop: 16, textAlign: 'center' }}>
        Нет аккаунта? <Link to="/register">Регистрация</Link>
      </p>
    </div>
  )
}
