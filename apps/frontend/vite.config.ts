import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

function normalizedBasePath() {
  const raw = process.env.VITE_BASE_PATH || "/";
  const withLeadingSlash = raw.startsWith("/") || raw.startsWith("http") ? raw : `/${raw}`;
  return withLeadingSlash.endsWith("/") ? withLeadingSlash : `${withLeadingSlash}/`;
}

export default defineConfig({
  base: normalizedBasePath(),
  plugins: [vue()]
});

