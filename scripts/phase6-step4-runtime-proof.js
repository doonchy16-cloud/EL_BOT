'use strict';
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const python = String(process.env.EL_PYTHON || '').trim();
const registry = String(process.env.EL_FORGEY_REGISTRY || '').trim();
const launcher = path.join(ROOT, 'scripts', 'run-step4-runtime.py');
const evidenceDir = path.join(ROOT, 'data', 'phase6-step4');

if (!python) throw new Error('EL_PYTHON is required');
if (!fs.existsSync(python)) throw new Error('EL_PYTHON does not exist');
if (!registry || !fs.existsSync(registry)) throw new Error('EL_FORGEY_REGISTRY is required');
if (!fs.existsSync(launcher)) throw new Error('Step-4 runtime launcher is missing');

function conceptFold(value) {
  return Array.from(String(value || '').normalize('NFKC'))
    .filter((char) => !/\p{Cf}/u.test(char))
    .join('')
    .replace(/\s+/gu, ' ')
    .trim()
    .replace(/[.!?]+$/u, '')
    .trim()
    .toLocaleLowerCase('en-US');
}
function codePoints(value) {
  return Array.from(String(value || '')).map((char) => `U+${char.codePointAt(0).toString(16).toUpperCase().padStart(4,'0')}`).join(' ');
}

function infer(input, expectedWinner, evidenceName, { conceptExact = false } = {}) {
  const run = spawnSync(python, [launcher, '🔀'], {
    cwd: ROOT,
    input,
    encoding: 'utf8',
    windowsHide: true,
    maxBuffer: 16 * 1024 * 1024,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', EL_FORGEY_REGISTRY: registry },
  });
  if (run.error) throw run.error;
  if (run.status !== 0) throw new Error(`runtime exited ${run.status}: ${String(run.stderr || '').slice(0, 1000)}`);
  const stdout = String(run.stdout || '').trim();
  if (!stdout.startsWith('{') || !stdout.endsWith('}')) throw new Error(`runtime stdout is not one JSON object: ${stdout.slice(0, 300)}`);
  let payload;
  try { payload = JSON.parse(stdout); }
  catch (error) { throw new Error(`runtime JSON parse failed: ${error.message}`); }
  const metrics = payload && payload.metrics || {};
  const winner = String(payload && payload.winner || '');
  const winnerMatches = conceptExact ? conceptFold(winner) === conceptFold(expectedWinner) : winner === expectedWinner;
  if (!winnerMatches) {
    throw new Error(`winner mismatch: expected ${JSON.stringify(expectedWinner)} [${codePoints(expectedWinner)}], got ${JSON.stringify(winner)} [${codePoints(winner)}]`);
  }
  if (conceptExact && Number(metrics.roundtrip) !== 1) throw new Error(`reverse concept matched but deterministic round-trip was not exact: ${metrics.roundtrip}`);
  if (metrics.forgey_primary_released !== true) {
    throw new Error(`Forgey primary was not released: rejection=${JSON.stringify(metrics.forgey_rejection_reason || null)} validation=${JSON.stringify(metrics.forgey_validation || null)} assist=${JSON.stringify(metrics.assist_path || null)} roundtrip=${JSON.stringify(metrics.roundtrip ?? null)}`);
  }
  if (Number(metrics.provider_calls) !== 0) throw new Error('provider call occurred on successful Forgey-primary inference');
  if (metrics.forgey_generation !== 'G2') throw new Error(`selected generation is not G2: ${metrics.forgey_generation}`);
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceDir, evidenceName), JSON.stringify(payload, null, 2) + '\n', 'utf8');
  return { payload, stderrBytes: Buffer.byteLength(String(run.stderr || ''), 'utf8'), winnerMatches };
}

const forward = infer('2\nvehicle powered by pedals with two wheels', '🚲', 'primary-forward.json');
const reverse = infer('1\n🚲', 'bicycle', 'primary-reverse.json', { conceptExact: true });
const streamProof = {
  schema_version: 1,
  stdout_json_exact: true,
  stdout_stderr_separated: true,
  forward_winner: forward.payload.winner,
  reverse_winner: reverse.payload.winner,
  reverse_concept_exact: reverse.winnerMatches,
  reverse_roundtrip_exact: Number(reverse.payload.metrics.roundtrip) === 1,
  generation: forward.payload.metrics.forgey_generation,
  provider_calls: forward.payload.metrics.provider_calls,
  forward_stderr_bytes: forward.stderrBytes,
  reverse_stderr_bytes: reverse.stderrBytes,
};
fs.writeFileSync(path.join(evidenceDir, 'runtime-stream-proof.json'), JSON.stringify(streamProof, null, 2) + '\n', 'utf8');
console.log(`PHASE6_STEP4_RUNTIME_OK forward=🚲 reverse=${JSON.stringify(reverse.payload.winner)} concept=bicycle roundtrip=1 generation=G2 provider=0`);
