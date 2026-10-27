/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./login.html",
    "./admin.html"
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        primary: '#FC4C02',
        'primary-hover': '#E34402',
        secondary: '#242428',
        tertiary: '#FC4C02',
        'tertiary-hover': '#E34402',
        'tertiary-active': '#C93B00',
        'tertiary-subtle': '#FFF3ED',
        'brand-orange': '#FC4C02',
        'brand-orange-hover': '#E34402',
        'brand-teal': '#FC4C02',
        'brand-teal-hover': '#E34402',
        'action-red': '#FC4C02',
        'action-red-hover': '#E34402',
        neutral: '#FFFFFF',
        'flat-green': '#10B981',
        'flat-orange': '#FC4C02',
        'flat-amber': '#F59E0B',
        bg: 'var(--bg-color)',
        surface: 'var(--surface-color)',
        'surface-subtle': 'var(--surface-subtle)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        border: 'var(--border-color)',
        'border-strong': 'var(--border-strong)',
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        display: ['-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace']
      },
      borderRadius: {
        sm: '4px',
        DEFAULT: '6px',
        md: '8px',
        lg: '12px',
        xl: '16px',
        '2xl': '20px',
        pill: '9999px',
        none: '0px'
      },
      boxShadow: {
        none: 'none',
        xs: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
        sm: '0 1px 3px 0 rgba(0, 0, 0, 0.08), 0 1px 2px -1px rgba(0, 0, 0, 0.04)',
        md: '0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.04)',
      }
    }
  },
  plugins: [],
}
