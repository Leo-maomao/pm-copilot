import assert from 'node:assert/strict';
import { execFileSync, spawn } from 'node:child_process';
import { once } from 'node:events';
import {
  chmod,
  mkdir,
  mkdtemp,
  readFile,
  rm,
  writeFile,
} from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import test from 'node:test';

const repositoryRoot = process.cwd();
const script = join(
  repositoryRoot,
  'plugins',
  'pm-copilot',
  'scripts',
  'pm-copilot-mcp.mjs',
);

function startMcp(configPath) {
  const child = spawn(process.execPath, [script], {
    cwd: repositoryRoot,
    env: { ...process.env, PM_COPILOT_CONFIG_PATH: configPath },
    stdio: ['pipe', 'pipe', 'pipe'],
  });
  const pending = [];
  let buffer = '';
  child.stdout.setEncoding('utf8');
  child.stdout.on('data', (chunk) => {
    buffer += chunk;
    const lines = buffer.split('\n');
    buffer = lines.pop() ?? '';
    for (const line of lines) {
      const next = pending.shift();
      if (next) next(JSON.parse(line));
    }
  });
  return {
    async call(name, args) {
      const response = new Promise((resolve) => pending.push(resolve));
      child.stdin.write(
        `${JSON.stringify({
          jsonrpc: '2.0',
          id: Math.random(),
          method: 'tools/call',
          params: { name, arguments: args },
        })}\n`,
      );
      const message = await response;
      return JSON.parse(message.result.content[0].text);
    },
    async stop() {
      child.stdin.end();
      await once(child, 'exit');
    },
  };
}

async function fixture(t) {
  const root = await mkdtemp(join(tmpdir(), 'pm-copilot-mcp-'));
  const projectRoot = join(root, 'SeaFlow');
  const libraryRoot = join(root, 'library');
  const configPath = join(root, 'config.json');
  await mkdir(projectRoot, { recursive: true });
  execFileSync('git', ['init'], { cwd: projectRoot, stdio: 'ignore' });
  execFileSync(
    'git',
    ['remote', 'add', 'origin', 'git@github.com:team/SeaFlow.git'],
    {
      cwd: projectRoot,
      stdio: 'ignore',
    },
  );
  await writeFile(configPath, JSON.stringify({ repositoryRoot: libraryRoot }));
  await mkdir(join(libraryRoot, 'packages', 'core', 'dist'), {
    recursive: true,
  });
  const sourceCore = join(
    repositoryRoot,
    'packages',
    'core',
    'dist',
    'index.js',
  );
  await writeFile(
    join(libraryRoot, 'packages', 'core', 'dist', 'index.js'),
    await readFile(sourceCore),
  );
  t.after(() => rm(root, { force: true, recursive: true }));
  return { configPath, libraryRoot, projectRoot };
}

function section(title, description, imagePaths = []) {
  return { description, image_paths: imagePaths, title };
}

test('creates a pure text requirement for the current Git project', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  const created = await mcp.call('create_text_requirement', {
    project_root: projectRoot,
    requirement_id: 'fix-empty-result',
    title: '修复空结果提示',
    sections: [section('', '当搜索没有结果时，页面显示空状态提示。')],
  });
  assert.deepEqual(created.requirement, {
    id: 'fix-empty-result',
    project_key: 'SeaFlow',
    status: 'defined',
    title: '修复空结果提示',
  });
  const markdown = await readFile(
    join(
      libraryRoot,
      'requirements',
      'SeaFlow',
      'fix-empty-result',
      'requirement.md',
    ),
    'utf8',
  );
  assert.match(markdown, /^status: "defined"$/m);
  assert.doesNotMatch(markdown, /!\[/);
});

