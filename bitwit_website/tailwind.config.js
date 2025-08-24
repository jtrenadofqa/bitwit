    /** @type {import('tailwindcss').Config} */
    module.exports = {
      content: [
        "./src/**/*.{js,jsx,ts,tsx}", // This is crucial for Tailwind to find your classes
        "./public/index.html",
      ],
      theme: {
        extend: {
          fontFamily: {
            inter: ['Inter', 'sans-serif'],
          },
          colors: {
            'gray-950': '#0A0A0A',
          },
        },
      },
      plugins: [],
    }
    