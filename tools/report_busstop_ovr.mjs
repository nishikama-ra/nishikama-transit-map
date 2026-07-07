import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync('index.html', 'utf8');

function extractLiteralAfter(marker, openChar, closeChar) {
  const markerIndex = html.indexOf(marker);
  if (markerIndex < 0) throw new Error(`${marker} not found`);
  const start = html.indexOf(openChar, markerIndex);
  if (start < 0) throw new Error(`${marker} opening ${openChar} not found`);

  let depth = 0;
  let quote = null;
  let escaped = false;
  for (let i = start; i < html.length; i++) {
    const ch = html[i];
    if (quote) {
      if (escaped) escaped = false;
      else if (ch === '\\') escaped = true;
      else if (ch === quote) quote = null;
      continue;
    }
    if (ch === '"' || ch === "'" || ch === '`') {
      quote = ch;
      continue;
    }
    if (ch === openChar) depth++;
    if (ch === closeChar) {
      depth--;
      if (depth === 0) return html.slice(start, i + 1);
    }
  }
  throw new Error(`${marker} closing ${closeChar} not found`);
}

const context = vm.createContext({});
const stops = vm.runInContext(`(${extractLiteralAfter('const BUSSTOPS=', '[', ']')})`, context);
const rails = vm.runInContext(`(${extractLiteralAfter('const RAILSTOPS=', '[', ']')})`, context);
const busWithOvr = stops.filter(s => s.ovr && Object.keys(s.ovr).length);
const busWithoutOvr = stops.filter(s => !(s.ovr && Object.keys(s.ovr).length));

function hubKeys(s) {
  return s.ovr ? Object.keys(s.ovr).join('') : '';
}

const lines = [];
lines.push(`# BUSSTOPS ovr report`);
lines.push(``);
lines.push(`BUSSTOPS total: ${stops.length}`);
lines.push(`BUSSTOPS with ovr: ${busWithOvr.length}`);
lines.push(`BUSSTOPS without ovr: ${busWithoutOvr.length}`);
lines.push(`RAILSTOPS total: ${rails.length}`);
lines.push(``);
lines.push(`## bus stops with ovr`);
for (const s of busWithOvr) lines.push(`- ${s.n} (${s.d || ''}) hubs=${hubKeys(s)}`);
lines.push(``);
lines.push(`## bus stops without ovr`);
for (const s of busWithoutOvr) lines.push(`- ${s.n} (${s.d || ''})`);

fs.writeFileSync('busstop_ovr_report.md', lines.join('\n') + '\n', 'utf8');
console.log(lines.slice(0, 6).join('\n'));
