/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        severity: {
          critical: '#dc2626', // red-600
          high: '#ea580c',     // orange-600
          medium: '#ca8a04',   // yellow-600
          low: '#2563eb',      // blue-600
        },
        trend: {
          up: '#16a34a',       // green-600
          down: '#dc2626',     // red-600
          neutral: '#6b7280',  // gray-500
        },
      },
    },
  },
  plugins: [],
}
