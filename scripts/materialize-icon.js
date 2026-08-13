'use strict';
const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const identity = JSON.parse(fs.readFileSync(path.join(root, '🪪', '🎛️'), 'utf8'));
const source = path.join(root, '🪪', String(identity.icon_asset || '🎨'));
const bytes = Buffer.from(fs.readFileSync(source, 'utf8').trim(), 'base64');
const pngSignature = Buffer.from([0x89,0x50,0x4e,0x47,0x0d,0x0a,0x1a,0x0a]);
if (bytes.length < 100 || !bytes.subarray(0, 8).equals(pngSignature)) throw new Error('identity icon is not a PNG');
if (bytes.readUInt32BE(16) !== 256 || bytes.readUInt32BE(20) !== 256) throw new Error('identity icon must be 256x256');

// ICO supports a PNG-compressed 256x256 image directly. Build the container
// ourselves so Windows packaging uses the validated identity pixels without a
// lossy or libvips-dependent PNG -> ICO conversion step.
const header = Buffer.alloc(22);
header.writeUInt16LE(0, 0);       // reserved
header.writeUInt16LE(1, 2);       // type: icon
header.writeUInt16LE(1, 4);       // image count
header[6] = 0;                    // width 256
header[7] = 0;                    // height 256
header[8] = 0;                    // palette count: unspecified
header[9] = 0;                    // reserved
header.writeUInt16LE(1, 10);      // color planes
header.writeUInt16LE(32, 12);     // nominal bit depth
header.writeUInt32LE(bytes.length, 14);
header.writeUInt32LE(header.length, 18);
const ico = Buffer.concat([header, bytes]);
if (!ico.subarray(22, 30).equals(pngSignature)) throw new Error('ICO payload materialization failed');

const outDir = path.join(root, 'build');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'el-bot.png'), bytes);
fs.writeFileSync(path.join(outDir, 'el-bot.ico'), ico);
console.log('✅🎨🪟📦');