test('completes a manager-created requirement while preserving and assigning every image', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  const directory = join(
    libraryRoot,
    'requirements',
    'SeaFlow',
    'publish-flow',
  );
  await mkdir(join(directory, 'assets'), { recursive: true });
  await writeFile(join(directory, 'assets', 'editor.png'), 'image');
  await writeFile(join(directory, 'assets', 'preview.png'), 'image');
  await writeFile(
    join(directory, 'requirement.md'),
    `---\nid: publish-flow\ntitle: 发布流程\nstatus: planning\ncreatedAt: 2026-09-10T00:00:00.000Z\nupdatedAt: 2026-09-10T00:00:00.000Z\n---\n\n![编辑器](assets/editor.png)\n\n![预览](assets/preview.png)\n`,
  );
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  const result = await mcp.call('complete_implemented_requirement', {
    project_root: projectRoot,
    requirement_id: 'publish-flow',
    title: '发布前预览',
    sections: [
      section('编辑', '用户在编辑器中完成内容配置。', ['assets/editor.png']),
      section('预览', '用户在发布前检查最终效果。', ['assets/preview.png']),
    ],
  });
  assert.equal(result.requirement.status, 'defined');
  const markdown = await readFile(join(directory, 'requirement.md'), 'utf8');
  assert.match(markdown, /^status: "defined"$/m);
  assert.match(markdown, /## 编辑[\s\S]*assets\/editor\.png/);
  assert.match(markdown, /## 预览[\s\S]*assets\/preview\.png/);
  const missingAssignment = await mcp.call('complete_implemented_requirement', {
    project_root: projectRoot,
    requirement_id: 'publish-flow',
    title: '发布前预览',
    sections: [
      section('编辑', '用户在编辑器中完成内容配置。', ['assets/editor.png']),
    ],
  });
  assert.equal(missingAssignment.ok, false);
  assert.match(missingAssignment.error, /Every existing image path/);
});

test('updates content without changing the status, creation time, or image paths', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  const directory = join(libraryRoot, 'requirements', 'SeaFlow', 'published');
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'requirement.md'),
    `---\nid: published\ntitle: 已有需求\nstatus: scheduled\ncreatedAt: 2026-09-01T00:00:00.000Z\nupdatedAt: 2026-09-02T00:00:00.000Z\n---\n\n## 原内容\n\n![原图](assets/original.png)\n\n旧正文。\n`,
  );
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  const result = await mcp.call('update_requirement_content', {
    project_root: projectRoot,
    target_title: '已有需求',
    title: '更新后的需求',
    sections: [section('新内容', '新正文。', ['assets/original.png'])],
  });
  assert.equal(result.requirement.status, 'scheduled');
  const markdown = await readFile(join(directory, 'requirement.md'), 'utf8');
  assert.match(markdown, /^createdAt: "2026-09-01T00:00:00.000Z"$/m);
  assert.match(markdown, /^status: "scheduled"$/m);
  assert.match(markdown, /assets\/original\.png/);
  assert.doesNotMatch(markdown, /^updatedAt: "2026-09-02T00:00:00.000Z"$/m);
});

test('rejects missing configuration and duplicate requirement targets', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  const missing = startMcp(join(libraryRoot, 'missing.json'));
  t.after(() => missing.stop());
  const configurationError = await missing.call(
    'inspect_project_requirements',
    {
      project_root: projectRoot,
    },
  );
  assert.equal(configurationError.ok, false);
  assert.match(configurationError.error, /not configured/);

  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  const args = {
    project_root: projectRoot,
    requirement_id: 'same-id',
    title: '同名需求',
    sections: [section('', '正文。')],
  };
  assert.equal((await mcp.call('create_text_requirement', args)).ok, true);
  const duplicateId = await mcp.call('create_text_requirement', {
    ...args,
    title: '不同标题',
  });
  assert.match(duplicateId.error, /id already exists/);
  const duplicateTitle = await mcp.call('create_text_requirement', {
    ...args,
    requirement_id: 'other-id',
  });
  assert.match(duplicateTitle.error, /title already exists/);
});

test('configures the local repository through MCP', async (t) => {
  const { libraryRoot } = await fixture(t);
  const mcp = startMcp(join(libraryRoot, 'missing.json'));
  t.after(() => mcp.stop());
  const result = await mcp.call('configure_pm_copilot', {
    repository_root: libraryRoot,
  });
  assert.equal(result.ok, true);
  assert.deepEqual(
    JSON.parse(await readFile(join(libraryRoot, 'missing.json'))),
    {
      repositoryRoot: libraryRoot,
    },
  );
});

test('uses the manager origin mapping after a project directory is renamed', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  await mkdir(join(libraryRoot, 'requirements', '已改名项目'), {
    recursive: true,
  });
  await mkdir(join(libraryRoot, 'requirements', '.manager'), {
    recursive: true,
  });
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    JSON.stringify({ origins: { 已改名项目: 'SeaFlow' } }),
  );
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  const result = await mcp.call('create_text_requirement', {
    project_root: projectRoot,
    requirement_id: 'mapped-project',
    title: '改名项目需求',
    sections: [section('', '正文。')],
  });
  assert.equal(result.requirement.project_key, 'SeaFlow');
  await assert.doesNotReject(() =>
    readFile(
      join(
        libraryRoot,
        'requirements',
        '已改名项目',
        'mapped-project',
        'requirement.md',
      ),
      'utf8',
    ),
  );
});

