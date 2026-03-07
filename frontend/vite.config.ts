import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      // Proxy /api to Python backend. Match run.py --port (default 6782).
      // Set VITE_API_PORT=6783 when using: python run.py --port 6783
      "/api": {
        target: `http://localhost:${process.env.VITE_API_PORT || 6782}`,
        changeOrigin: true,
        secure: false,
      },
    },
  },
});
