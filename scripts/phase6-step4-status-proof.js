'use strict';
const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const python = String(process.env.EL_PYTHON || '').trim();
const registry = String(process.env.EL_FORGEY_REGISTRY || '').trim();
const collector = path.join(ROOT, 'scripts', 'phase6-step4-status.py');
const evidenceDir = path.join(ROOT, 'data', 'phase6-step4');

if (!python || !fs.existsSync(python)) throw new Error('EL_PYTHON is required');
if (!registry || !fs.existsSync(registry)) throw new Error('EL_FORGEY_REGISTRY is required');
if (!fs.existsSync(collector)) throw new Error('Step-4 status collector is missing');

const run = spawnSync(python, [collector, '--registry', registry, '--validate'], { cwd: ROOT, encoding: 'utf8', windowsHide: true, maxBuffer: 32 * 1024 * 1024, env: { ...process.env, PYTHONIOENCODING: 'utf-8', EL_FORGEY_REGISTRY: registry } });
if (run.error) throw run.error;
if (run.status !== 0) throw new Error(`status collector exited ${run.status}: ${String(run.stderr || '').slice(0, 1000)}`);
const stdout = String(run.stdout || '').trim();
if (!stdout.startsWith('{') || !stdout.endsWith('}')) throw new Error(`status stdout is not one JSON object: ${stdout.slice(0, 300)}`);
let payload; try { payload = JSON.parse(stdout); } catch (error) { throw new Error(`status JSON parse failed: ${error.message}`); }

if (payload.available !== true) throw new Error(`status unavailable: ${payload.reason || 'unknown'}`);
if (!payload.registry || payload.registry.hashes_verified !== true) throw new Error('registry hashes are not verified');
if (payload.registry.selected_generation !== 'G2') throw new Error(`selected generation is not G2: ${payload.registry.selected_generation}`);
if (!payload.model || payload.model.loadable !== true) throw new Error('selected model is not loadable');
const params = Number(payload.model.trainable_parameters);
if (!(params >= 1000000 && params <= 3000000)) throw new Error(`trainable parameter count outside authority: ${params}`);
if (payload.model.vision_enabled !== true || !(Number(payload.model.vision_parameters) > 0)) throw new Error('selected model is not natively vision-enabled');
if (Number(payload.model.vision_image_size) !== 64 || Number(payload.model.vision_patch_size) !== 8 || Number(payload.model.visual_tokens) !== 64) throw new Error('native vision geometry mismatch');
if (!(Number(payload.model.model_file_bytes) > 0)) throw new Error('real model file size missing');
if (!(Number(payload.model.tokenizer_file_bytes) > 0)) throw new Error('real tokenizer file size missing');
if (!payload.training || payload.training.vision_validation_pass !== true || !/^\d+\/\d+$/.test(String(payload.training.vision_probes || ''))) throw new Error('native vision promotion metrics missing');
if (!payload.diagnostics || payload.diagnostics.passed !== true || Number(payload.diagnostics.count) !== 44) throw new Error('44/44 diagnostics missing from status');
if (!payload.validation || payload.validation.registry_hashes !== true || payload.validation.model_loadable !== true || payload.validation.native_vision !== true || payload.validation.diagnostics_passed !== true) throw new Error('status validation proof failed');

fs.mkdirSync(evidenceDir, { recursive: true });
fs.writeFileSync(path.join(evidenceDir, 'status.json'), JSON.stringify(payload, null, 2) + '\n', 'utf8');
fs.writeFileSync(path.join(evidenceDir, 'status-stream-proof.json'), JSON.stringify({ schema_version: 2, stdout_json_exact: true, stdout_stderr_separated: true, stderr_bytes: Buffer.byteLength(String(run.stderr || ''), 'utf8'), selected_generation: payload.registry.selected_generation, trainable_parameters: params, native_vision: true, vision_parameters: payload.model.vision_parameters, vision_probes: payload.training.vision_probes, model_file_bytes: payload.model.model_file_bytes, tokenizer_file_bytes: payload.model.tokenizer_file_bytes, diagnostics: `${payload.diagnostics.count}/44 PASS` }, null, 2) + '\n', 'utf8');
console.log(`PHASE6_STEP4_STATUS_OK generation=G2 params=${params} vision_params=${payload.model.vision_parameters} diagnostics=44/44`);