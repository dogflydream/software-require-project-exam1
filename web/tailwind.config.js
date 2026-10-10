/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50:'#ecfdf5',100:'#d1fae5',200:'#a7f3d0',300:'#6ee7b7',400:'#34d399',
          500:'#10b981',600:'#059669',700:'#047857',800:'#065f46',900:'#064e3b',
        },
        canvas:   'var(--c-bg)',
        surface:  'var(--c-surface)',
        elevated: 'var(--c-elevated)',
        line:     'var(--c-border)',
        ink:      'var(--c-text)',
        muted:    'var(--c-muted)',
        subtle:   'var(--c-subtle)',
      },
      fontFamily: {
        sans: ['"Segoe UI"','-apple-system','BlinkMacSystemFont','"PingFang SC"','"Microsoft YaHei"','system-ui','sans-serif'],
        mono: ['"JetBrains Mono"','Consolas','monospace'],
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,32,26,.04), 0 8px 24px -12px rgba(16,32,26,.12)',
        lift: '0 2px 6px rgba(16,32,26,.06), 0 18px 40px -18px rgba(16,32,26,.22)',
      },
      borderRadius: { xl2: '1.25rem' },
      keyframes: {
        rise:  { '0%':{opacity:0, transform:'translateY(10px)'}, '100%':{opacity:1, transform:'none'} },
        pop:   { '0%':{opacity:0, transform:'scale(.96)'}, '100%':{opacity:1, transform:'none'} },
      },
      animation: { rise:'rise .34s cubic-bezier(.22,1,.36,1) both', pop:'pop .18s ease-out both' },
    },
  },
  plugins: [],
}
