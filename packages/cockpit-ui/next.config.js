/** @type {import('next').NextConfig} */
const nextConfig = {
  // output: 'export' is required for the static bundle served by drift-cockpit,
  // but breaks dynamic routes in dev mode.  Activate only during `next build`.
  ...(process.env.NODE_ENV === 'production' ? { output: 'export', trailingSlash: true } : {}),
  env: {
    COCKPIT_API_URL: process.env.COCKPIT_API_URL || 'http://localhost:8001',
  },
}

module.exports = nextConfig
