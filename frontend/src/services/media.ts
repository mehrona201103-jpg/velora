/** Resolve media path for img/src (DB media, uploads, absolute URLs). */
export function mediaUrl(url?: string | null): string {
  if (!url) return 'data:image/svg+xml,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400"><rect fill="#f3f0ff" width="100%" height="100%"/><text x="50%" y="50%" text-anchor="middle" fill="#a78bfa" font-size="18">VELORA</text></svg>')
  if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('data:')) return url
  // /api/v1/media/1 or /uploads/...
  if (url.startsWith('/')) return url
  return '/' + url
}
