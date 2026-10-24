import { rmSync } from 'node:fs';

export default async function globalTeardown() {
  if (process.env.E2E_DATA_DIRECTORY) {
    rmSync(process.env.E2E_DATA_DIRECTORY, { recursive: true, force: true });
  }
}
