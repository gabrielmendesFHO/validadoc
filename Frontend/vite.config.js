import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import process from 'node:process'
import { getApiBaseUrl } from './src/api/config.js'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const env = loadEnv(mode, process.cwd(), 'VITE_')
  getApiBaseUrl({ ...env, DEV: command === 'serve' })
  return { plugins: [react()], base: '/' }
})
