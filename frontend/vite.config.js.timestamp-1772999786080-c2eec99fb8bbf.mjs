// vite.config.js
import { defineConfig } from "file:///H:/Projects_AI/studaxis-vtwo/frontend/node_modules/vite/dist/node/index.js";
import react from "file:///H:/Projects_AI/studaxis-vtwo/frontend/node_modules/@vitejs/plugin-react/dist/index.js";
import { VitePWA } from "file:///H:/Projects_AI/studaxis-vtwo/frontend/node_modules/vite-plugin-pwa/dist/index.js";
var vite_config_default = defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: "autoUpdate",
      includeAssets: ["vite.svg", "assets/fonts/*.woff2", "pwa-512x512.png"],
      manifest: {
        name: "Studaxis \u2014 Offline-first AI Tutor",
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
            purpose: "any"
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "any"
          },
          {
            src: "pwa-512x512.png",
            sizes: "512x512",
            type: "image/png",
            purpose: "maskable"
          }
        ]
      },
      workbox: {
        globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2,woff,ttf}"],
        navigateFallbackDenylist: [/^\/api\//]
        /* API routes bypass SW; static assets use precache (CacheFirst) */
      },
      devOptions: {
        enabled: false
      }
    })
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: function(id) {
          if (id.includes("node_modules/react/") || id.includes("node_modules/react-dom/") || id.includes("node_modules/scheduler/")) {
            return "react-vendor";
          }
          if (id.includes("node_modules/react-router") || id.includes("node_modules/@remix-run/router")) {
            return "router";
          }
          if (id.includes("node_modules/recharts")) {
            return "recharts";
          }
          if (id.includes("node_modules/react-icons")) {
            return "react-icons";
          }
          if (id.includes("node_modules/axios") || id.includes("node_modules/jwt-decode")) {
            return "utils";
          }
        },
        chunkFileNames: "assets/[name]-[hash].js",
        entryFileNames: "assets/[name]-[hash].js",
        assetFileNames: "assets/[name]-[hash][extname]"
      }
    },
    chunkSizeWarningLimit: 400
  },
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      // Proxy /api to Python backend. Match run.py --port (default 6782).
      // Set VITE_API_PORT=6783 when using: python run.py --port 6783
      "/api": {
        target: "http://localhost:".concat(process.env.VITE_API_PORT || 6782),
        changeOrigin: true,
        secure: false
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJIOlxcXFxQcm9qZWN0c19BSVxcXFxzdHVkYXhpcy12dHdvXFxcXGZyb250ZW5kXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ZpbGVuYW1lID0gXCJIOlxcXFxQcm9qZWN0c19BSVxcXFxzdHVkYXhpcy12dHdvXFxcXGZyb250ZW5kXFxcXHZpdGUuY29uZmlnLmpzXCI7Y29uc3QgX192aXRlX2luamVjdGVkX29yaWdpbmFsX2ltcG9ydF9tZXRhX3VybCA9IFwiZmlsZTovLy9IOi9Qcm9qZWN0c19BSS9zdHVkYXhpcy12dHdvL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSBcInZpdGVcIjtcbmltcG9ydCByZWFjdCBmcm9tIFwiQHZpdGVqcy9wbHVnaW4tcmVhY3RcIjtcbmltcG9ydCB7IFZpdGVQV0EgfSBmcm9tIFwidml0ZS1wbHVnaW4tcHdhXCI7XG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICAgIHBsdWdpbnM6IFtcbiAgICAgICAgcmVhY3QoKSxcbiAgICAgICAgVml0ZVBXQSh7XG4gICAgICAgICAgICByZWdpc3RlclR5cGU6IFwiYXV0b1VwZGF0ZVwiLFxuICAgICAgICAgICAgaW5jbHVkZUFzc2V0czogW1widml0ZS5zdmdcIiwgXCJhc3NldHMvZm9udHMvKi53b2ZmMlwiLCBcInB3YS01MTJ4NTEyLnBuZ1wiXSxcbiAgICAgICAgICAgIG1hbmlmZXN0OiB7XG4gICAgICAgICAgICAgICAgbmFtZTogXCJTdHVkYXhpcyBcdTIwMTQgT2ZmbGluZS1maXJzdCBBSSBUdXRvclwiLFxuICAgICAgICAgICAgICAgIHNob3J0X25hbWU6IFwiU3R1ZGF4aXNcIixcbiAgICAgICAgICAgICAgICBkZXNjcmlwdGlvbjogXCJPZmZsaW5lLWZpcnN0IEFJIHR1dG9yIGZvciBzdHVkZW50c1wiLFxuICAgICAgICAgICAgICAgIHRoZW1lX2NvbG9yOiBcIiMwMEE4RThcIixcbiAgICAgICAgICAgICAgICBiYWNrZ3JvdW5kX2NvbG9yOiBcIiMwRjE3MkFcIixcbiAgICAgICAgICAgICAgICBkaXNwbGF5OiBcInN0YW5kYWxvbmVcIixcbiAgICAgICAgICAgICAgICBzY29wZTogXCIvXCIsXG4gICAgICAgICAgICAgICAgaWNvbnM6IFtcbiAgICAgICAgICAgICAgICAgICAge1xuICAgICAgICAgICAgICAgICAgICAgICAgc3JjOiBcInB3YS01MTJ4NTEyLnBuZ1wiLFxuICAgICAgICAgICAgICAgICAgICAgICAgc2l6ZXM6IFwiMTkyeDE5MlwiLFxuICAgICAgICAgICAgICAgICAgICAgICAgdHlwZTogXCJpbWFnZS9wbmdcIixcbiAgICAgICAgICAgICAgICAgICAgICAgIHB1cnBvc2U6IFwiYW55XCIsXG4gICAgICAgICAgICAgICAgICAgIH0sXG4gICAgICAgICAgICAgICAgICAgIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHNyYzogXCJwd2EtNTEyeDUxMi5wbmdcIixcbiAgICAgICAgICAgICAgICAgICAgICAgIHNpemVzOiBcIjUxMng1MTJcIixcbiAgICAgICAgICAgICAgICAgICAgICAgIHR5cGU6IFwiaW1hZ2UvcG5nXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICBwdXJwb3NlOiBcImFueVwiLFxuICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgICAgICB7XG4gICAgICAgICAgICAgICAgICAgICAgICBzcmM6IFwicHdhLTUxMng1MTIucG5nXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICBzaXplczogXCI1MTJ4NTEyXCIsXG4gICAgICAgICAgICAgICAgICAgICAgICB0eXBlOiBcImltYWdlL3BuZ1wiLFxuICAgICAgICAgICAgICAgICAgICAgICAgcHVycG9zZTogXCJtYXNrYWJsZVwiLFxuICAgICAgICAgICAgICAgICAgICB9LFxuICAgICAgICAgICAgICAgIF0sXG4gICAgICAgICAgICB9LFxuICAgICAgICAgICAgd29ya2JveDoge1xuICAgICAgICAgICAgICAgIGdsb2JQYXR0ZXJuczogW1wiKiovKi57anMsY3NzLGh0bWwsaWNvLHBuZyxzdmcsd29mZjIsd29mZix0dGZ9XCJdLFxuICAgICAgICAgICAgICAgIG5hdmlnYXRlRmFsbGJhY2tEZW55bGlzdDogWy9eXFwvYXBpXFwvL10sXG4gICAgICAgICAgICAgICAgLyogQVBJIHJvdXRlcyBieXBhc3MgU1c7IHN0YXRpYyBhc3NldHMgdXNlIHByZWNhY2hlIChDYWNoZUZpcnN0KSAqL1xuICAgICAgICAgICAgfSxcbiAgICAgICAgICAgIGRldk9wdGlvbnM6IHtcbiAgICAgICAgICAgICAgICBlbmFibGVkOiBmYWxzZSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgIH0pLFxuICAgIF0sXG4gICAgYnVpbGQ6IHtcbiAgICAgICAgcm9sbHVwT3B0aW9uczoge1xuICAgICAgICAgICAgb3V0cHV0OiB7XG4gICAgICAgICAgICAgICAgbWFudWFsQ2h1bmtzOiBmdW5jdGlvbiAoaWQpIHtcbiAgICAgICAgICAgICAgICAgICAgLy8gUmVhY3QgY29yZSBcdTIwMTQgYWx3YXlzIG5lZWRlZCwgc2VwYXJhdGUgZm9yIGNhY2hpbmdcbiAgICAgICAgICAgICAgICAgICAgaWYgKGlkLmluY2x1ZGVzKFwibm9kZV9tb2R1bGVzL3JlYWN0L1wiKSB8fCBpZC5pbmNsdWRlcyhcIm5vZGVfbW9kdWxlcy9yZWFjdC1kb20vXCIpIHx8IGlkLmluY2x1ZGVzKFwibm9kZV9tb2R1bGVzL3NjaGVkdWxlci9cIikpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBcInJlYWN0LXZlbmRvclwiO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIC8vIFJlYWN0IFJvdXRlciBcdTIwMTQgcm91dGluZ1xuICAgICAgICAgICAgICAgICAgICBpZiAoaWQuaW5jbHVkZXMoXCJub2RlX21vZHVsZXMvcmVhY3Qtcm91dGVyXCIpIHx8IGlkLmluY2x1ZGVzKFwibm9kZV9tb2R1bGVzL0ByZW1peC1ydW4vcm91dGVyXCIpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gXCJyb3V0ZXJcIjtcbiAgICAgICAgICAgICAgICAgICAgfVxuICAgICAgICAgICAgICAgICAgICAvLyBSZWNoYXJ0cyBcdTIwMTQgaGVhdnkgY2hhcnRzLCBvbmx5IGxvYWRlZCBmb3IgSW5zaWdodHNcbiAgICAgICAgICAgICAgICAgICAgaWYgKGlkLmluY2x1ZGVzKFwibm9kZV9tb2R1bGVzL3JlY2hhcnRzXCIpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gXCJyZWNoYXJ0c1wiO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgICAgIC8vIFJlYWN0IEljb25zIFx1MjAxNCBVSSBpY29uc1xuICAgICAgICAgICAgICAgICAgICBpZiAoaWQuaW5jbHVkZXMoXCJub2RlX21vZHVsZXMvcmVhY3QtaWNvbnNcIikpIHtcbiAgICAgICAgICAgICAgICAgICAgICAgIHJldHVybiBcInJlYWN0LWljb25zXCI7XG4gICAgICAgICAgICAgICAgICAgIH1cbiAgICAgICAgICAgICAgICAgICAgLy8gVXRpbHMgXHUyMDE0IGF4aW9zLCBqd3QtZGVjb2RlXG4gICAgICAgICAgICAgICAgICAgIGlmIChpZC5pbmNsdWRlcyhcIm5vZGVfbW9kdWxlcy9heGlvc1wiKSB8fCBpZC5pbmNsdWRlcyhcIm5vZGVfbW9kdWxlcy9qd3QtZGVjb2RlXCIpKSB7XG4gICAgICAgICAgICAgICAgICAgICAgICByZXR1cm4gXCJ1dGlsc1wiO1xuICAgICAgICAgICAgICAgICAgICB9XG4gICAgICAgICAgICAgICAgfSxcbiAgICAgICAgICAgICAgICBjaHVua0ZpbGVOYW1lczogXCJhc3NldHMvW25hbWVdLVtoYXNoXS5qc1wiLFxuICAgICAgICAgICAgICAgIGVudHJ5RmlsZU5hbWVzOiBcImFzc2V0cy9bbmFtZV0tW2hhc2hdLmpzXCIsXG4gICAgICAgICAgICAgICAgYXNzZXRGaWxlTmFtZXM6IFwiYXNzZXRzL1tuYW1lXS1baGFzaF1bZXh0bmFtZV1cIixcbiAgICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgICAgIGNodW5rU2l6ZVdhcm5pbmdMaW1pdDogNDAwLFxuICAgIH0sXG4gICAgc2VydmVyOiB7XG4gICAgICAgIHBvcnQ6IDUxNzMsXG4gICAgICAgIHN0cmljdFBvcnQ6IGZhbHNlLFxuICAgICAgICBwcm94eToge1xuICAgICAgICAgICAgLy8gUHJveHkgL2FwaSB0byBQeXRob24gYmFja2VuZC4gTWF0Y2ggcnVuLnB5IC0tcG9ydCAoZGVmYXVsdCA2NzgyKS5cbiAgICAgICAgICAgIC8vIFNldCBWSVRFX0FQSV9QT1JUPTY3ODMgd2hlbiB1c2luZzogcHl0aG9uIHJ1bi5weSAtLXBvcnQgNjc4M1xuICAgICAgICAgICAgXCIvYXBpXCI6IHtcbiAgICAgICAgICAgICAgICB0YXJnZXQ6IFwiaHR0cDovL2xvY2FsaG9zdDpcIi5jb25jYXQocHJvY2Vzcy5lbnYuVklURV9BUElfUE9SVCB8fCA2NzgyKSxcbiAgICAgICAgICAgICAgICBjaGFuZ2VPcmlnaW46IHRydWUsXG4gICAgICAgICAgICAgICAgc2VjdXJlOiBmYWxzZSxcbiAgICAgICAgICAgIH0sXG4gICAgICAgIH0sXG4gICAgfSxcbn0pO1xuIl0sCiAgIm1hcHBpbmdzIjogIjtBQUF5UyxTQUFTLG9CQUFvQjtBQUN0VSxPQUFPLFdBQVc7QUFDbEIsU0FBUyxlQUFlO0FBQ3hCLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQ3hCLFNBQVM7QUFBQSxJQUNMLE1BQU07QUFBQSxJQUNOLFFBQVE7QUFBQSxNQUNKLGNBQWM7QUFBQSxNQUNkLGVBQWUsQ0FBQyxZQUFZLHdCQUF3QixpQkFBaUI7QUFBQSxNQUNyRSxVQUFVO0FBQUEsUUFDTixNQUFNO0FBQUEsUUFDTixZQUFZO0FBQUEsUUFDWixhQUFhO0FBQUEsUUFDYixhQUFhO0FBQUEsUUFDYixrQkFBa0I7QUFBQSxRQUNsQixTQUFTO0FBQUEsUUFDVCxPQUFPO0FBQUEsUUFDUCxPQUFPO0FBQUEsVUFDSDtBQUFBLFlBQ0ksS0FBSztBQUFBLFlBQ0wsT0FBTztBQUFBLFlBQ1AsTUFBTTtBQUFBLFlBQ04sU0FBUztBQUFBLFVBQ2I7QUFBQSxVQUNBO0FBQUEsWUFDSSxLQUFLO0FBQUEsWUFDTCxPQUFPO0FBQUEsWUFDUCxNQUFNO0FBQUEsWUFDTixTQUFTO0FBQUEsVUFDYjtBQUFBLFVBQ0E7QUFBQSxZQUNJLEtBQUs7QUFBQSxZQUNMLE9BQU87QUFBQSxZQUNQLE1BQU07QUFBQSxZQUNOLFNBQVM7QUFBQSxVQUNiO0FBQUEsUUFDSjtBQUFBLE1BQ0o7QUFBQSxNQUNBLFNBQVM7QUFBQSxRQUNMLGNBQWMsQ0FBQywrQ0FBK0M7QUFBQSxRQUM5RCwwQkFBMEIsQ0FBQyxVQUFVO0FBQUE7QUFBQSxNQUV6QztBQUFBLE1BQ0EsWUFBWTtBQUFBLFFBQ1IsU0FBUztBQUFBLE1BQ2I7QUFBQSxJQUNKLENBQUM7QUFBQSxFQUNMO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDSCxlQUFlO0FBQUEsTUFDWCxRQUFRO0FBQUEsUUFDSixjQUFjLFNBQVUsSUFBSTtBQUV4QixjQUFJLEdBQUcsU0FBUyxxQkFBcUIsS0FBSyxHQUFHLFNBQVMseUJBQXlCLEtBQUssR0FBRyxTQUFTLHlCQUF5QixHQUFHO0FBQ3hILG1CQUFPO0FBQUEsVUFDWDtBQUVBLGNBQUksR0FBRyxTQUFTLDJCQUEyQixLQUFLLEdBQUcsU0FBUyxnQ0FBZ0MsR0FBRztBQUMzRixtQkFBTztBQUFBLFVBQ1g7QUFFQSxjQUFJLEdBQUcsU0FBUyx1QkFBdUIsR0FBRztBQUN0QyxtQkFBTztBQUFBLFVBQ1g7QUFFQSxjQUFJLEdBQUcsU0FBUywwQkFBMEIsR0FBRztBQUN6QyxtQkFBTztBQUFBLFVBQ1g7QUFFQSxjQUFJLEdBQUcsU0FBUyxvQkFBb0IsS0FBSyxHQUFHLFNBQVMseUJBQXlCLEdBQUc7QUFDN0UsbUJBQU87QUFBQSxVQUNYO0FBQUEsUUFDSjtBQUFBLFFBQ0EsZ0JBQWdCO0FBQUEsUUFDaEIsZ0JBQWdCO0FBQUEsUUFDaEIsZ0JBQWdCO0FBQUEsTUFDcEI7QUFBQSxJQUNKO0FBQUEsSUFDQSx1QkFBdUI7QUFBQSxFQUMzQjtBQUFBLEVBQ0EsUUFBUTtBQUFBLElBQ0osTUFBTTtBQUFBLElBQ04sWUFBWTtBQUFBLElBQ1osT0FBTztBQUFBO0FBQUE7QUFBQSxNQUdILFFBQVE7QUFBQSxRQUNKLFFBQVEsb0JBQW9CLE9BQU8sUUFBUSxJQUFJLGlCQUFpQixJQUFJO0FBQUEsUUFDcEUsY0FBYztBQUFBLFFBQ2QsUUFBUTtBQUFBLE1BQ1o7QUFBQSxJQUNKO0FBQUEsRUFDSjtBQUNKLENBQUM7IiwKICAibmFtZXMiOiBbXQp9Cg==
