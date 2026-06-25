import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

const djangoTarget = process.env.VITE_SSK_API_PROXY_TARGET || "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": {
        target: djangoTarget,
        changeOrigin: true,
      },
    },
  },
});
