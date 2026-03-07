import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // React core — always needed, separate for caching
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/scheduler/")) {
            return "react-vendor";
          }
          // React Router — routing
          if (id.includes("node_modules/react-router") || id.includes("node_modules/@remix-run/router")) {
            return "router";
          }
          // Recharts — heavy charts, only loaded for Insights
          if (id.includes("node_modules/recharts")) {
            return "recharts";
          }
          // React Icons — UI icons
          if (id.includes("node_modules/react-icons")) {
            return "react-icons";
          }
          // Utils — axios, jwt-decode
          if (id.includes("node_modules/axios") || id.includes("node_modules/jwt-decode")) {
            return "utils";
          }
        },
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]",
      },
    },
    chunkSizeWarningLimit: 400,
  },
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
