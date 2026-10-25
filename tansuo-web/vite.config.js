import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { registerApi } from './server/api.js'

export default defineConfig({
  plugins: [
    vue(),
    {
      name: 'tansuo-api',
      configureServer(server) {
        registerApi(server)
      },
      configurePreviewServer(server) {
        registerApi(server)
      }
    }
  ],
  server: {
    host: '0.0.0.0',
    port: 5173,
    allowedHosts: true
  },
  preview: {
    host: '0.0.0.0',
    port: 5173
  }
})
