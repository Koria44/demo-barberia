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
        // Nueva identidad visual: Blanco y Negro, minimalista y editorial
        bg: {
          main: '#FFFFFF',     // Fondo principal blanco puro
          alt: '#F7F7F5',      // Fondo alterno de secciones (blanco roto sutil)
          surface: '#FFFFFF',  // Superficie de tarjetas
          elevated: '#FAFAF8', // Superficie elevada / dropdowns
          border: '#E7E7E4',   // Líneas y divisores 1px
          dark: '#0A0A0A',     // Secciones invertidas (Hero, CTA, Footer)
          'dark-surface': '#141414',
          'dark-border': '#262626',
        },
        // Mapeo retrocompatible para clases heredadas
        ivory: {
          DEFAULT: '#0A0A0A',  // Pasa a texto principal oscuro sobre fondos claros
          light: '#FFFFFF',    // Blanco para secciones invertidas
          muted: '#5C5C58',    // Texto secundario
          dim: '#9A9A95',      // Texto terciario / deshabilitado
        },
        // Acciones editoriales: el antiguo dorado pasa a negro puro
        gold: {
          DEFAULT: '#0A0A0A',  // Acción primaria negra
          hover: '#262626',    // Hover carbón oscuro
          light: '#F7F7F5',    // Acento muy sutil en gris claro
          dark: '#000000',     // Negro profundo
          subtle: '#E7E7E4',   // Borde neutro
        },
        // Texto general
        text: {
          main: '#0A0A0A',     // Texto principal / negro carbón
          muted: '#5C5C58',    // Texto secundario / gris medio
          dim: '#9A9A95',      // Texto terciario / deshabilitado
          inverse: '#FFFFFF',  // Texto blanco sobre fondo oscuro
        },
        // Acciones
        brand: {
          black: '#0A0A0A',
          hover: '#262626',
          white: '#FFFFFF',
          border: '#E7E7E4',
        },
        // Colores funcionales desaturados y moderados (solo para estado, no decorativos)
        status: {
          success: '#2F7D4F', // Éxito / Confirmada (verde bosque sobrio)
          error: '#B3412F',   // Error / Cancelada (rojo teja)
          warning: '#B7791F', // Pendiente / Alerta (ocre apagado)
          info: '#2D3748',    // Informativo (gris pizarra)
        }
      },
      fontFamily: {
        serif: ['"Playfair Display"', 'Georgia', 'serif'],
        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
      },
      boxShadow: {
        'soft': '0 8px 30px rgba(0, 0, 0, 0.06)',
        'card': '0 4px 20px rgba(0, 0, 0, 0.04)',
        'card-dark': '0 10px 30px -10px rgba(0, 0, 0, 0.5)',
        'gold-glow': '0 4px 20px rgba(0, 0, 0, 0.08)',
        'gold-glow-lg': '0 8px 30px rgba(0, 0, 0, 0.12)',
      },
      animation: {
        'pulse-subtle': 'pulseSubtle 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'marquee': 'marquee 25s linear infinite',
      },
      keyframes: {
        pulseSubtle: {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.9', transform: 'scale(1.02)' },
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
