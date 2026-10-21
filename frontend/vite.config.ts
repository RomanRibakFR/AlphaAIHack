import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// для npm run dev: /api на локальный бэк (в докере это делает nginx)
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": "http://localhost:8000" },
  },
});
