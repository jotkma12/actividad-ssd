import { rmSync } from 'node:fs';

export default async function globalTeardown() {
  if (process.env.E2E_DATA_DIRECTORY) {
    const testDataDirectory = process.env.E2E_DATA_DIRECTORY;
    process.once('exit', () => {
      rmSync(testDataDirectory, { recursive: true, force: true });
    });
  }
}
