import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../services/api'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    password: '',
    password_confirm: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (form.password !== form.password_confirm) {
      setError('Пароли не совпадают')
      return
    }
    setLoading(true)
    try {
      await register(form)
      navigate('/profile')
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Ошибка регистрации')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="px-4 pt-10 max-w-md mx-auto">
      <h1 className="text-2xl font-light text-center mb-8 tracking-wide">Регистрация</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <input
          type="text"
          placeholder="Имя"
          value={form.first_name}
          onChange={(e) => update('first_name', e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
        />
        <input
          type="text"
          placeholder="Фамилия"
          value={form.last_name}
          onChange={(e) => update('last_name', e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
        />
        <input
          type="tel"
          placeholder="Телефон (+992...)"
          value={form.phone}
          onChange={(e) => update('phone', e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
        />
        <input
          type="password"
          placeholder="Пароль (мин. 8 символов)"
          value={form.password}
          onChange={(e) => update('password', e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
          minLength={8}
        />
        <input
          type="password"
          placeholder="Подтвердите пароль"
          value={form.password_confirm}
          onChange={(e) => update('password_confirm', e.target.value)}
          className="w-full px-4 py-3 bg-cream border border-beige rounded-sm outline-none focus:border-gold"
          required
        />
        {error && <p className="text-red-600 text-sm">{error}</p>}
        <button type="submit" disabled={loading} className="btn-primary w-full">
          {loading ? 'Регистрация...' : 'Зарегистрироваться'}
        </button>
      </form>
      <p className="text-center mt-6 text-sm text-charcoal/60">
        Уже есть аккаунт?{' '}
        <Link to="/login" className="text-gold">
          Войти
        </Link>
      </p>
    </div>
  )
}
