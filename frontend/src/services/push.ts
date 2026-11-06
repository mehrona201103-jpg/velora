/** Web Push — реальные уведомления на телефон (PWA / APK). */
import api from './api'

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const out = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) out[i] = raw.charCodeAt(i)
  return out
}

export type PushSetupResult = {
  ok: boolean
  reason?: string
  devices?: number
  testSent?: number
}

async function getSWRegistration(): Promise<ServiceWorkerRegistration> {
  let reg = await navigator.serviceWorker.getRegistration('/')
  if (!reg) {
    reg = await navigator.serviceWorker.register('/sw.js', { scope: '/' })
  }
  // ensure active
  if (!reg.active) {
    await new Promise<void>((resolve) => {
      const sw = reg!.installing || reg!.waiting
      if (!sw) return resolve()
      sw.addEventListener('statechange', () => {
        if (sw.state === 'activated' || sw.state === 'installed') resolve()
      })
      setTimeout(() => resolve(), 4000)
    })
  }
  return navigator.serviceWorker.ready
}

export async function ensurePushSubscription(forceResubscribe = false): Promise<PushSetupResult> {
  try {
    if (!('serviceWorker' in navigator)) {
      return { ok: false, reason: 'Браузер не поддерживает Service Worker' }
    }
    if (!('PushManager' in window)) {
      return { ok: false, reason: 'Push не поддерживается на этом устройстве' }
    }
    if (!window.isSecureContext) {
      return { ok: false, reason: 'Нужен HTTPS' }
    }

    let perm = Notification.permission
    if (perm === 'denied') {
      return {
        ok: false,
        reason: 'Уведомления запрещены в настройках браузера/телефона. Разрешите их для VELORA.',
      }
    }
    if (perm !== 'granted') {
      perm = await Notification.requestPermission()
    }
    if (perm !== 'granted') {
      return { ok: false, reason: 'Вы не разрешили уведомления' }
    }

    const reg = await getSWRegistration()

    const keyRes = await api.get('/auth/push/vapid-public-key')
    const publicKey = keyRes.data?.publicKey as string
    if (!publicKey) {
      return { ok: false, reason: 'Сервер не выдал ключ. Подождите деплой и обновите страницу.' }
    }

    // Always drop old subscription when forcing — avoids VAPID mismatch
    const existing = await reg.pushManager.getSubscription()
    if (existing && forceResubscribe) {
      try { await existing.unsubscribe() } catch {}
    }

    let sub = forceResubscribe ? null : existing
    if (!sub) {
      sub = await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(publicKey),
      })
    }

    const json = sub.toJSON()
    if (!json.endpoint || !json.keys?.p256dh || !json.keys?.auth) {
      return { ok: false, reason: 'Браузер не создал подписку' }
    }

    const r = await api.post('/auth/push/subscribe', {
      endpoint: json.endpoint,
      p256dh: json.keys.p256dh,
      auth: json.keys.auth,
      user_agent: (navigator.userAgent || '').slice(0, 280),
    })
    localStorage.setItem('velora_push_ok', '1')

    const testSent = Number(r.data?.test_sent || 0)
    const testErrors: string[] = r.data?.test_errors || []
    if (testSent === 0 && testErrors.length) {
      return {
        ok: true,
        devices: r.data?.devices ?? 1,
        testSent: 0,
        reason: 'Подписка сохранена, но мгновенная отправка не прошла. Нажмите «Тест» ещё раз. ' + (testErrors[0] || ''),
      }
    }
    return { ok: true, devices: r.data?.devices ?? 1, testSent }
  } catch (e: any) {
    const msg = e?.response?.data?.detail || e?.message || String(e)
    console.error('[VELORA] push setup', e)
    return { ok: false, reason: msg }
  }
}

export async function sendTestPush(): Promise<{ ok: boolean; reason?: string }> {
  try {
    // Force fresh subscription with current VAPID key, then test
    const setup = await ensurePushSubscription(true)
    if (!setup.ok) return { ok: false, reason: setup.reason }
    if ((setup.testSent || 0) > 0) {
      return { ok: true }
    }
    await api.post('/auth/push/test')
    return { ok: true }
  } catch (e: any) {
    const detail = e?.response?.data?.detail
    return { ok: false, reason: typeof detail === 'string' ? detail : (e?.message || 'Ошибка теста') }
  }
}

export async function getPushStatus(): Promise<{ devices: number; ok: boolean }> {
  try {
    const r = await api.get('/auth/push/status')
    return { devices: r.data?.devices || 0, ok: !!r.data?.ok }
  } catch {
    return { devices: 0, ok: false }
  }
}
