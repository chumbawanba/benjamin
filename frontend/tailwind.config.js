/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Navy — cor de destaque da app, alinhada com o Primary (#0F172A) do
        // BRAND.md (2026-07-21, substituiu o antigo "petrol" verde-petróleo).
        // Saturação mais alta que o "slate" (já usado como neutro/fundo em toda
        // a UI) para o accent continuar distinguível do chrome neutro.
        navy: {
          50: '#eef1f8',
          100: '#dce3f1',
          200: '#b9c7e3',
          300: '#93a8d1',
          400: '#6685bb',
          500: '#46639e',
          600: '#344e82',
          700: '#283d68',
          800: '#1c2c4d',
          900: '#0f172a',
        },
      },
    },
  },
  plugins: [],
};
