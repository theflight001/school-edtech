const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const files = require('./runtime-files.json');
const out = path.join(root, 'dist');
for (const file of files) {
  if (file.includes('..') || path.isAbsolute(file) || !fs.statSync(path.join(root, file)).isFile()) throw new Error(`Missing runtime file: ${file}`);
}
fs.rmSync(out, {recursive:true, force:true});
fs.mkdirSync(out);
let bytes = 0;
for (const file of files) {
  const dest = path.join(out, file);
  fs.mkdirSync(path.dirname(dest), {recursive:true});
  fs.copyFileSync(path.join(root,file),dest);
  bytes += fs.statSync(dest).size;
}
console.log(`Static release: ${files.length} files, ${bytes} bytes`);
