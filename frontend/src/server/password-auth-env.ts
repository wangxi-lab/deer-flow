import { existsSync } from "node:fs";
import { resolve } from "node:path";

import { config } from "dotenv";

let loaded = false;

export function loadPasswordAuthEnv() {
  if (loaded) {
    return;
  }
  loaded = true;

  const cwd = process.cwd();

  for (const envPath of [
    resolve(cwd, "..", ".env"),
    resolve(cwd, ".env"),
    resolve(cwd, "frontend", ".env.local"),
    resolve(cwd, "frontend", ".env"),
    resolve(cwd, ".env.local"),
  ]) {
    if (existsSync(envPath)) {
      config({ path: envPath, override: false });
    }
  }
}
