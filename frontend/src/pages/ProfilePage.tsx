import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getMe, logout, UserMe } from '../services/api'

export default function ProfilePage() {
  const navigate = useNavigate()
  const [user, setUser] = useState<UserMe | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getMe()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  function handleLogout() {
    logout()
    setUser(null)
    navigate('/login')
  }

  if (loading) {
    return (
      <div className="px-4 pt-10 text-center text-charcoal/50">Загрузка...</div>
    )
  }

  if (!user) {
    return (
      <div className="px-4 pt-6">
        <h1 className="text-xl font-light mb-6">Профиль</h1>
        <div className="space-y-3">
          <Link to="/login" className="block py-3 border-b border-beige text-sm">
            Войти
          </Link>
          <Link to="/register" className="block py-3 border-b border-beige text-sm">
            Регистрация
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="px-4 pt-6">
      <h1 className="text-xl font-light mb-6">Профиль</h1>
      <div className="bg-cream rounded-sm p-4 mb-6">
        <p className="font-medium">
          {user.first_name} {user.last_name}
        </p>
        <p className="text-sm text-charcoal/60 mt-1">{user.phone}</p>
        <p className="text-sm mt-3">
          Баланс: <span className="text-gold font-medium">{user.balance} TJS</span>
        </p>
        <p className="text-xs text-charcoal/40 mt-1">
          Роли: {user.roles.join(', ') || 'CLIENT'}
        </p>
      </div>
      <button onClick={handleLogout} className="text-sm text-charcoal/60 underline">
        Выйти
      </button>
    </div>
  )
}
