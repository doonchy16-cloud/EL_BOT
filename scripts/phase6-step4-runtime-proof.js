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

function infer(input, expectedWinner, evidenceName) {
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
  if (payload.winner !== expectedWinner) throw new Error(`winner mismatch: expected ${expectedWinner}, got ${payload.winner}`);
  if (metrics.forgey_primary_released !== true) throw new Error('Forgey primary was not released');
  if (Number(metrics.provider_calls) !== 0) throw new Error('provider call occurred on successful Forgey-primary inference');
  if (metrics.forgey_generation !== 'G2') throw new Error(`selected generation is not G2: ${metrics.forgey_generation}`);
  fs.mkdirSync(evidenceDir, { recursive: true });
  fs.writeFileSync(path.join(evidenceDir, evidenceName), JSON.stringify(payload, null, 2) + '\n', 'utf8');
  return { payload, stderrBytes: Buffer.byteLength(String(run.stderr || ''), 'utf8') };
}

const forward = infer('2\nvehicle powered by pedals with two wheels', '🚲', 'primary-forward.json');
const reverse = infer('1\n🚲', 'bicycle', 'primary-reverse.json');
const streamProof = {
  schema_version: 1,
  stdout_json_exact: true,
  stdout_stderr_separated: true,
  forward_winner: forward.payload.winner,
  reverse_winner: reverse.payload.winner,
  generation: forward.payload.metrics.forgey_generation,
  provider_calls: forward.payload.metrics.provider_calls,
  forward_stderr_bytes: forward.stderrBytes,
  reverse_stderr_bytes: reverse.stderrBytes,
};
fs.writeFileSync(path.join(evidenceDir, 'runtime-stream-proof.json'), JSON.stringify(streamProof, null, 2) + '\n', 'utf8');
console.log('PHASE6_STEP4_RUNTIME_OK forward=🚲 reverse=bicycle generation=G2 provider=0');
