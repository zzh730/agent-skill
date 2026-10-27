#!/usr/bin/env node
// Render Mermaid source files to themed SVG (and optional PNG) with Pele.
// Run through the `pele-render` wrapper, which installs pinned dependencies.
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { createRequire } from 'node:module';
import { basename, dirname, extname, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { parseArgs } from 'node:util';

const USAGE = `usage: pele-render [options] FILE.mmd...

Writes FILE.svg next to each input. The SVG has a solid background and
switches to a dark palette when the viewer prefers a dark color scheme.

options:
  --out-dir DIR   write outputs into DIR instead of next to the input
  --png           also write FILE.png (light) and FILE.dark.png for review
  --scale N       PNG pixel ratio (default 2)
  --check         parse and lay out only; write nothing
  --json          print a JSON summary instead of text`;

const FONT_STACK = '-apple-system, BlinkMacSystemFont, Segoe UI, Noto Sans, Helvetica, Arial, sans-serif';

// GitHub Primer colors, so diagrams sit naturally in PR descriptions.
const THEMES = {
  light: {
    'pele-bg': '#ffffff',
    'pele-fg': '#1f2328',
    'pele-muted': '#59636e',
    'pele-line': '#59636e',
    'pele-surface': '#f6f8fa',
    'pele-surface-alt': '#eaeef2',
    'pele-border': '#8c959f',
    'pele-accent': '#0969da',
    'pd-added': '#1a7f37',
    'pd-added-bg': '#dafbe1',
    'pd-added-text': '#1f2328',
    'pd-removed': '#cf222e',
    'pd-removed-bg': '#ffebe9',
    'pd-removed-text': '#59636e',
    'pd-changed': '#9a6700',
    'pd-changed-bg': '#fff8c5',
    'pd-changed-text': '#1f2328',
  },
  dark: {
    'pele-bg': '#0d1117',
    'pele-fg': '#f0f6fc',
    'pele-muted': '#9198a1',
    'pele-line': '#9198a1',
    'pele-surface': '#151b23',
    'pele-surface-alt': '#212830',
    'pele-border': '#656c76',
    'pele-accent': '#4493f8',
    'pd-added': '#3fb950',
    'pd-added-bg': '#12261e',
    'pd-added-text': '#f0f6fc',
    'pd-removed': '#f85149',
    'pd-removed-bg': '#25171c',
    'pd-removed-text': '#9198a1',
    'pd-changed': '#d29922',
    'pd-changed-bg': '#272115',
    'pd-changed-text': '#f0f6fc',
  },
};

// Pele rejects var() inside classDef, so the diff classes render with
// sentinel colors that are swapped for theme variables afterwards.
const DIFF_CLASSES = {
  added: { code: '1', extra: ',stroke-width:2px' },
  removed: { code: '2', extra: ',stroke-dasharray:6 4' },
  changed: { code: '3', extra: ',stroke-width:2px' },
};
const SENTINEL_ROLES = { 1: 'bg', 2: '', 3: 'text' };

function diffClassesUsed(source) {
  const names = Object.keys(DIFF_CLASSES).join('|');
  const used = new Set();
  const patterns = [
    new RegExp(`:::(${names})\\b`, 'g'),
    new RegExp(`^\\s*class\\s+[^\\n]*?\\b(${names})\\s*;?\\s*$`, 'gm'),
  ];
  for (const pattern of patterns) {
    for (const match of source.matchAll(pattern)) used.add(match[1]);
  }
  return used;
}

function withDiffClassDefs(source, used) {
  const names = Object.keys(DIFF_CLASSES).join('|');
  const stripped = source.replace(new RegExp(`^\\s*classDef\\s+(${names})\\b.*$\\n?`, 'gm'), '');
  const defs = [...used].map((name) => {
    const { code, extra } = DIFF_CLASSES[name];
    return `  classDef ${name} fill:#FE00${code}1,stroke:#FE00${code}2,color:#FE00${code}3${extra}`;
  });
  return `${stripped.replace(/\s*$/, '')}\n${defs.join('\n')}\n`;
}

function replaceSentinels(svg) {
  return svg.replace(/#FE00([1-3])([1-3])\b/gi, (_, code, role) => {
    const name = Object.keys(DIFF_CLASSES).find((key) => DIFF_CLASSES[key].code === code);
    const suffix = SENTINEL_ROLES[role] ? `-${SENTINEL_ROLES[role]}` : '';
    return `var(--pd-${name}${suffix})`;
  });
}

function themeStyle(selector) {
  const block = (tokens) => Object.entries(tokens).map(([key, value]) => `--${key}:${value}`).join(';');
  return (
    `<style>${selector}{${block(THEMES.light)}}` +
    `@media (prefers-color-scheme: dark){${selector}{${block(THEMES.dark)}}}</style>`
  );
}

