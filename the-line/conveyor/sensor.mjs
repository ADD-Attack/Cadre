#!/usr/bin/env node
// The Line's completion sensor.
// Fetches a shipped artifact's live URL, checks that every expected
// marker is present in the response, and writes a receipt JSON.
// The sensor — not any agent — declares completion.
//
// Usage:
//   node conveyor/sensor.mjs --ticket 001 --url https://example.github.io/the-line/products/weather/ \
//     --expect "Hour by Hour" --expect "data-generated-at" --out receipts/001.json [--attempt 2]
//
// Exit code 0 = PASS (receipt written with status "pass"),
// 1 = FAIL (receipt still written, status "fail", with the reasons).

import { writeFileSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";

function parseArgs(argv) {
  const args = { expect: [], attempt: 1 };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === "--ticket") args.ticket = argv[++i];
    else if (a === "--url") args.url = argv[++i];
    else if (a === "--expect") args.expect.push(argv[++i]);
    else if (a === "--out") args.out = argv[++i];
    else if (a === "--attempt") args.attempt = Number(argv[++i]);
  }
  return args;
}

const args = parseArgs(process.argv);
if (!args.ticket || !args.url || !args.out) {
  console.error("required: --ticket <id> --url <url> --out <receipt-path>");
  process.exit(2);
}

const checkedAt = new Date().toISOString();
const checks = [];
let httpStatus = null;
let body = "";

try {
  const res = await fetch(args.url, { redirect: "follow" });
  httpStatus = res.status;
  body = await res.text();
  checks.push({ check: "http_200", pass: res.status === 200, detail: `status ${res.status}` });
} catch (err) {
  checks.push({ check: "http_200", pass: false, detail: `fetch failed: ${err.message}` });
}

for (const marker of args.expect) {
  const found = body.includes(marker);
  checks.push({ check: `marker:${marker}`, pass: found, detail: found ? "present in live body" : "NOT found in live body" });
}

const pass = checks.every((c) => c.pass);
const receipt = {
  ticket: args.ticket,
  url: args.url,
  attempt: args.attempt,
  status: pass ? "pass" : "fail",
  checked_at: checkedAt,
  http_status: httpStatus,
  bytes: body.length,
  checks,
};

mkdirSync(dirname(args.out), { recursive: true });
writeFileSync(args.out, JSON.stringify(receipt, null, 2) + "\n");
console.log(JSON.stringify(receipt, null, 2));
process.exit(pass ? 0 : 1);
