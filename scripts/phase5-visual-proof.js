'use strict';
const { app, BrowserWindow } = require('electron');
const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');
const ffmpeg = require('ffmpeg-static');

const ROOT = path.resolve(__dirname, '..');
const VIEW = path.join(ROOT, '⚡', '🖥️');
const CSS = path.join(ROOT, '⚡', '✨');
const ENHANCE = path.join(ROOT, '⚡', '🎞️');
const OUT = path.resolve(process.env.EL_PHASE5_PROOF_DIR || path.join(ROOT, 'proof', 'phase5'));
const FRAMES = path.join(OUT, 'frames');
const FPS = 30;
const CYCLE_MS = 5600;
const FRAME_COUNT = Math.round(CYCLE_MS / 1000 * FPS);

function sha(buffer) { return crypto.createHash('sha256').update(buffer).digest('hex'); }
function stage(name) { console.log(`PHASE5_PROOF_STAGE ${name}`); }
function runFfmpeg(args) {
  const result = spawnSync(ffmpeg, args, { stdio: 'inherit', windowsHide: true });
  if (result.status !== 0) throw new Error('ffmpeg failed: ' + result.status);
}
async function capture(win, target) {
  try {
    const image = await win.webContents.capturePage();
    const bytes = image.toPNG();
    if (bytes.length < 1000) throw new Error('rendered screenshot is unexpectedly small');
    fs.writeFileSync(target, bytes);
    return bytes;
  } catch (error) {
    throw new Error(`capture failed for ${path.basename(target)}: ${error && error.message ? error.message : error}`);
  }
}
async function angleAt(win, ms) {
  return Number(await win.webContents.executeJavaScript(`(() => {
    document.getAnimations().forEach((a) => { a.pause(); a.currentTime = ${Number(ms)}; });
    const value = getComputedStyle(document.getElementById('hourglass')).transform;
    if (!value || value === 'none') return 0;
    const m = new DOMMatrixReadOnly(value);
    let deg = Math.atan2(m.b, m.a) * 180 / Math.PI;
    if (deg < 0) deg += 360;
    if (deg > 180.0001) deg = 360 - deg;
    return Math.round(deg * 10) / 10;
  })()`, true));
}
async function streamOpacityAt(win, ms) {
  return Number(await win.webContents.executeJavaScript(`(() => {
    document.getAnimations().forEach((a) => { a.pause(); a.currentTime = ${Number(ms)}; });
    return Number(getComputedStyle(document.querySelector('.sandStream')).opacity);
  })()`, true));
}

