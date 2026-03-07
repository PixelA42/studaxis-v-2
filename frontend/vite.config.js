import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        strictPort: false,
        proxy: {
            // Proxy /api to Python backend (FastAPI on port 6782)
            "/api": {
                target: "http://localhost:6782",
                changeOrigin: true,
                secure: false,
            },
        },
    },
});
