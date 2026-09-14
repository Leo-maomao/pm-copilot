import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const root = await mkdtemp(join(tmpdir(), 'pm-copilot-e2e-'));
const port = process.env.PM_COPILOT_E2E_PORT ?? '57392';
const directory = join(root, 'demo-project', 'demo-requirement');
await mkdir(directory, { recursive: true });
await writeFile(
  join(directory, 'requirement.md'),
  `---\nid: demo-requirement\ntitle: 演示需求\nstatus: defined\ncreatedAt: 2026-09-11T00:00:00.000Z\nupdatedAt: 2026-09-11T00:00:00.000Z\n---\n\n测试正文。\n`,
  'utf8',
);

let stopping = false;

async function stop() {
  if (stopping) return;
  stopping = true;
  await rm(root, { force: true, recursive: true });
}

process.on('SIGINT', () => void stop().then(() => process.exit(0)));
process.on('SIGTERM', () => void stop().then(() => process.exit(0)));
process.env.NODE_ENV = 'test';
process.env.PM_COPILOT_HOST = '127.0.0.1';
process.env.PM_COPILOT_LIBRARY_ROOT = root;
process.env.PM_COPILOT_PORT = port;
await import('../../services/local-server/dist/index.js');
