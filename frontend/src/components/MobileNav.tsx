import { Link, useLocation } from 'react-router-dom'

const tabs = [
  { path: '/', label: 'Главная' },
  { path: '/catalog', label: 'Каталог' },
  { path: '/cart', label: 'Корзина' },
  { path: '/profile', label: 'Профиль' },
]

export default function MobileNav() {
  const { pathname } = useLocation()

  return (
    <nav className="fixed bottom-0 left-0 right-0 bg-ivory border-t border-beige safe-area-pb">
      <div className="flex justify-around items-center h-14">
        {tabs.map((tab) => (
          <Link
            key={tab.path}
            to={tab.path}
            className={`text-xs tracking-wide ${
              pathname === tab.path ? 'text-gold font-medium' : 'text-charcoal/60'
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </div>
    </nav>
  )
}
