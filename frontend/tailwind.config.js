/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ivory: '#F5F0E6',
        cream: '#F8F4EC',
        beige: '#E8DFD0',
        champagne: '#F0E6D3',
        gold: '#C9A84C',
        'warm-gold': '#B8943F',
        charcoal: '#2C2C2C',
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