async function main() {
  stage('prepare');
  fs.rmSync(OUT, { recursive: true, force: true });
  fs.mkdirSync(FRAMES, { recursive: true });
  const viewSource = fs.readFileSync(VIEW, 'utf8');
  if (!/^\s*<!doctype html>/i.test(viewSource) || !viewSource.includes('id="hourglass"')) throw new Error('production UI authority is not valid HTML');
  const proofView = path.join(OUT, 'production-ui-proof.html');
  fs.writeFileSync(proofView, viewSource, 'utf8');
  if (fs.readFileSync(proofView, 'utf8') !== viewSource) throw new Error('proof HTML materialization changed production UI bytes');

  const css = fs.readFileSync(CSS, 'utf8');
  if (!css.includes('@keyframes hourglassFlip')) throw new Error('Phase-5 hourglass keyframes missing');
  if (css.includes('rotate(360deg)')) throw new Error('360-degree hourglass rotation is forbidden');
  if (!css.includes('rotate(180deg)')) throw new Error('180-degree hourglass state missing');

  stage('create-visible-window');
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    show: true,
    skipTaskbar: true,
    backgroundColor: '#080b12',
    webPreferences: { contextIsolation: true, nodeIntegration: false, sandbox: true, backgroundThrottling: false }
  });
  stage('load-production-html');
  await win.loadFile(proofView);
  const renderedAuthority = await win.webContents.executeJavaScript(`(() => {
    const required = ['mode1','mode2','run','image','clear','diag','ollama','input','output','state','hourglass','stageMeta','preview'];
    return required.every((id) => Boolean(document.getElementById(id))) && document.documentElement.tagName === 'HTML';
  })()`, true);
  if (!renderedAuthority) throw new Error('production UI did not render required Phase-5 nodes after HTML materialization');
  stage('inject-production-polish');
  await win.webContents.insertCSS(css);
  await win.webContents.executeJavaScript(fs.readFileSync(ENHANCE, 'utf8'), true);
  await new Promise((resolve) => setTimeout(resolve, 180));

  const sampleSvg = `<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="700"><rect width="100%" height="100%" fill="#101827"/><rect x="60" y="60" width="1080" height="580" rx="30" fill="#17243a" stroke="#76b7ff" stroke-width="5"/><text x="100" y="160" font-family="Segoe UI" font-size="54" fill="white">PHASE 5 SCREENSHOT PREVIEW</text><text x="100" y="250" font-family="Segoe UI" font-size="38" fill="#ffd166">Visible evidence remains inspectable while processing.</text><text x="100" y="335" font-family="Segoe UI" font-size="34" fill="#72f2a6">Click preview to enlarge • Escape to close</text><text x="100" y="430" font-family="Segoe UI" font-size="34" fill="#ffb347">Slow-stage warning proof</text></svg>`;
  const dataUrl = 'data:image/svg+xml;base64,' + Buffer.from(sampleSvg, 'utf8').toString('base64');
  await win.webContents.executeJavaScript(`showImage(${JSON.stringify(dataUrl)});`, true);
  stage('capture-idle');
  await capture(win, path.join(OUT, 'ui-idle.png'));

  stage('capture-preview-zoom');
  await win.webContents.executeJavaScript(`document.getElementById('preview').click();`, true);
  const zoomed = await win.webContents.executeJavaScript(`document.getElementById('preview').classList.contains('zoom') && getComputedStyle(document.getElementById('preview')).position === 'fixed'`, true);
  if (!zoomed) throw new Error('preview zoom did not enter fixed enlarged state');
  await capture(win, path.join(OUT, 'preview-zoom.png'));
  await win.webContents.executeJavaScript(`document.getElementById('preview').click();`, true);

  stage('begin-hourglass');
  await win.webContents.executeJavaScript(`(() => {
    beginProcessing('📸 Screenshot Vision — Phase 5 Render Proof');
    updateStage({index:4,total:7,label:'Screenshot Vision — Observe Visible Facts',warn_after_ms:999999});
    try { if (processingTimer) { clearInterval(processingTimer); processingTimer = 0; } } catch (_) {}
    document.getAnimations().forEach((a) => { a.pause(); a.currentTime = 0; });
  })()`, true);

  stage('capture-168-frames');
  const hashes = new Set();
  for (let i = 0; i < FRAME_COUNT; i += 1) {
    const ms = i * 1000 / FPS;
    await win.webContents.executeJavaScript(`(() => {
      document.getAnimations().forEach((a) => { a.pause(); a.currentTime = ${ms}; });
      document.getElementById('stageMeta').textContent = '4 / 7  •  ⏱️ ${(ms / 1000).toFixed(1)}s  •  Σ ${(ms / 1000).toFixed(1)}s';
    })()`, true);
    const file = path.join(FRAMES, `frame${String(i).padStart(3, '0')}.png`);
    hashes.add(sha(await capture(win, file)));
  }
  if (hashes.size < 24) throw new Error('hourglass render did not produce enough visually distinct frames');

  stage('measure-animation');
  const sampledAngles = {
    start: await angleAt(win, 0),
    inverted: await angleAt(win, CYCLE_MS * 0.50),
    returned: await angleAt(win, CYCLE_MS * 0.96)
  };
  if (Math.abs(sampledAngles.start) > 1.5 || Math.abs(sampledAngles.inverted - 180) > 2 || Math.abs(sampledAngles.returned) > 2) {
    throw new Error('rendered hourglass angle contract failed: ' + JSON.stringify(sampledAngles));
  }
  const streamOpacity = {
    flowing: await streamOpacityAt(win, 1000),
    pausedForFlip: await streamOpacityAt(win, 2050),
    resumedAfterSettle: await streamOpacityAt(win, 3000)
  };
  if (streamOpacity.flowing < .8 || streamOpacity.pausedForFlip > .15 || streamOpacity.resumedAfterSettle < .8) {
    throw new Error('sand pause/resume contract failed: ' + JSON.stringify(streamOpacity));
  }

  stage('capture-warning');
  await win.webContents.executeJavaScript(`(() => {
    document.getElementById('stageMeta').textContent = '4 / 7  •  ⏱️ 46s  •  Σ 52s  ⚠️';
  })()`, true);
  await new Promise((resolve) => setTimeout(resolve, 60));
  const warningOn = await win.webContents.executeJavaScript(`document.getElementById('processing').classList.contains('warn')`, true);
  if (!warningOn) throw new Error('visual slow-stage warning state did not activate');
  await capture(win, path.join(OUT, 'ui-warning.png'));

  stage('encode-mp4');
  runFfmpeg(['-y','-framerate',String(FPS),'-i',path.join(FRAMES,'frame%03d.png'),'-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p',path.join(OUT,'hourglass-30fps.mp4')]);
  stage('encode-contact-sheet');
  runFfmpeg(['-y','-framerate',String(FPS),'-i',path.join(FRAMES,'frame%03d.png'),'-vf','select=not(mod(n\\,7)),scale=350:-1,tile=6x4','-frames:v','1',path.join(OUT,'hourglass-contact-sheet.png')]);

  const proof = {
    schema_version: 1,
    phase: 5,
    github_sha: process.env.GITHUB_SHA || '',
    fps: FPS,
    cycle_ms: CYCLE_MS,
    expected_frames: FRAME_COUNT,
    rendered_frames: FRAME_COUNT,
    distinct_frame_hashes: hashes.size,
    rotation_contract: '0↔180 only',
    sampled_angles_degrees: sampledAngles,
    sand_stream_opacity: streamOpacity,
    warning_state_rendered: Boolean(warningOn),
    preview_zoom_rendered: Boolean(zoomed),
    production_ui_sha256: sha(Buffer.from(viewSource, 'utf8')),
    materialized_ui_sha256: sha(Buffer.from(fs.readFileSync(proofView, 'utf8'), 'utf8')),
    visual_css_sha256: sha(Buffer.from(css, 'utf8')),
    visual_js_sha256: sha(Buffer.from(fs.readFileSync(ENHANCE, 'utf8'), 'utf8'))
  };
  fs.writeFileSync(path.join(OUT, 'proof.json'), JSON.stringify(proof, null, 2));
  fs.rmSync(FRAMES, { recursive: true, force: true });
  stage('complete');
  console.log(`✅📸🎞️${FRAME_COUNT}@${FPS}fps 0↔180 🏖️⏸️✅ 🔍✅ ⚠️✅`);
  win.destroy();
}

app.whenReady().then(main).then(() => app.quit()).catch((error) => {
  console.error(error && error.stack ? error.stack : error);
  app.exit(1);
});
