#!/usr/bin/env node
/**
 * @title Pre-flight Check Runner
 * @description Run lint, type:check, format:check, test, and build in sequence with a summary
 * @author ropean, Claude Sonnet (Anthropic)
 *
 * Runs all pre-flight checks in sequence; prints one summary line each.
 * Detailed output is captured silently; failures dump captured output afterward.
 * Exit code = number of failed checks (0 == clean).
 *
 * @example
 * node scripts/check.mjs
 *
 * @requires pnpm
 */

import { spawn } from 'node:child_process';

const CHECKS = [
  { name: 'lint', cmd: 'pnpm', args: ['lint'] },
  { name: 'type:check', cmd: 'pnpm', args: ['type:check'] },
  { name: 'format:check', cmd: 'pnpm', args: ['format:check'] },
  { name: 'test', cmd: 'pnpm', args: ['test'] },
  { name: 'build', cmd: 'pnpm', args: ['build'] },
];

const C = {
  reset: '\x1b[0m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  cyan: '\x1b[36m',
  bold: '\x1b[1m',
};

function fmtMs(ms) {
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function runOne({ name, cmd, args }) {
  return new Promise((resolve) => {
    const start = Date.now();
    const isWin = process.platform === 'win32';
    const child = spawn(isWin ? [cmd, ...args].join(' ') : cmd, isWin ? [] : args, {
      stdio: ['ignore', 'pipe', 'pipe'],
      env: process.env,
      shell: isWin,
    });
    let out = '';
    let err = '';
    child.stdout.on('data', (d) => {
      out += d.toString();
    });
    child.stderr.on('data', (d) => {
      err += d.toString();
    });
    child.on('close', (code) => {
      resolve({ name, code, ms: Date.now() - start, out, err });
    });
    child.on('error', (e) => {
      resolve({ name, code: -1, ms: Date.now() - start, out, err: err + '\n' + e.message });
    });
  });
}

function statusBadge(code) {
  return code === 0 ? `${C.green}PASS${C.reset}` : `${C.red}FAIL${C.reset}`;
}

const PAD = Math.max(...CHECKS.map((c) => c.name.length));

console.log(`${C.bold}Running ${CHECKS.length} checks…${C.reset}\n`);

const results = [];
for (const check of CHECKS) {
  process.stdout.write(
    `  ${C.dim}…${C.reset} ${check.name.padEnd(PAD)}  ${C.dim}running${C.reset}`,
  );
  const r = await runOne(check);
  results.push(r);
  // Overwrite progress line
  process.stdout.write(
    `\r  ${statusBadge(r.code)} ${r.name.padEnd(PAD)}  ${C.dim}${fmtMs(r.ms)}${C.reset}\n`,
  );
}

const failed = results.filter((r) => r.code !== 0);

console.log(`\n${C.bold}Summary${C.reset}`);
console.log(
  `  ${results.length - failed.length}/${results.length} passed  ${C.dim}(${fmtMs(results.reduce((s, r) => s + r.ms, 0))} total)${C.reset}`,
);

if (failed.length === 0) {
  console.log(`\n${C.green}${C.bold}All checks passed.${C.reset}`);
}

process.exit(failed.length);
