import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login } from '../services/api'

export default function LoginPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(phone, password)
      navigate('/profile')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка входа')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 pt-10 max-w-md mx-auto">
      <h1 className="text-2xl font-light text-center mb-8 tracking-wide">Вход</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="tel"
          placeholder="Телефон (+992...)"
          value={phone}
          onChange={(e) => setPhone(e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
        />
        <input
          type="password"
          placeholder="Пароль"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
        />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Вход...' : 'Войти'}
        </button>
      </form>
      <p className="text-center mt-6 text-sm text-charcoal/60">
        Нет аккаунта?{' '}
        <Link to="/register" className="text-gold">
          Регистрация
        </Link>
      </p>
    </div>
  )
}
