import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createHash } from 'node:crypto';
import { once } from 'node:events';
import {
  mkdir,
  mkdtemp,
  readFile,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
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

test('persists a local status change in the central library', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'requirement-manager-test-'));
  const directory = join(root, 'projects', 'demo', 'requirements', 'sample');
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'requirement.md'),
    '---\nid: sample\ntitle: Status test\nstatus: defined\ncreatedAt: 2026-09-10T10:00:00.000Z\nupdatedAt: 2026-09-10T10:00:00.000Z\nsummary: Verify centralized storage.\n---\n\nContent.',
    'utf8',
  );
  const serverPort = await port();
  const server = spawn(process.execPath, ['dist/index.js'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PM_COPILOT_HOST: '127.0.0.1',
      PM_COPILOT_PORT: String(serverPort),
      PM_COPILOT_LIBRARY_ROOT: root,
      PM_COPILOT_HISTORY_ROOT: join(root, 'empty'),
    },
    stdio: 'ignore',
  });
  t.after(async () => {
    server.kill();
    await once(server, 'exit');
    await rm(root, { force: true, recursive: true });
  });
  const baseUrl = `http://127.0.0.1:${serverPort}`;
  const lockedPayload = await (await index(`${baseUrl}/api/index`)).json();
  assert.equal(lockedPayload.canEdit, false);
  const unlock = await fetch(`${baseUrl}/api/edit-session`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ passcode: '9527' }),
  });
  assert.equal(unlock.status, 204);
  const cookie = unlock.headers.get('set-cookie');
  assert.ok(cookie);
  assert.match(cookie, /Max-Age=315360000/);
  await assert.doesNotReject(() =>
    readFile(join(root, '.manager', 'editor-sessions.json'), 'utf8').then(
      (content) => assert.match(content, /"sessions"/),
    ),
  );
  const payload = await (
    await fetch(`${baseUrl}/api/index`, { headers: { Cookie: cookie } })
  ).json();
  assert.equal(payload.canEdit, true);
  const projectResponse = await fetch(`${baseUrl}/api/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({ projectName: '全新项目' }),
  });
  assert.equal(projectResponse.status, 201);
  const projectPayload = await projectResponse.json();
  assert.equal(
    projectPayload.projects.some(
      (project) =>
        project.projectName === '全新项目' && project.requirements.length === 0,
    ),
    true,
  );
  const renamedProjectResponse = await fetch(
    `${baseUrl}/api/projects/${encodeURIComponent('全新项目')}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({ projectName: '已重命名项目' }),
    },
  );
  assert.equal(renamedProjectResponse.status, 200);
  assert.equal(
    (await renamedProjectResponse.json()).projects.some(
      (project) => project.projectName === '已重命名项目',
    ),
    true,
  );
  await assert.doesNotReject(() =>
    stat(join(root, 'projects', '已重命名项目')),
  );
  const deletedProjectResponse = await fetch(
    `${baseUrl}/api/projects/${encodeURIComponent('已重命名项目')}`,
    { method: 'DELETE', headers: { Cookie: cookie } },
  );
  assert.equal(deletedProjectResponse.status, 200);
  assert.equal(
    (await deletedProjectResponse.json()).projects.some(
      (project) => project.projectName === '已重命名项目',
    ),
    false,
  );
  await assert.rejects(() => stat(join(root, 'projects', '已重命名项目')));
  const createdResponse = await fetch(`${baseUrl}/api/requirements`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Cookie: cookie },
    body: JSON.stringify({ projectName: 'demo', title: 'Created requirement' }),
  });
  assert.equal(createdResponse.status, 201);
  const createdPayload = await createdResponse.json();
  assert.equal(createdPayload.created.projectName, 'demo');
  assert.equal(
    createdPayload.created.id.startsWith('created-requirement-'),
    true,
  );
  await assert.doesNotReject(() =>
    readFile(
      join(
        root,
        'projects',
        'demo',
        'requirements',
        createdPayload.created.id,
        'requirement.md',
      ),
      'utf8',
    ).then((content) => {
      assert.match(content, /^title: Created requirement$/m);
      assert.match(content, /^status: planning$/m);
      assert.match(content, /^summary: 待补充需求内容。$/m);
    }),
  );
  const key = payload.projects[0].requirements[0].assetKey;
  const response = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({ status: 'scheduled' }),
    },
  );
  assert.equal(response.status, 200);
  await assert.doesNotReject(() =>
    readFile(join(directory, 'requirement.md'), 'utf8').then((content) =>
      assert.match(content, /^status: scheduled$/m),
    ),
  );
  const visual = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}/visuals`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({
        data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL9xQAAAABJRU5ErkJggg==',
        filename: 'top-level.png',
        sectionTitle: '',
      }),
    },
  );
  assert.equal(visual.status, 200);
  const group = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}/visual-groups`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({ action: 'add', sectionIndex: 1 }),
    },
  );
  assert.equal(group.status, 200);
  const secondVisual = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}/visuals`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({
        data: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVQIHWP4z8DwHwAFgAI/ScL9xQAAAABJRU5ErkJggg==',
        filename: 'second-level.png',
        sectionTitle: '图示 1',
      }),
    },
  );
  assert.equal(secondVisual.status, 200);
  await assert.doesNotReject(() =>
    readFile(join(directory, 'requirement.md'), 'utf8').then((content) =>
      assert.match(content, /## 图示 1/),
    ),
  );
  const order = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}/visual-order`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({
        path: 'assets/top-level.png',
        targetPath: 'assets/second-level.png',
        targetSectionIndex: 1,
      }),
    },
  );
  assert.equal(order.status, 200, await order.text());
  await assert.doesNotReject(() =>
    readFile(join(directory, 'requirement.md'), 'utf8').then((content) =>
      assert.match(
        content,
        /## 图示 1\n{2,}!\[需求图示\]\(assets\/top-level\.png\)\n\n!\[需求图示\]\(assets\/second-level\.png\)/,
      ),
    ),
  );
  const orderAfter = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}/visual-order`,
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({
        insertAfter: true,
        path: 'assets/top-level.png',
        targetPath: 'assets/second-level.png',
        targetSectionIndex: 1,
      }),
    },
  );
  assert.equal(orderAfter.status, 200, await orderAfter.text());
  await assert.doesNotReject(() =>
    readFile(join(directory, 'requirement.md'), 'utf8').then((content) =>
      assert.match(
        content,
        /## 图示 1\n{2,}!\[需求图示\]\(assets\/second-level\.png\)\n\n!\[需求图示\]\(assets\/top-level\.png\)/,
      ),
    ),
  );
});

test('reconciles historical requirement dates from the version record', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'requirement-manager-history-'));
  const historyRoot = join(root, 'history');
  const sourceDirectory = join(
    historyRoot,
    'legacy-project',
    'pm-copilot-outputs',
    'sample-history',
  );
  const sourceMarkdown = join(sourceDirectory, 'prd.md');
  const source = `# 示例历史需求 - 2026-06-02

