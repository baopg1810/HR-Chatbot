/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        'brand-blue': '#062474',
        'brand-mint': '#66f0cb',
        'brand-mint-light': '#e0fbf4',
        'brand-gray': '#f8f9fa',
        'brand-text': '#1a1a1a',
        // Discord Dark Mode Palette
        'discord-bg': '#313338',
        'discord-sidebar': '#2b2d31',
        'discord-card': '#1e1f22',
        'discord-card-hover': '#232428',
        'discord-text': '#dbdee1',
        'discord-text-muted': '#949ba4',
        'discord-accent': '#5865F2',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
