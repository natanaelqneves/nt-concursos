import { defineConfig } from "astro/config";

export default defineConfig({
  site: "https://ntconcursos.com.br",
  output: "static",
  trailingSlash: "always",
  build: { format: "directory" },
  compressHTML: true,
});
