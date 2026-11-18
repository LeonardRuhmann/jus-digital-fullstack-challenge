/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Geist", "Inter", "system-ui", "-apple-system", "sans-serif"],
      },
      colors: {
        // Exact Radix/Figma color tokens extracted from Propostas prototype
        brand: {
          green: "#30A46C",       // Green/9 - Sidebar BG & Primary buttons
          greenHover: "#29915E",  // Hover state for primary buttons
          greenActive: "#5BB98B", // Green/8 - Active sidebar menu item
          greenLight: "#FBFEFC",  // Green/1 - Sidebar primary text
          greenMuted: "#C4E8D1",  // Green/5 - Sidebar subtitle text
        },
        slate: {
          1: "#FCFCFD",  // Main canvas & Dialog background
          2: "#F9F9FB",  // Modal document preview background
          3: "#F0F0F3",  // Input fields & secondary pill background
          6: "#D9D9E0",  // Card, container & dashed dropzone borders
          10: "#80838D", // Muted metadata (date, size, extension, placeholder)
          11: "#60646C", // Secondary labels & dropdown menu items
          12: "#1C2024", // Primary headings & titles
        },
        selection: {
          bg: "#E6F4FE",     // Blue/3 - Selected Document Card background
          border: "#0090FF", // Blue/9 - Selected checkmark badge
        },
        danger: {
          DEFAULT: "#E5484D", // Red/9 - Destructive actions & errors
        },
      },
    },
  },
  plugins: [],
};
