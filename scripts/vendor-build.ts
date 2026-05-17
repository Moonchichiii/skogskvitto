import { copyFileSync, mkdirSync, statSync } from "node:fs";

mkdirSync("static/vendor", { recursive: true });

const files: ReadonlyArray<readonly [string, string]> = [
  ["node_modules/alpinejs/dist/cdn.min.js", "static/vendor/alpine.min.js"],
  ["node_modules/htmx.org/dist/htmx.min.js", "static/vendor/htmx.min.js"],
];

for (const [src, dest] of files) {
  copyFileSync(src, dest);
  const size = (statSync(dest).size / 1024).toFixed(2);
  console.log(`  ${dest}  ${size} KB`);
}