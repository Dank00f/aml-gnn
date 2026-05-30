import type { NextConfig } from 'next'

const BACKEND_URL = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:9090'

const nextConfig: NextConfig = {
  allowedDevOrigins: ['127.0.0.1', 'localhost'],
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${BACKEND_URL}/api/:path*`
      }
    ]
  }
}

export default nextConfig
