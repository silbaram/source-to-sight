const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '..');
const pkg = path.join(root, 'node_modules/@dagrejs/dagre');
const dest = path.join(root, 'skills/code-flow/templates/vendor');
fs.mkdirSync(dest, {recursive: true});
// Source maps would request an external file when the generated HTML is inspected.
const js = fs.readFileSync(path.join(pkg, 'dist/dagre.min.js'), 'utf8')
  .replace(/\/\/# sourceMappingURL=.*$/gm, '');
fs.writeFileSync(path.join(dest, 'dagre.min.js'), js);
fs.copyFileSync(path.join(pkg, 'LICENSE'), path.join(dest, 'dagre.LICENSE'));
fs.copyFileSync(path.join(pkg, 'dist/dagre.min.js.LEGAL.txt'), path.join(dest, 'dagre.NOTICES'));
console.log('Vendored @dagrejs/dagre 3.1.1 with its license and notices.');
