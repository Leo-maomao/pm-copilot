import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
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
  const directory = join(root, 'demo', 'sample');
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'requirement.md'),
    '---\nid: sample\ntitle: Status test\nstatus: defined\ncreatedAt: 2026-09-10T10:00:00.000Z\nupdatedAt: 2026-09-10T10:00:00.000Z\n---\n\nContent.',
    'utf8',
  );
  await mkdir(join(root, '恢复后的项目'), { recursive: true });
  await mkdir(join(root, '.manager'), { recursive: true });
  await writeFile(
    join(root, '.manager', 'project-rename.json'),
    JSON.stringify({
      from: '原项目',
      origins: { 恢复后的项目: '原项目' },
      to: '恢复后的项目',
    }),
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
  const lockedPayload = await (await index(`${baseUrl}/api/index`)).json();
  assert.equal(lockedPayload.canEdit, false);
  await assert.doesNotReject(() =>
    readFile(join(root, '.manager', 'project-origins.json'), 'utf8').then(
      (content) => assert.match(content, /"恢复后的项目": "原项目"/),
    ),
  );
  await assert.rejects(() =>
    stat(join(root, '.manager', 'project-rename.json')),
  );
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
  await assert.rejects(() =>
    stat(join(root, '.manager', 'project-rename.json')),
  );
  const payload = await (
    await fetch(`${baseUrl}/api/index`, { headers: { Cookie: cookie } })
  ).json();
  assert.equal(payload.canEdit, true);
  assert.equal(
    payload.projects.some((project) => project.projectName === '.manager'),
    false,
  );
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
  await assert.doesNotReject(() => stat(join(root, '已重命名项目')));
  await assert.doesNotReject(() =>
    readFile(join(root, '.manager', 'project-origins.json'), 'utf8').then(
      (content) => assert.match(content, /"已重命名项目": "全新项目"/),
    ),
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
  await assert.rejects(() => stat(join(root, '已重命名项目')));
  await assert.doesNotReject(() =>
    readFile(join(root, '.manager', 'project-origins.json'), 'utf8').then(
      (content) => assert.doesNotMatch(content, /已重命名项目/),
    ),
  );
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
      join(root, 'demo', createdPayload.created.id, 'requirement.md'),
      'utf8',
    ).then((content) => {
      assert.match(content, /^title: "Created requirement"$/m);
      assert.match(content, /^status: "planning"$/m);
      assert.doesNotMatch(content, /^summary:/m);
    }),
  );
  const deletedRequirementResponse = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(`demo:${createdPayload.created.id}`)}`,
    { method: 'DELETE', headers: { Cookie: cookie } },
  );
  assert.equal(deletedRequirementResponse.status, 200);
  assert.equal(
    (await deletedRequirementResponse.json()).projects
      .find((project) => project.projectName === 'demo')
      .requirements.some(
        (requirement) => requirement.document.id === createdPayload.created.id,
      ),
    false,
  );
  await assert.rejects(() =>
    stat(join(root, 'demo', createdPayload.created.id)),
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
  const statusPayload = await response.json();
  const statusRequirement = statusPayload.projects
    .flatMap((project) => project.requirements)
    .find((requirement) => requirement.assetKey === key);
  assert.equal(
    statusRequirement.document.updatedAt,
    payload.projects[0].requirements[0].document.updatedAt,
  );
  await assert.doesNotReject(() =>
    readFile(join(directory, 'requirement.md'), 'utf8').then((content) => {
      assert.match(content, /^status: "scheduled"$/m);
      assert.match(content, /^updatedAt: "2026-09-10T10:00:00.000Z"$/m);
    }),
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
  const renamedVisual = await fetch(
    `${baseUrl}/api/requirements/${encodeURIComponent(key)}/visuals`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', Cookie: cookie },
      body: JSON.stringify({
        alt: '节点搜索清单',
        path: 'assets/top-level.png',
      }),
    },
  );
  assert.equal(renamedVisual.status, 200, await renamedVisual.text());
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
        /## 图示 1\n{2,}!\[节点搜索清单\]\(assets\/top-level\.png\)\n\n!\[second-level\]\(assets\/second-level\.png\)/,
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
        /## 图示 1\n{2,}!\[second-level\]\(assets\/second-level\.png\)\n\n!\[节点搜索清单\]\(assets\/top-level\.png\)/,
      ),
    ),
  );
});

test('recovers an interrupted project deletion before indexing', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'requirement-manager-delete-'));
  await mkdir(join(root, '.manager'), { recursive: true });
  await writeFile(
    join(root, '.manager', 'project-origins.json'),
    JSON.stringify({ origins: { 已删除项目: 'source-project' } }),
  );
  await writeFile(
    join(root, '.manager', 'project-delete.json'),
    JSON.stringify({ origins: {}, projectName: '已删除项目' }),
  );
  const serverPort = await port();
  const server = spawn(process.execPath, ['dist/index.js'], {
    cwd: process.cwd(),
    env: {
      ...process.env,
      NODE_ENV: 'test',
      PM_COPILOT_HOST: '127.0.0.1',
      PM_COPILOT_LIBRARY_ROOT: root,
      PM_COPILOT_PORT: String(serverPort),
    },
    stdio: 'ignore',
  });
  t.after(async () => {
    server.kill();
    await once(server, 'exit');
    await rm(root, { force: true, recursive: true });
  });
  await index(`http://127.0.0.1:${serverPort}/api/index`);
  await assert.doesNotReject(() =>
    readFile(join(root, '.manager', 'project-origins.json'), 'utf8').then(
      (content) => assert.deepEqual(JSON.parse(content), { origins: {} }),
    ),
  );
  await assert.rejects(() =>
    stat(join(root, '.manager', 'project-delete.json')),
  );
});
