import type { Config } from 'tailwindcss'

const config: Config = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Stemacteren brand colors (can be customized)
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          200: '#bae6fd',
          300: '#7dd3fc',
          400: '#38bdf8',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          800: '#075985',
          900: '#0c4a6e',
        },
        // Workshop type colors (configurable)
        workshop: {
          BWS: '#3b82f6', // blue
          BTC: '#8b5cf6', // violet
          VWS: '#10b981', // emerald
          IWS: '#f59e0b', // amber
          AWS: '#ef4444', // red
          LBWS: '#ec4899', // pink
        },
      },
    },
  },
  plugins: [],
}
export default config
