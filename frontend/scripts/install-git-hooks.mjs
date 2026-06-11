#!/usr/bin/env node
import { chmodSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { execSync } from "node:child_process";

const SCRIPT_DIR = dirname(fileURLToPath(import.meta.url));
const FRONTEND_ROOT = join(SCRIPT_DIR, "..");

const HOOK_SCRIPT = `#!/bin/sh
set -e
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT/frontend" || exit 1
node scripts/write-build-info.mjs --prefer-edit-msg
git add "$ROOT/frontend/src/generated/build-info.ts"
`;

function getRepoRoot() {
  try {
    return execSync("git rev-parse --show-toplevel", {
      cwd: FRONTEND_ROOT,
      encoding: "utf8",
    }).trim();
  } catch {
    return null;
  }
}

function main() {
  if (process.env.VERCEL || process.env.CI) {
    return;
  }

  const repoRoot = getRepoRoot();
  if (!repoRoot) {
    console.warn("install-git-hooks: not a git repository, skipping");
    return;
  }

  const hookPath = join(repoRoot, ".git", "hooks", "pre-commit");
  writeFileSync(hookPath, HOOK_SCRIPT, "utf8");
  try {
    chmodSync(hookPath, 0o755);
  } catch {
    /* Windows may not support chmod on all filesystems */
  }

  console.log(`Installed pre-commit hook: ${hookPath}`);
}

main();