function decorate(svg, id) {
  const open = svg.match(/^<svg\b[^>]*>/);
  if (!open) throw new Error('unexpected Pele output: no <svg> root');
  const viewBox = open[0].match(/viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"/);
  const [x, y, w, h] = viewBox ? viewBox.slice(1).map(Number) : [0, 0, 0, 0];
  const root = open[0].replace(/^<svg\b/, `<svg id="${id}"`);
  const background = `<rect class="pele-bg" x="${x}" y="${y}" width="${w}" height="${h}" rx="6" fill="var(--_bg)"/>`;
  return root + themeStyle(`#${id}`) + background + svg.slice(open[0].length);
}

// resvg does not support CSS custom properties or media queries, so the PNG
// gets every var() resolved against one palette.
function flatten(svg, themeName) {
  const tokens = { ...THEMES[themeName] };
  const root = svg.match(/^<svg\b[^>]*>/)[0];
  const style = root.match(/style="([^"]*)"/)?.[1] ?? '';
  const resolveValue = (value) => {
    let out = value;
    for (let i = 0; i < 10 && out.includes('var('); i += 1) {
      out = out.replace(/var\(--([\w-]+)(?:,([^()]*))?\)/g, (_, name, fallback) => tokens[name] ?? (fallback ?? '').trim());
    }
    return out;
  };
  const kept = [];
  for (const decl of style.split(';')) {
    const match = decl.match(/^\s*--([\w-]+)\s*:(.*)$/);
    if (match) tokens[match[1]] = resolveValue(match[2].trim());
    else if (decl.trim()) kept.push(decl.trim());
  }
  // resvg drops a style attribute that holds custom properties and misreads
  // the `font` shorthand, so the root style keeps only plain longhands.
  const rootStyle = kept
    .join(';')
    .replace(/\bfont:\s*([\d.]+px)\s+([^;]+)/g, 'font-size:$1;font-family:$2');
  const flat = svg
    .replace(/<style>[\s\S]*?<\/style>/, '')
    .replace(root, root.replace(/style="[^"]*"/, `style="${rootStyle}"`));
  return resolveValue(flat);
}

function loadDeps() {
  const depsDir = process.env.PELE_DIAGRAM_DEPS;
  if (!depsDir) throw new Error('PELE_DIAGRAM_DEPS is not set; run the pele-render wrapper');
  return createRequire(join(depsDir, 'package.json'));
}

function sanitizeId(name) {
  const slug = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return `pele-${slug || 'diagram'}`;
}

function warningsFor(result, source) {
  const warnings = [];
  if (result.width > 900) {
    warnings.push(`width ${Math.round(result.width)}px: a GitHub PR body is 780-880px wide, so the text shrinks; shorten labels, drop nodes, or split the diagram`);
  }
  const nodeCount = (result.svg.match(/class="pele-node\b/g) ?? []).length;
  if (nodeCount > 25) warnings.push(`${nodeCount} nodes: hard to read; show only the components that change`);
  const longLabel = source.match(/\[[^\]\n]{45,}\]/);
  if (longLabel) warnings.push(`long label ${longLabel[0].slice(0, 30)}...: use <br/> to wrap`);
  return warnings;
}

async function main() {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      'out-dir': { type: 'string' },
      png: { type: 'boolean', default: false },
      scale: { type: 'string', default: '2' },
      check: { type: 'boolean', default: false },
      json: { type: 'boolean', default: false },
      help: { type: 'boolean', short: 'h', default: false },
    },
  });
  if (values.help || positionals.length === 0) {
    console.log(USAGE);
    return values.help ? 0 : 2;
  }

  const require = loadDeps();
  const { render, PeleError } = await import(pathToFileURL(require.resolve('pele')).href);
  const summaries = [];
  let failed = false;

  for (const input of positionals) {
    const name = basename(input, extname(input));
    const outDir = resolve(values['out-dir'] ?? dirname(input));
    const original = readFileSync(input, 'utf8');
    const used = diffClassesUsed(original);
    const source = used.size > 0 ? withDiffClassDefs(original, used) : original;
    const id = sanitizeId(name);
    const summary = { input, ok: false };
    summaries.push(summary);

    let result;
    try {
      result = render(source, {
        responsive: false,
        autoDirection: false,
        padding: 16,
        fontFamily: FONT_STACK,
        idPrefix: `${id}-`,
      });
    } catch (error) {
      if (!(error instanceof PeleError)) throw error;
      failed = true;
      Object.assign(summary, { error: error.code, line: error.line, column: error.column, message: error.message });
      continue;
    }

    const svg = decorate(replaceSentinels(result.svg), id);
    Object.assign(summary, {
      ok: true,
      type: result.type,
      width: Math.round(result.width),
      height: Math.round(result.height),
      warnings: warningsFor(result, original),
    });
    if (values.check) continue;

    mkdirSync(outDir, { recursive: true });
    summary.svg = join(outDir, `${name}.svg`);
    writeFileSync(summary.svg, svg);

    if (values.png) {
      const { Resvg } = require('@resvg/resvg-js');
      const font = {
        loadSystemFonts: true,
        defaultFontFamily: process.platform === 'darwin' ? 'Helvetica' : 'DejaVu Sans',
      };
      for (const theme of ['light', 'dark']) {
        const png = new Resvg(flatten(svg, theme), {
          fitTo: { mode: 'zoom', value: Number(values.scale) },
          font,
        }).render().asPng();
        const key = theme === 'light' ? 'png' : 'darkPng';
        summary[key] = join(outDir, theme === 'light' ? `${name}.png` : `${name}.dark.png`);
        writeFileSync(summary[key], png);
      }
    }
  }

  if (values.json) {
    console.log(JSON.stringify(summaries, null, 2));
  } else {
    for (const s of summaries) {
      if (!s.ok) {
        console.log(`FAIL ${s.input}: ${s.error} at line ${s.line}, column ${s.column}\n${s.message}`);
        continue;
      }
      const outputs = [s.svg, s.png, s.darkPng].filter(Boolean).join(' ');
      console.log(`ok ${s.input} ${s.type} ${s.width}x${s.height}${outputs ? ` -> ${outputs}` : ''}`);
      for (const warning of s.warnings) console.log(`  warn: ${warning}`);
    }
  }
  return failed ? 1 : 0;
}

process.exitCode = await main();
