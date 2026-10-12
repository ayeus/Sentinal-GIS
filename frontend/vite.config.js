import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Output layout matches what the backend, Dockerfile and nginx config serve:
// frontend/build/index.html with hashed assets under build/static/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 3000 },
  build: { outDir: "build", assetsDir: "static", chunkSizeWarningLimit: 900 },
  test: { globals: true, environment: "node" },
});
