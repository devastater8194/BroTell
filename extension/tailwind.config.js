/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./popup.html",
    "./sidepanel.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        slate: {
          850: '#1e293b', // Custom middle tone
        }
      }
    },
  },
  plugins: [],
}
