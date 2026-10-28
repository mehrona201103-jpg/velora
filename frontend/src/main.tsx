import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { I18nProvider } from './i18n'
import './index.css'

class ErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { err: string | null }
> {
  state = { err: null as string | null }
  static getDerivedStateFromError(e: Error) {
    return { err: e.message + (e.stack ? '\n' + e.stack.slice(0, 400) : '') }
  }
  componentDidCatch(e: Error) {
    console.error(e)
  }
  render() {
    if (this.state.err) {
      return (
        <div style={{ padding: 24, fontFamily: 'system-ui', maxWidth: 560 }}>
          <h2>Ошибка загрузки VELORA</h2>
          <pre style={{ whiteSpace: 'pre-wrap', color: '#b91c1c', fontSize: 12 }}>{this.state.err}</pre>
          <button type="button" onClick={() => {
            localStorage.clear()
            if ('serviceWorker' in navigator) {
              navigator.serviceWorker.getRegistrations().then((r) => r.forEach((x) => x.unregister()))
            }
            location.reload()
          }}>Очистить кэш и обновить</button>
        </div>
      )
    }
    return this.props.children
  }
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <BrowserRouter>
        <I18nProvider>
          <App />
        </I18nProvider>
      </BrowserRouter>
    </ErrorBoundary>
  </React.StrictMode>
)

if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
