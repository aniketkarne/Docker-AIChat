/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        'netflix-background': '#141414',
        'netflix-primary': '#E50914',
        'netflix-accent': '#B81D24',
        'netflix-text': '#FFFFFF',
        'netflix-card': '#181818'
      }
    }
  },
  plugins: []
};
