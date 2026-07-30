// https://nuxt.com/docs/api/configuration/nuxt-config
import { defineNuxtConfig } from 'nuxt/config'

export default defineNuxtConfig({
  experimental: {
    appManifest: false,
  },

  modules: ['@nuxt/eslint', '@nuxt/ui', '@vueuse/nuxt', '@pinia/nuxt', '@nu-grid/nuxt'],

  icon: {
    collections: ['lucide', 'simple-icons']
  },

  colorMode: {
    preference: 'light',
    fallback: 'light'
  },

  ssr: false,

  // Disable heavy DevTools overlay — big lag source in dev mode
  devtools: {
    enabled: false
  },

  css: [
    '~/assets/css/main.css',
    '@quasar/quasar-ui-qcalendar/dist/QCalendarVariables.css',
    '@quasar/quasar-ui-qcalendar/dist/QCalendarMonth.css',
    '@quasar/quasar-ui-qcalendar/dist/QCalendarDay.css',
    '@quasar/quasar-ui-qcalendar/dist/QCalendarResource.css',
    '@quasar/quasar-ui-qcalendar/dist/QCalendarTask.css',
  ],

  runtimeConfig: {
    public: {
      apiUrl: process.env.NUXT_PUBLIC_API_URL || '/api'
    }
  },

  vite: {
    // Speed up HMR and reduce build overhead
    optimizeDeps: {
      // Force pre-bundle these heavy packages on startup, not lazily
      include: [
        'pinia',
        'vue',
        'vue-router',
        '@vueuse/core',
        'socket.io-client',
        '@internationalized/date',
      ]
    },
    server: {
      ws: {
        // keep websocket HMR alive longer to avoid false disconnects
        timeout: 5000
      }
    },
    build: {
      chunkSizeWarningLimit: 1000,
      rollupOptions: {
        // let vite handle chunks automatically
      }
    }
  },

  compatibilityDate: '2025-01-15',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})
