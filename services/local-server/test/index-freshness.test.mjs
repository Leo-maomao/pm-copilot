import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdir, mkdtemp, rm, writeFile } from 'node:fs/promises';
import { createServer as createNetServer } from 'node:net';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

async function port() {
  const server = createNetServer();
  server.listen(0, '127.0.0.1');
  await once(server, 'listening');
  const address = server.address();
  server.close();
  await once(server, 'close');
  if (!address || typeof address === 'string') throw new Error('No port.');
  return address.port;
}
async function index(url) {
  for (let attempt = 0; attempt < 40; attempt += 1) {
    try {
      const response = await fetch(url);
      if (response.ok) return response;
    } catch {
      /* retry */
    }
    await new Promise((resolve) => setTimeout(resolve, 25));
  }
  throw new Error('Server did not start.');
}
function requirementMarkdown(id, title, body) {
  return `---\nid: ${id}\ntitle: ${title}\nstatus: defined\ncreatedAt: 2026-09-10T10:00:00.000Z\nupdatedAt: 2026-09-10T10:00:00.000Z\n---\n\n${body}\n`;
}
function readRequirement(payload, id) {
  return payload.projects
    .flatMap((project) => project.requirements)
    .find((requirement) => requirement.document.id === id);
}

test('serves requirement files that were written outside the server', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'requirement-manager-fresh-'));
  const directory = join(root, 'demo-project', 'existing');
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'requirement.md'),
    requirementMarkdown('existing', '已有需求', '### 一、原内容\n1. 旧正文。'),
    'utf8',
  );
  const serverPort = await port();
  const server = spawn(process.execPath, ['dist/index.js'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      NODE_ENV: 'test',
      PM_COPILOT_HOST: '127.0.0.1',
      PM_COPILOT_PORT: String(serverPort),
      PM_COPILOT_LIBRARY_ROOT: root,
    },
    stdio: 'ignore',
  });
  t.after(async () => {
    server.kill();
    await once(server, 'exit');
    await rm(root, { force: true, recursive: true });
  });
  const baseUrl = `http://127.0.0.1:${serverPort}`;

  const baseline = await (await index(`${baseUrl}/api/index`)).json();
  assert.equal(readRequirement(baseline, 'existing') !== undefined, true);

  // The plugin MCP writes straight to disk; no server call is involved.
  const written = join(root, 'demo-project', 'added-out-of-band');
  await mkdir(written, { recursive: true });
  await writeFile(
    join(written, 'requirement.md'),
    requirementMarkdown(
      'added-out-of-band',
      '外部写入需求',
      '### 一、外部\n1. 插件写入。',
    ),
    'utf8',
  );
  const afterWrite = await (await index(`${baseUrl}/api/index`)).json();
  assert.equal(
    readRequirement(afterWrite, 'added-out-of-band')?.document.title,
    '外部写入需求',
  );

  // Editing an existing file on disk has to show up as well.
  await writeFile(
    join(directory, 'requirement.md'),
    requirementMarkdown('existing', '已有需求', '### 一、改过\n1. 新正文。'),
    'utf8',
  );
  const afterEdit = await (await index(`${baseUrl}/api/index`)).json();
  assert.match(
    readRequirement(afterEdit, 'existing').document.sections[0].description,
    /新正文/,
  );

  // A removed directory disappears from the index.
  await rm(written, { force: true, recursive: true });
  const afterDelete = await (await index(`${baseUrl}/api/index`)).json();
  assert.equal(readRequirement(afterDelete, 'added-out-of-band'), undefined);
});
