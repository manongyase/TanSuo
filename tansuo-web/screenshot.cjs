// 本地截图：先起 preview（或直接用 5173 守护），然后 puppeteer 截
// 用法：先确保 preview 在跑，node screenshot.cjs
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const url = process.env.URL || 'http://localhost:4173/';
const outDir = path.join(__dirname, '.screenshots');
fs.mkdirSync(outDir, { recursive: true });

const views = [
  { name: 'mobile-iphone12', width: 390, height: 844, ua: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1' },
  { name: 'mobile-android', width: 393, height: 852, ua: 'Mozilla/5.0 (Linux; Android 14; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Mobile Safari/537.36' },
  { name: 'desktop-1440', width: 1440, height: 900, ua: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/130.0' },
];

(async () => {
  const browser = await puppeteer.launch({
    executablePath: '/usr/bin/chromium-browser',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--disable-dev-shm-usage'],
    headless: true,
  });

  for (const v of views) {
    console.log(`→ ${v.name} (${v.width}x${v.height}) ...`);
    const page = await browser.newPage({ viewport: { width: v.width, height: v.height }, userAgent: v.ua });
    await page.goto(url, { waitUntil: 'networkidle2', timeout: 20000 });
    // 等 Vue mount + 数据拉完
    await page.waitForTimeout(2500);
    // 找一下可能的 console error
    const errors = [];
    page.on('pageerror', (e) => errors.push(e.message));
    page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
    const out = path.join(outDir, `${v.name}.png`);
    await page.screenshot({ path: out, fullPage: true });
    console.log(`  ✓ saved ${out}`);
    if (errors.length) console.log(`  ⚠️ console errors:`, errors.join(' | '));
    await page.close();
  }

  await browser.close();
  console.log('done');
})();
