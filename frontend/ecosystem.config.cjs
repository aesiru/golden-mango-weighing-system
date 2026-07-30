module.exports = {
  apps: [
    {
      name: 'eam-frontend',
      cwd: __dirname,
      script: './.output/server/index.mjs',
      interpreter: 'node',
      exec_mode: 'fork',
      instances: 1,
      watch: false,
      max_memory_restart: '512M',
      env: {
        NODE_ENV: 'production',
        HOST: '127.0.0.1',
        PORT: '3010',
        NUXT_PUBLIC_API_URL: '/api'
      }
    }
  ]
}
