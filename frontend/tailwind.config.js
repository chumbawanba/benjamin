/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Verde-petróleo — cor de destaque da app (tema escuro estilo trading).
        petrol: {
          50: '#e6f5f4',
          100: '#ccebe8',
          200: '#99d6d1',
          300: '#66c2ba',
          400: '#33ada3',
          500: '#0f8f84',
          600: '#0c726a',
          700: '#0a5a54',
          800: '#07423e',
          900: '#052b28',
        },
      },
    },
  },
  plugins: [],
};
