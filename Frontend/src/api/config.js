export function getApiBaseUrl(env) {
  const value = env.VITE_API_URL?.trim()
  if (!value && env.DEV && !import.meta.env?.PROD) return 'http://127.0.0.1:8000'
  try {
    const url = new URL(value)
    const local = ['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)
    if ((!env.DEV && (url.protocol !== 'https:' || local)) ||
        !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash) {
      throw new Error('invalid')
    }
    return value.replace(/\/+$/, '')
  } catch {
    throw new Error('VITE_API_URL deve definir a URL HTTPS pública da API para o build.')
  }
}
