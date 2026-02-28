import path from "path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "tailwindcss";

import mdx from "@mdx-js/rollup";
import rehypeHighlight from "rehype-highlight";

const ReactCompilerConfig = {
  target: "18",
};

export default defineConfig({
  plugins: [
    {enforce: "pre", ...mdx({
      rehypePlugins: [rehypeHighlight]
    })},
    react({
      babel: {
        plugins: [["babel-plugin-react-compiler", ReactCompilerConfig]],
      },
    }),
  ],
  css: {
    postcss: {
      plugins: [tailwindcss()],
    },
  },
  resolve: {
    alias: {
      "@acc": path.resolve(__dirname, "./src"),
    },
  },
});
