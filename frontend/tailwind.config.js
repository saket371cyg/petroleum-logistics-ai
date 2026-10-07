/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"IBM Plex Sans"', 'sans-serif'],
        mono: ['"IBM Plex Mono"', 'monospace'],
      },
      colors: {
        canvas: '#0E1316',
        surface: {
          DEFAULT: '#161C20',
          2: '#1D242A',
          3: '#242C33',
        },
        line: {
          DEFAULT: '#2A333A',
          strong: '#3A454D',
        },
        ink: {
          primary: '#E7ECEE',
          secondary: '#9AA7AE',
          muted: '#6B767C',
        },
        amber: {
          DEFAULT: '#E8A23A',
          soft: '#3A2E1A',
        },
        rust: {
          DEFAULT: '#D9622F',
        },
        teal: {
          DEFAULT: '#3FA9A0',
          soft: '#173330',
        },
        good: {
          DEFAULT: '#4FAE79',
          soft: '#16301F',
        },
        warn: {
          DEFAULT: '#E8A23A',
          soft: '#3A2E1A',
        },
        bad: {
          DEFAULT: '#E2574C',
          soft: '#3A1E1B',
        },
      },
      borderRadius: {
        card: '10px',
      },
      boxShadow: {
        none: 'none',
      },
    },
  },
  plugins: [],
}
