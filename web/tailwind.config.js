/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Nunito', 'sans-serif'],
        display: ['Quicksand', 'sans-serif'],
      },
    },
  },
  plugins: [require("daisyui")],
  daisyui: {
    themes: [
      {
        kawaii: {
          "primary": "#8b5cf6",
          "secondary": "#a78bfa",
          "accent": "#6366f1",
          "neutral": "#f8fafc",
          "base-100": "#ffffff",
          "base-200": "#f8fafc",
          "base-300": "#f1f5f9",
          "info": "#93c5fd",
          "success": "#86efac",
          "warning": "#fde047",
          "error": "#fca5a5",
        },
      },
      "cupcake",
    ],
  },
}
