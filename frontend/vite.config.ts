import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, ".", "");
  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": env.VITE_API_PROXY_TARGET || "http://localhost:8000",
        "/ready": env.VITE_API_PROXY_TARGET || "http://localhost:8000",
      },
    },
    test: {
      environment: "jsdom",
      setupFiles: "./src/test/setup.ts",
      exclude: ["e2e/**", "node_modules/**", "dist/**"],
    },
  };
});
