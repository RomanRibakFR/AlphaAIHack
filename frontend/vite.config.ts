import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// для npm run dev: /api на локальный бэк (в докере это делает nginx).
// API_URL позволяет направить фронт на другой стенд, не трогая конфиг.
const API_URL = process.env.API_URL ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": API_URL },
  },
});
