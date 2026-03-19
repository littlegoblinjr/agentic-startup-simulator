/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                background: '#05070a', // Deep Space Black
                surface: '#0d1117', // Dark Slate
                primary: '#4f46e5', // Deep Indigo
                glow: '#818cf8', // Light Indigo for glow
                accent: '#c084fc', // Orchid/Violet
                danger: '#f43f5e', // Rose-500
            },
            fontFamily: {
                sans: ['Inter', 'sans-serif'],
                mono: ['JetBrains Mono', 'monospace'],
            },
            backgroundImage: {
                'circuit-pattern': "url('https://www.transparenttextures.com/patterns/carbon-fibre.png')", // Fallback pattern
            },
            boxShadow: {
                'neon-indigo': '0 0 20px rgba(79, 70, 229, 0.4)',
                'neon-glow': '0 0 40px rgba(129, 140, 248, 0.2)',
            }
        },
    },
    plugins: [],
}
