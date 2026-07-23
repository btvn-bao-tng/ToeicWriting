import { build, context } from "esbuild";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = resolve(__dirname, "..");
const entry = resolve(root, "src/static/_entry.jsx");
const outdir = resolve(root, "src/static/dist");
const isWatch = process.argv.includes("--watch");

const options = {
  entryPoints: [entry],
  bundle: true,
  minify: true,
  target: ["es2020"],
  jsx: "transform",
  jsxFactory: "React.createElement",
  jsxFragment: "React.Fragment",
  outfile: resolve(outdir, "app.js"),
  sourcemap: false,
  legalComments: "none",
  logLevel: "info",
  define: {
    "process.env.NODE_ENV": '"production"',
  },
  loader: { ".jsx": "jsx" },
};

if (isWatch) {
  const ctx = await context(options);
  await ctx.watch();
  console.log("Watching for changes...");
} else {
  await build(options);
  console.log("Build complete: src/static/dist/app.js");
}
