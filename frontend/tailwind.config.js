/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'brand-blue': '#062474',
        'brand-mint': '#66f0cb',
        'brand-mint-light': '#e0fbf4',
        'brand-gray': '#f8f9fa',
        'brand-text': '#1a1a1a',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
