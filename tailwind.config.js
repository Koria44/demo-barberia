/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
    './static/js/**/*.js',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Paleta inspirada en barbería de lujo y viggomhc.cl
        bg: {
          dark: '#0A0A0A',    // Fondo principal negro carbón
          surface: '#141414', // Superficie de tarjetas y contenedores
          elevated: '#1C1C1C',// Superficie elevada / dropdowns
          border: '#2A2A2A',  // Bordes sutiles
        },
        gold: {
          DEFAULT: '#C9A24B', // Dorado acento de conversión
          hover: '#DDB968',   // Dorado claro al pasar el cursor
          light: '#F2DFAB',   // Brillo sutil
          dark: '#8C6C26',    // Dorado apagado
        },
        ivory: {
          DEFAULT: '#F5F0E6', // Texto marfil principal
          muted: '#A8A294',   // Texto secundario
          dim: '#6E695F',     // Texto tenue / placeholders
        },
        status: {
          success: '#3E8E5E', // Éxito / Confirmada (verde apagado)
          error: '#B3412F',   // Error / Cancelada (rojo ladrillo)
          warning: '#D4973B', // Pendiente / Alerta
          info: '#3B7ED4',    // Informativo
        }
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'gold-glow': '0 0 25px -5px rgba(201, 162, 75, 0.3)',
        'gold-glow-lg': '0 0 40px -5px rgba(201, 162, 75, 0.45)',
        'card-dark': '0 10px 30px -10px rgba(0, 0, 0, 0.8)',
      },
      animation: {
        'pulse-subtle': 'pulseSubtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'shimmer': 'shimmer 2.5s infinite linear',
        'marquee': 'marquee 25s linear infinite',
      },
      keyframes: {
        pulseSubtle: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.85', transform: 'scale(1.03)' },
        },
        shimmer: {
          '0%': { transform: 'translateX(-100%)' },
          '100%': { transform: 'translateX(100%)' },
        },
        marquee: {
          '0%': { transform: 'translateX(0%)' },
          '100%': { transform: 'translateX(-50%)' },
        }
      }
    },
  },
  plugins: [],
}