### 2. 版本记录

| 版本 | 日期 | 变更内容 |
| --- | --- | --- |
| v0.1 | 2026-06-01 | 首次创建 |
| v0.2 | 2026-06-03 | 更新说明 |

## 五、需求详情

历史需求正文。`;
  await mkdir(sourceDirectory, { recursive: true });
  await writeFile(sourceMarkdown, source, 'utf8');

  const fingerprint = createHash('sha256').update(sourceMarkdown).digest('hex');
  const id = `history-sample-history-1-${fingerprint.slice(0, 8)}`;
  const directory = join(
    root,
    'projects',
    'legacy-project',
    'requirements',
    id,
  );
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'requirement.md'),
    `---
id: ${id}
title: 已迁移历史需求
status: scheduled
createdAt: 2026-09-10T10:00:00.000Z
updatedAt: 2026-09-10T10:00:00.000Z
summary: 保留本机修改。
---

本机正文。`,
    'utf8',
  );

  const serverPort = await port();
  const server = spawn(process.execPath, ['dist/index.js'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      PM_COPILOT_HOST: '127.0.0.1',
      PM_COPILOT_PORT: String(serverPort),
      PM_COPILOT_LIBRARY_ROOT: root,
      PM_COPILOT_HISTORY_ROOT: historyRoot,
    },
    stdio: 'ignore',
  });
  t.after(async () => {
    server.kill();
    await once(server, 'exit');
    await rm(root, { force: true, recursive: true });
  });

  const payload = await (
    await index(`http://127.0.0.1:${serverPort}/api/index`)
  ).json();
  const document = payload.projects[0].requirements[0].document;
  assert.equal(document.createdAt, '2026-06-01T00:00:00.000Z');
  assert.equal(document.updatedAt, '2026-06-03T00:00:00.000Z');
  assert.equal(document.status, 'scheduled');
  await assert.doesNotReject(() =>
    readFile(join(directory, 'requirement.md'), 'utf8').then((content) => {
      assert.match(content, /^title: 已迁移历史需求$/m);
      assert.match(content, /^summary: 保留本机修改。$/m);
    }),
  );
});
