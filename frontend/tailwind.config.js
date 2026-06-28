/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          950: '#050E1C',
          900: '#0A1628',
          800: '#0F2040',
          700: '#162D58',
          600: '#1E3A6E',
        },
        azure: {
          600: '#0078D4',
          500: '#0086F0',
          400: '#2899F5',
        },
        teal: {
          400: '#00B4D8',
          300: '#22D3EE',
        },
        gold: {
          400: '#FFB700',
          300: '#FFC933',
        },
        emerald: {
          400: '#00C978',
          300: '#34D399',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'azure-gradient': 'linear-gradient(135deg, #0078D4, #0086F0)',
        'navy-gradient': 'linear-gradient(180deg, #0A1628 0%, #050E1C 100%)',
      },
      animation: {
        'spin-slow': 'spin 2s linear infinite',
        'pulse-glow': 'pulse-glow 2s ease-in-out infinite',
        'fade-in-up': 'fadeInUp 0.4s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(0,134,240,0.4)' },
          '50%': { boxShadow: '0 0 0 8px rgba(0,134,240,0)' },
        },
        fadeInUp: {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      backdropBlur: {
        xl: '24px',
      },
    },
  },
  plugins: [],
}