test('rejects a title collision introduced by a content update', async (t) => {
  const { configPath, projectRoot } = await fixture(t);
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  for (const [id, title] of [
    ['first-requirement', '第一条需求'],
    ['second-requirement', '第二条需求'],
  ]) {
    assert.equal(
      (
        await mcp.call('create_text_requirement', {
          project_root: projectRoot,
          requirement_id: id,
          title,
          sections: [section('', '正文。')],
        })
      ).ok,
      true,
    );
  }
  const result = await mcp.call('update_requirement_content', {
    project_root: projectRoot,
    requirement_id: 'first-requirement',
    title: '第二条需求',
    sections: [section('', '更新正文。')],
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /title already exists/);
});

test('rejects invalid origin mappings and unsupported content structures', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  await mkdir(join(libraryRoot, 'requirements', '.manager'), {
    recursive: true,
  });
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    '{',
  );
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-delete.json'),
    '{}',
  );
  const pendingTransaction = await mcp.call('inspect_project_requirements', {
    project_root: projectRoot,
  });
  assert.equal(pendingTransaction.ok, false);
  assert.match(pendingTransaction.error, /transaction recovery is pending/);
  await rm(
    join(libraryRoot, 'requirements', '.manager', 'project-delete.json'),
  );
  const invalidMapping = await mcp.call('inspect_project_requirements', {
    project_root: projectRoot,
  });
  assert.equal(invalidMapping.ok, false);
  assert.match(invalidMapping.error, /mapping is invalid/);

  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    JSON.stringify({ origins: {} }),
  );
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    JSON.stringify({ origins: { '../outside': 'SeaFlow' } }),
  );
  const escapedMapping = await mcp.call('inspect_project_requirements', {
    project_root: projectRoot,
  });
  assert.equal(escapedMapping.ok, false);
  assert.match(escapedMapping.error, /mapping is invalid/);
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    JSON.stringify({ origins: { '.manager': 'SeaFlow' } }),
  );
  const metadataMapping = await mcp.call('inspect_project_requirements', {
    project_root: projectRoot,
  });
  assert.equal(metadataMapping.ok, false);
  assert.match(metadataMapping.error, /mapping is invalid/);
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    JSON.stringify({ origins: { renamed: 'SeaFlow' } }),
  );
  const missingDirectory = await mcp.call('inspect_project_requirements', {
    project_root: projectRoot,
  });
  assert.equal(missingDirectory.ok, false);
  assert.match(missingDirectory.error, /Mapped project directory is missing/);
  await writeFile(
    join(libraryRoot, 'requirements', '.manager', 'project-origins.json'),
    JSON.stringify({ origins: {} }),
  );
  const withImage = await mcp.call('create_text_requirement', {
    project_root: projectRoot,
    requirement_id: 'invalid-image',
    title: '不允许的图片引用',
    sections: [section('', '正文。', ['assets/missing.png'])],
  });
  assert.match(withImage.error, /must not contain image paths/);
  const withHeading = await mcp.call('create_text_requirement', {
    project_root: projectRoot,
    requirement_id: 'invalid-heading',
    title: '不允许的层级',
    sections: [section('', '正文。\n\n## 额外层级')],
  });
  assert.match(withHeading.error, /must not contain Markdown headings/);
});

test('does not overwrite a directory whose requirement id is malformed', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  const directory = join(libraryRoot, 'requirements', 'SeaFlow', 'reserved-id');
  await mkdir(directory, { recursive: true });
  await writeFile(
    join(directory, 'requirement.md'),
    `---\nid: another-id\ntitle: 异常目录\nstatus: defined\ncreatedAt: 2026-09-11T00:00:00.000Z\nupdatedAt: 2026-09-11T00:00:00.000Z\n---\n\n正文。\n`,
  );
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  const result = await mcp.call('create_text_requirement', {
    project_root: projectRoot,
    requirement_id: 'reserved-id',
    title: '新需求',
    sections: [section('', '正文。')],
  });
  assert.equal(result.ok, false);
  assert.match(result.error, /directory with this id already exists/);
  assert.match(
    await readFile(join(directory, 'requirement.md'), 'utf8'),
    /id: another-id/,
  );
});

test('leaves the original document intact when an atomic update cannot write', async (t) => {
  const { configPath, libraryRoot, projectRoot } = await fixture(t);
  const directory = join(libraryRoot, 'requirements', 'SeaFlow', 'read-only');
  await mkdir(directory, { recursive: true });
  const filename = join(directory, 'requirement.md');
  const original = `---\nid: read-only\ntitle: 不可写需求\nstatus: defined\ncreatedAt: 2026-09-01T00:00:00.000Z\nupdatedAt: 2026-09-02T00:00:00.000Z\n---\n\n原正文。\n`;
  await writeFile(filename, original);
  const mcp = startMcp(configPath);
  t.after(() => mcp.stop());
  await chmod(directory, 0o500);
  try {
    const result = await mcp.call('update_requirement_content', {
      project_root: projectRoot,
      requirement_id: 'read-only',
      sections: [section('', '新正文。')],
    });
    assert.equal(result.ok, false);
  } finally {
    await chmod(directory, 0o700);
  }
  assert.equal(await readFile(filename, 'utf8'), original);
});
