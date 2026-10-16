const fs = require('fs');
const path = require('path');

const distDir = path.resolve(__dirname, 'dist');

// Clear and recreate dist/ directory
if (fs.existsSync(distDir)) {
  fs.rmSync(distDir, { recursive: true, force: true });
}
fs.mkdirSync(distDir, { recursive: true });

// List of standalone files to copy
const filesToCopy = [
  'index.html',
  'login.html',
  'admin.html',
  'manifest.json',
  'sw.js',
  'favicon.ico',
  'apple-touch-icon.png'
];

for (const file of filesToCopy) {
  const src = path.resolve(__dirname, file);
  const dest = path.resolve(distDir, file);
  if (fs.existsSync(src)) {
    fs.copyFileSync(src, dest);
    console.log(`Copied ${file} -> dist/${file}`);
  }
}

// Copy public/ folder if it exists
const publicSrc = path.resolve(__dirname, 'public');
const publicDest = path.resolve(distDir, 'public');
if (fs.existsSync(publicSrc)) {
  fs.cpSync(publicSrc, publicDest, { recursive: true });
  console.log('Copied public/ -> dist/public/');
}

console.log('Build completed successfully. Files are in dist/');
