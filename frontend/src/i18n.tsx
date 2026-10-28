import { createContext, useContext, useState, useMemo, type ReactNode } from 'react'

const dict = {
  ru: {
    search: 'Поиск товаров',
    home: 'Главная',
    cart: 'Корзина',
    orders: 'Заказы',
    profile: 'Профиль',
    login: 'Вход',
    register: 'Регистрация',
    popular: 'Популярное',
    buy: 'Купить',
    buyAgain: 'Купить снова',
    review: 'Отзыв',
    delivered: 'Доставлен',
    promo: 'Промокод',
    apply: 'Применить',
    lang: 'Тоҷикӣ',
    support: 'Поддержка',
    favorites: 'Избранное',
    policy: 'Правила и возврат',
    noOrders: 'Заказов пока нет',
  },
  tg: {
    search: 'Ҷустуҷӯи мол',
    home: 'Асосӣ',
    cart: 'Сабад',
    orders: 'Фармоишҳо',
    profile: 'Профил',
    login: 'Вуруд',
    register: 'Сабти ном',
    popular: 'Машҳур',
    buy: 'Харидан',
    buyAgain: 'Боз харидан',
    review: 'Шарҳ',
    delivered: 'Расонида шуд',
    promo: 'Промокод',
    apply: 'Татбиқ',
    lang: 'Русӣ',
    support: 'Дастгирӣ',
    favorites: 'Дӯстдошта',
    policy: 'Қоидаҳо ва бозгашт',
    noOrders: 'Фармоиш нест',
  },
} as const

type Lang = 'ru' | 'tg'
type Keys = keyof typeof dict.ru

function safeLang(v: string | null): Lang {
  return v === 'tg' ? 'tg' : 'ru'
}

const Ctx = createContext({
  lang: 'ru' as Lang,
  t: (k: Keys) => dict.ru[k] as string,
  toggle: () => {},
})

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => safeLang(localStorage.getItem('velora_lang')))
  const value = useMemo(() => ({
    lang,
    t: (k: Keys) => {
      const d = dict[lang] || dict.ru
      return d[k] || dict.ru[k] || String(k)
    },
    toggle: () => setLang((l) => {
      const n: Lang = l === 'ru' ? 'tg' : 'ru'
      localStorage.setItem('velora_lang', n)
      return n
    }),
  }), [lang])
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

export const useI18n = () => useContext(Ctx)
