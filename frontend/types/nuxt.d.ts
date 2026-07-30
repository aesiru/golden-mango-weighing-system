// Type declarations for global variables
declare global {
  interface Window {
    __NUXT_AUTH__?: {
      token: string
      refreshToken: string
      isAuthenticated: boolean
    }
  }
}

export {}
