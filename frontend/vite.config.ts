import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["vite.svg", "assets/fonts/*.woff2", "pwa-512x512.png"],
      manifest: {
        name: "Studaxis — Offline-first AI Tutor",
        short_name: "Studaxis",
        description: "Offline-first AI tutor for students",
        theme_color: "#00A8E8",
        background_color: "#0F172A",
        display: "standalone",
        scope: "/",
        icons: [
          {
            src: "pwa-512x512.png",
            sizes: "192x192",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any",
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable",
          },
        ],
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2,woff,ttf}"],
        navigateFallbackDenylist: [/^\/api\//],
        /* API routes bypass SW; static assets use precache (CacheFirst) */
      },
      devOptions: {
        enabled: false,
      },
    }),
  ],
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
