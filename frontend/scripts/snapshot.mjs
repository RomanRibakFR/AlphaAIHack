/**
 * Склеивает собранный лендинг в один самодостаточный HTML-файл.
 *
 * Зачем: показать страницу живой, не поднимая ни сервера, ни докера —
 * файл открывается двойным кликом и остаётся кликабельным.
 *
 * Внутрь уезжают стили, скрипт и три начертания фирменного шрифта
 * (в base64, иначе по file:// они не подгрузятся). Внешних запросов
 * после склейки не остаётся.
 *
 * Запуск: npm run snapshot
 */
import { readFile, writeFile, mkdir } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const BUILD = resolve(root, "dist-snapshot");
const OUT = resolve(root, "..", "docs", "frontend", "snapshot", "landing.html");

/** Шрифты лежат в public и в сборку попадают как есть, по абсолютным путям. */
async function fontDataUri(publicPath) {
  const file = resolve(root, "public", publicPath.replace(/^\//, ""));
  const base64 = (await readFile(file)).toString("base64");
  return `data:font/woff2;base64,${base64}`;
}

/** Заменяет url(/alfa/fonts/…woff2) на base64 прямо в тексте стилей. */
async function inlineFonts(css) {
  const urls = [...new Set([...css.matchAll(/url\(["']?(\/alfa\/[^"')]+\.woff2)["']?\)/g)].map((m) => m[1]))];
  let result = css;
  for (const url of urls) {
    const dataUri = await fontDataUri(url);
    result = result.replaceAll(url, () => dataUri);
  }
  return { css: result, count: urls.length };
}

const html = await readFile(resolve(BUILD, "index.html"), "utf8");

const scriptSrc = html.match(/<script[^>]+src="([^"]+)"[^>]*><\/script>/);
const styleHref = html.match(/<link[^>]+rel="stylesheet"[^>]*href="([^"]+)"[^>]*>/);
if (!scriptSrc || !styleHref) {
  throw new Error("В собранном index.html не нашлись ссылки на скрипт и стили");
}

const rawCss = await readFile(resolve(BUILD, styleHref[1].replace(/^\//, "")), "utf8");
const { css, count } = await inlineFonts(rawCss);

// Закрывающий тег внутри кода оборвал бы <script> раньше времени.
// Сейчас в бандле его нет, но замена оставлена на будущее: без неё
// случайная строка "</script" в коде развалила бы всю страницу.
const js = (await readFile(resolve(BUILD, scriptSrc[1].replace(/^\//, "")), "utf8")).replaceAll(
  "</script",
  "<\\/script",
);

// Замена обязательно функцией, а не строкой: в строке замены $&, $` и $\'
// — спецпоследовательности, и минифицированный бандл, где такие сочетания
// встречаются, вставился бы покорёженным.
const out = html
  .replace(styleHref[0], () => `<style>\n${css}\n</style>`)
  .replace(scriptSrc[0], () => `<script type="module">\n${js}\n</script>`);

await mkdir(dirname(OUT), { recursive: true });
await writeFile(OUT, out, "utf8");

const mb = (Buffer.byteLength(out) / 1024 / 1024).toFixed(2);
console.log(`Снимок собран: ${OUT}`);
console.log(`Размер ${mb} МБ, шрифтов внутри: ${count}`);
