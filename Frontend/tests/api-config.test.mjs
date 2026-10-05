import test from 'node:test'
import assert from 'node:assert/strict'
import { getApiBaseUrl } from '../src/api/config.js'

test('desenvolvimento usa API local', () => {
  assert.equal(getApiBaseUrl({ DEV: true }), 'http://127.0.0.1:8000')
})
test('build exige URL HTTPS explicita', () => {
  for (const value of [undefined, '', 'http://api.invalid', 'https://localhost', 'https://u:senha@api.invalid']) {
    assert.throws(() => getApiBaseUrl({ DEV: false, VITE_API_URL: value }), /VITE_API_URL/)
  }
})
test('URL explicita remove barra final', () => {
  assert.equal(getApiBaseUrl({ DEV: false, VITE_API_URL: 'https://api.example.invalid/' }), 'https://api.example.invalid')
})
