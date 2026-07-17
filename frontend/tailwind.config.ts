import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        cfb: {
          navy: "#0b1d3a",
          crimson: "#a6192e",
          gold: "#c9a227",
        },
      },
    },
  },
  plugins: [],
};

export default config;
