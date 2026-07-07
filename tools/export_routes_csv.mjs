import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync('index.html', 'utf8');

function extractObjectLiteral(name) {
  const marker = `const ${name}=`;
  const markerIndex = html.indexOf(marker);
  if (markerIndex < 0) throw new Error(`${name} not found`);
  const start = html.indexOf('{', markerIndex);
  if (start < 0) throw new Error(`${name} opening brace not found`);

  let depth = 0;
  let quote = null;
  let escaped = false;
  for (let i = start; i < html.length; i++) {
    const ch = html[i];
    if (quote) {
      if (escaped) {
        escaped = false;
      } else if (ch === '\\') {
        escaped = true;
      } else if (ch === quote) {
        quote = null;
      }
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') {
      quote = ch;
      continue;
    }
    if (ch === '{') depth++;
    if (ch === '}') {
      depth--;
      if (depth === 0) return html.slice(start, i + 1);
    }
  }
  throw new Error(`${name} closing brace not found`);
}

const context = vm.createContext({});
const R = vm.runInContext(`(${extractObjectLiteral('R')})`, context);
const REXTRA = vm.runInContext(`(${extractObjectLiteral('REXTRA')})`, context);

Object.entries(REXTRA).forEach(([id, extra]) => {
  if (!R[id]) R[id] = { n: id, op: '', hubs: [], d: 0, r: 0 };
  Object.assign(R[id], extra);
});

function csvCell(value) {
  const s = value == null ? '' : String(value);
  if (/[",\n\r]/.test(s)) return `"${s.replaceAll('"', '""')}"`;
  return s;
}

const rows = [
  ['id', '系統名', '日中毎時', '朝毎時', '1日本数', '始発', '終発', '直通拠点'],
];

for (const [id, route] of Object.entries(R)) {
  rows.push([
    id,
    route.n ?? id,
    route.d ?? '',
    route.r ?? '',
    route.t ?? '',
    route.fs ?? '',
    route.ls ?? '',
    Array.isArray(route.hubs) ? route.hubs.join('') : '',
  ]);
}

const csv = rows.map(row => row.map(csvCell).join(',')).join('\n') + '\n';
fs.writeFileSync('routes_data.csv', csv, 'utf8');
console.log(`Wrote routes_data.csv with ${rows.length - 1} routes.`);
