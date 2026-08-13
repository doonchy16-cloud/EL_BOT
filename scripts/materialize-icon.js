'use strict';
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const identity = JSON.parse(fs.readFileSync(path.join(root, '🪪', '🎛️'), 'utf8'));
const source = path.join(root, '🪪', String(identity.icon_asset || '🎨'));
const bytes = Buffer.from(fs.readFileSync(source, 'utf8').trim(), 'base64');
const png = Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]);
if (bytes.length < 100 || !bytes.subarray(0, 8).equals(png)) throw new Error('identity icon is not a PNG');
const outDir = path.join(root, 'build');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'el-bot.png'), bytes);
console.log('✅🎨📦');
