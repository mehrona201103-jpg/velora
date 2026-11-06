/** WebAuthn Face ID / Touch ID helpers (platform authenticator). */

const CRED_KEY = 'velora_webauthn_cred'

function bufToB64(buf: ArrayBuffer): string {
  const bytes = new Uint8Array(buf)
  let s = ''
  bytes.forEach((b) => { s += String.fromCharCode(b) })
  return btoa(s).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
}

function b64ToBuf(b64: string): ArrayBuffer {
  const pad = '='.repeat((4 - (b64.length % 4)) % 4)
  const str = atob((b64 + pad).replace(/-/g, '+').replace(/_/g, '/'))
  const buf = new Uint8Array(str.length)
  for (let i = 0; i < str.length; i++) buf[i] = str.charCodeAt(i)
  return buf.buffer
}

export async function isBiometricAvailable(): Promise<boolean> {
  try {
    if (!window.PublicKeyCredential) return false
    // @ts-ignore
    if (typeof PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable === 'function') {
      // @ts-ignore
      return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable()
    }
    return true
  } catch {
    return false
  }
}

export async function registerBiometric(userId: string, userName: string): Promise<boolean> {
  try {
    const challenge = crypto.getRandomValues(new Uint8Array(32))
    const cred = await navigator.credentials.create({
      publicKey: {
        challenge,
        rp: { name: 'VELORA', id: window.location.hostname },
        user: {
          id: new TextEncoder().encode(userId),
          name: userName,
          displayName: userName,
        },
        pubKeyCredParams: [
          { type: 'public-key', alg: -7 },
          { type: 'public-key', alg: -257 },
        ],
        authenticatorSelection: {
          authenticatorAttachment: 'platform',
          userVerification: 'required',
          residentKey: 'preferred',
        },
        timeout: 60000,
      },
    }) as PublicKeyCredential | null
    if (!cred) return false
    localStorage.setItem(CRED_KEY, bufToB64(cred.rawId))
    localStorage.setItem('velora_lock_type', 'biometric')
    return true
  } catch (e) {
    console.warn('biometric register failed', e)
    return false
  }
}

export async function verifyBiometric(): Promise<boolean> {
  try {
    const id = localStorage.getItem(CRED_KEY)
    if (!id) return false
    const challenge = crypto.getRandomValues(new Uint8Array(32))
    const cred = await navigator.credentials.get({
      publicKey: {
        challenge,
        timeout: 60000,
        userVerification: 'required',
        allowCredentials: [{
          type: 'public-key',
          id: b64ToBuf(id),
          transports: ['internal'],
        }],
      },
    })
    return !!cred
  } catch (e) {
    console.warn('biometric verify failed', e)
    return false
  }
}

export function hasBiometricRegistered(): boolean {
  return !!localStorage.getItem(CRED_KEY)
}

export function clearBiometric(): void {
  localStorage.removeItem(CRED_KEY)
  if (localStorage.getItem('velora_lock_type') === 'biometric') {
    localStorage.removeItem('velora_lock_type')
  }
}
