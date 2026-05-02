// @ts-check
const esbuild = require("esbuild");

const production = process.argv.includes("--production");
const watch = process.argv.includes("--watch");

/** @type {import("esbuild").BuildOptions} */
const baseOptions = {
  entryPoints: ["src/extension.ts"],
  bundle: true,
  outfile: "out/extension.js",
  external: ["vscode"],          // vscode is provided by the host
  format: "cjs",
  platform: "node",
  target: "node18",
  sourcemap: !production,
  minify: production,
  treeShaking: true,
  logLevel: "info",
};

async function main() {
  if (watch) {
    const ctx = await esbuild.context(baseOptions);
    await ctx.watch();
    console.log("[esbuild] watching…");
  } else {
    await esbuild.build(baseOptions);
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
