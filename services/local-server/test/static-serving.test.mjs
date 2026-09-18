import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { mkdtemp, rm } from 'node:fs/promises';
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
async function ready(url) {
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

test('serves the manager page for shared requirement links', async (t) => {
  const root = await mkdtemp(join(tmpdir(), 'requirement-manager-routes-'));
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
  await ready(`${baseUrl}/api/index`);

  // A link has no file behind it: the manager page loads and resolves it.
  const link = await fetch(`${baseUrl}/r/demo-project/some-requirement`);
  assert.equal(link.status, 200);
  assert.match(link.headers.get('content-type') ?? '', /text\/html/);
  assert.equal((await link.text()).length > 0, true);

  // A stale bundle must stay a 404 rather than turn into HTML.
  const asset = await fetch(`${baseUrl}/assets/missing-bundle.js`);
  assert.equal(asset.status, 404);

  // Unknown API paths must not answer with the page either.
  const api = await fetch(`${baseUrl}/api/unknown`);
  assert.equal(api.status, 404);

  // Shared links are built from an address another machine can open.
  const payload = await (await fetch(`${baseUrl}/api/index`)).json();
  assert.equal(Array.isArray(payload.lanOrigins), true);
  for (const origin of payload.lanOrigins) {
    assert.match(origin, /^http:\/\/\d+\.\d+\.\d+\.\d+:\d+$/);
    assert.equal(origin.endsWith(`:${serverPort}`), true);
    assert.equal(origin.startsWith('http://127.'), false);
    // Link-local, and the RFC 2544 block a VPN client parks its tunnel on.
    assert.equal(origin.startsWith('http://169.254.'), false);
    assert.equal(origin.startsWith('http://198.18.'), false);
    assert.equal(origin.startsWith('http://198.19.'), false);
  }
});
