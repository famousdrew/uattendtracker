/** @type {import('next').NextConfig} */
const nextConfig = {
  // Use standalone output for Docker deployment
  // Creates a standalone folder without node_modules dependencies
  output: 'standalone',

  // Environment variables available at build time
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_ZENDESK_SUBDOMAIN: process.env.NEXT_PUBLIC_ZENDESK_SUBDOMAIN || 'workwelltech',
  },

  // Image optimization for production
  images: {
    // Configure allowed image domains if needed
    domains: [],
    // Optimize images for deployment
    minimumCacheTTL: 60 * 10, // 10 minutes
  },

  // Compress responses
  compress: true,

  // Disable React DevTools in production
  reactStrictMode: true,

  // Disable Next.js telemetry
  telemetry: false,

  // PoweredBy header for security
  poweredByHeader: false,

  // Production optimizations
  productionBrowserSourceMaps: false,

  // Internationalization (i18n) configuration if needed
  // i18n: {
  //   locales: ['en'],
  //   defaultLocale: 'en',
  // },

  // API rewrites for development proxy (if needed)
  // rewrites: async () => {
  //   return {
  //     beforeFiles: [
  //       // API proxy rules can be added here
  //     ],
  //   };
  // },

  // Security headers
  async headers() {
    return [
      {
        source: '/:path*',
        headers: [
          {
            key: 'X-Content-Type-Options',
            value: 'nosniff',
          },
          {
            key: 'X-Frame-Options',
            value: 'DENY',
          },
          {
            key: 'X-XSS-Protection',
            value: '1; mode=block',
          },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
        ],
      },
    ];
  },
}

module.exports = nextConfig
