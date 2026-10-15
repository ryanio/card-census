// Tweet images: screenshots of the live site plus every share card, retaken in one go before posting.
// usage: node scripts/shots.mjs [siteUrl] [outDir]   (defaults: the live site, ./tweet-images)
// Needs Google Chrome. Prints the headline numbers so the copy can be checked against the page.
import { spawn } from "node:child_process";
import { writeFile, mkdir, mkdtemp } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

const [base = "https://ryanio.github.io/card-census/", outDir = "tweet-images"] = process.argv.slice(2);
const CHROME = process.env.CHROME || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
await mkdir(join(outDir, "cards"), { recursive: true });
const profile = await mkdtemp(join(tmpdir(), "shots-"));
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=0", `--user-data-dir=${profile}`, "--hide-scrollbars", "--no-first-run", "about:blank"], { stdio: ["ignore", "ignore", "pipe"] });
const wsUrl = await new Promise((resolve, reject) => { let buf = ""; chrome.stderr.on("data", (d) => { buf += d; const m = buf.match(/DevTools listening on (ws:\/\/\S+)/); if (m) resolve(m[1]); }); setTimeout(() => reject(new Error("Chrome did not start; set CHROME to its path")), 15000); });
const ws = new WebSocket(wsUrl); await new Promise((r) => ws.addEventListener("open", r));
let id = 0; const pending = new Map();
ws.addEventListener("message", (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) { const { resolve, reject } = pending.get(m.id); pending.delete(m.id); m.error ? reject(new Error(m.error.message)) : resolve(m.result); } });
const send = (method, params = {}, sessionId) => new Promise((resolve, reject) => { const i = ++id; pending.set(i, { resolve, reject }); ws.send(JSON.stringify({ id: i, method, params, sessionId })); });
const { targetId } = await send("Target.createTarget", { url: "about:blank" });
const { sessionId } = await send("Target.attachToTarget", { targetId, flatten: true });
const s = (m, p) => send(m, p, sessionId);
await s("Page.enable"); await s("Network.enable");
await s("Network.setBlockedURLs", { urls: ["*googletagmanager.com*", "*google-analytics.com*"] });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ev = async (expr) => (await s("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.value;

async function open({ width, height, mobile = false, hash = "", clean = false }) {
  await s("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: mobile ? 3 : 2, mobile });
  await s("Emulation.setTouchEmulationEnabled", { enabled: mobile });
  await s("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }, { name: "prefers-reduced-motion", value: "reduce" }] });
  await s("Page.navigate", { url: base + "?shot=" + Date.now() + (hash ? "#" + hash : "") });
  await sleep(4500); await ev("document.fonts.ready.then(() => true)");
  if (clean) await ev(`(() => { const st = document.createElement("style"); st.textContent = ".mast{display:none!important} html{scroll-padding-top:0} .share{display:none!important}"; document.head.appendChild(st); return true; })()`);
}
async function save(name, data) { await writeFile(join(outDir, name), Buffer.from(data, "base64")); console.log("  " + name); }
// wait for two fresh frames, so a capture never reuses the frame from before a hover
const painted = () => ev("new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(() => r(1))))");
async function viewport(name) { await painted(); await save(name, (await s("Page.captureScreenshot", { format: "png", captureBeyondViewport: false })).data); }
async function element(name, selector, { pad = 28, wait = 1200 } = {}) {
  await ev(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({ block: "center" }); true`); await sleep(wait);
  await painted();
  const r = await ev(`(() => { const b = document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect(); return { x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height }; })()`);
  await save(name, (await s("Page.captureScreenshot", { format: "png", captureBeyondViewport: true, clip: { x: Math.max(0, r.x - pad), y: Math.max(0, r.y - pad), width: r.w + pad * 2, height: r.h + pad * 2, scale: 1 } })).data);
}
async function hoverCard() {
  const p = await ev(`(() => { const c = document.getElementById("cmap-top").getBoundingClientRect(), [x, y] = document.getElementById("cmap").dataset.hero.split(",").map(Number); return { x: c.left + x, y: c.top + y }; })()`);
  await s("Input.dispatchMouseEvent", { type: "mouseMoved", x: p.x - 4, y: p.y }); await sleep(80);
  await s("Input.dispatchMouseEvent", { type: "mouseMoved", x: p.x, y: p.y });
  await ev(`new Promise((r) => { const t = Date.now(); (function w() { const i = document.querySelector("#cprev img"); if ((i && i.classList.contains("on")) || Date.now() - t > 8000) r(1); else setTimeout(w, 150); })(); })`);
  await sleep(300);
}

try {
  console.log("screenshots");
  await open({ width: 1600, height: 1000 });
  await viewport("cover.png");
  // the most valuable card on the map, with its preview open
  await hoverCard(); await viewport("cover-preview.png");
  await s("Input.dispatchMouseEvent", { type: "mouseMoved", x: 5, y: 5 }); await sleep(300);
  await ev(`(() => { const t = [...document.querySelectorAll(".ctag")].find((e) => /^POKEMON/i.test(e.innerText)); t && t.dispatchEvent(new Event("mouseenter")); return 1; })()`); await sleep(600);
  await viewport("cover-pokemon.png");
  await ev(`(() => { document.querySelectorAll(".ctag").forEach((e) => e.dispatchEvent(new Event("mouseleave"))); const r = [...document.querySelectorAll(".trow")].find((e) => /Luffy/.test(e.innerText)); r && r.dispatchEvent(new Event("mouseenter")); return 1; })()`); await sleep(600);
  await viewport("cover-luffy.png");
  await open({ width: 1400, height: 1000, clean: true });
  await element("map.png", "#cmap", { pad: 24 });
  await element("lot-01.png", "#lot-1");
  await element("grades.png", "#fig-grades");
  await element("vaults.png", "#vaults", { pad: 32 });
  await element("pop-report-chart.png", "#fig-pop");
  await open({ width: 1280, height: 900, clean: true });
  await ev(`(() => { const r = document.querySelector('.trow[data-slug="card-monkey-d-luffy"]'); r && r.click(); return 1; })()`);
  await sleep(4000); await ev(`document.activeElement && document.activeElement.blur(); true`);
  await element("luffy-pop-report.png", "#dlg", { pad: 0, wait: 300 });
  await open({ width: 390, height: 844, mobile: true });
  await viewport("phone-cover.png");

  console.log("share cards (what X shows for each link)");
  const HL = await ev(`(() => { const h = JSON.parse(document.getElementById("highlights-data").textContent); return [...h.h.map((x) => x.id), ...Object.values(h.c)]; })()`);
  const extra = ["most-tens", "map"];
  for (const k of ["og", ...HL.filter((k) => !k.startsWith("card-")), ...extra, ...HL.filter((k) => k.startsWith("card-")).slice(0, 12)]) {
    const url = k === "og" ? base + "og.png" : base + "s/" + k + ".png";
    const r = await fetch(url + "?v=" + Date.now());
    if (!r.ok) { console.log("  missing " + url); continue; }
    await writeFile(join(outDir, k.startsWith("card-") ? "cards" : "", (k === "og" ? "link-card" : "share-" + k) + ".png"), Buffer.from(await r.arrayBuffer()));
    console.log("  " + (k === "og" ? "link-card.png  " + base : "share-" + k + ".png  " + base + "s/" + k + "/"));
  }

  console.log("numbers on the page now");
  console.log(await ev(`(() => { const S = JSON.parse(document.getElementById("summary").textContent), t = (p) => p.reduce((a, x) => a + (parseFloat(x[0]) >= 10 ? x[1] : 0), 0), sub = Object.fromEntries(S.subjects.map((x) => [x.s, x])), g = Object.fromEntries(S.graders.map((x) => [x.g, x])), fr = S.franchises[0];
    const lines = ["snapshot " + S.at, "cards " + S.n.toLocaleString(), fr.f + " " + Math.round(fr.n / S.n * 100) + "% (" + fr.n.toLocaleString() + ")"];
    for (const k of ["Pikachu", "Charizard", "Monkey D. Luffy", "Michael Jordan"]) if (sub[k]) lines.push(k + ": " + sub[k].n.toLocaleString() + " cards, " + t(sub[k].grade).toLocaleString() + " 10s of " + sub[k].graded.toLocaleString() + " graded");
    const gd = S.grade.reduce((a, x) => a + x[1], 0); lines.push("10s share " + Math.round(t(S.grade) / gd * 100) + "%, PSA " + Math.round(g.PSA.ten / g.PSA.n * 100) + "%, CGC " + Math.round(g.CGC.ten / g.CGC.n * 100) + "%");
    (S.issuers || []).forEach((x) => lines.push(x.name + " " + x.n.toLocaleString() + " (" + Math.round(x.n / S.n * 100) + "%)"));
    if (S.top[0]) lines.push("top card " + S.top[0].t + " " + S.top[0].g + " $" + S.top[0].v.toLocaleString());
    return lines.map((l) => "  " + l).join("\\n"); })()`));
} finally {
  ws.close(); chrome.kill();
}
