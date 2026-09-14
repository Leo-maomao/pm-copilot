import { execFile } from 'node:child_process';
import { randomBytes } from 'node:crypto';
import {
  mkdir,
  readdir,
  readFile,
  rename,
  stat,
  writeFile,
} from 'node:fs/promises';
import { basename, join, resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { promisify } from 'node:util';

const execute = promisify(execFile);
const configPath =
  process.env.PM_COPILOT_CONFIG_PATH ??
  join(process.env.HOME ?? '', '.config', 'pm-copilot', 'config.json');

const tools = [
  {
    name: 'configure_pm_copilot',
    description:
      '首次安装时配置产品助理仓库的绝对路径。仅写入当前用户本机配置，不会修改需求内容。',
    inputSchema: {
      type: 'object',
      required: ['repository_root'],
      properties: { repository_root: { type: 'string' } },
    },
  },
  {
    name: 'inspect_project_requirements',
    description:
      '读取当前项目在统一需求库中的已有需求、章节和图示路径。开发类补全或正文修改前必须先调用。',
    inputSchema: {
      type: 'object',
      required: ['project_root'],
      properties: {
        project_root: {
          type: 'string',
          description: '当前目标项目的绝对路径。',
        },
      },
    },
  },
  {
    name: 'complete_implemented_requirement',
    description:
      '将已在管理器创建且已贴图的需求补充为基于当前项目代码的正式需求。所有已有图示必须被明确归属，工具不会移动或删除图片文件。',
    inputSchema: {
      type: 'object',
      required: ['project_root', 'title', 'sections'],
      properties: {
        project_root: { type: 'string' },
        requirement_id: { type: 'string' },
        target_title: { type: 'string' },
        title: { type: 'string' },
        sections: { $ref: '#/$defs/sections' },
      },
      $defs: {
        sections: {
          type: 'array',
          minItems: 1,
          items: {
            type: 'object',
            required: ['title', 'description', 'image_paths'],
            properties: {
              title: { type: 'string' },
              description: { type: 'string' },
              image_paths: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },
  {
    name: 'create_text_requirement',
    description:
      '为当前项目创建无图示的正式需求，适用于 Bug 修复或纯文本产品需求。',
    inputSchema: {
      type: 'object',
      required: ['project_root', 'title', 'sections'],
      properties: {
        project_root: { type: 'string' },
        requirement_id: { type: 'string' },
        title: { type: 'string' },
        sections: { $ref: '#/$defs/sections' },
      },
      $defs: {
        sections: {
          type: 'array',
          minItems: 1,
          items: {
            type: 'object',
            required: ['title', 'description'],
            properties: {
              title: { type: 'string' },
              description: { type: 'string' },
            },
          },
        },
      },
    },
  },
  {
    name: 'update_requirement_content',
    description:
      '更新当前项目中已有需求的标题和正文。所有已有图示路径必须在提交的章节中保留且明确归属；不会修改状态、创建时间或图片文件。',
    inputSchema: {
      type: 'object',
      required: ['project_root', 'sections'],
      properties: {
        project_root: { type: 'string' },
        requirement_id: { type: 'string' },
        target_title: { type: 'string' },
        title: { type: 'string' },
        sections: { $ref: '#/$defs/sections' },
      },
      $defs: {
        sections: {
          type: 'array',
          minItems: 1,
          items: {
            type: 'object',
            required: ['title', 'description', 'image_paths'],
            properties: {
              title: { type: 'string' },
              description: { type: 'string' },
              image_paths: { type: 'array', items: { type: 'string' } },
            },
          },
        },
      },
    },
  },
];

function error(message) {
  throw new Error(message);
}

function projectDirectory(value) {
  if (
    typeof value !== 'string' ||
    !value ||
    value === '.' ||
    value === '..' ||
    value === '.manager' ||
    value.includes('\0') ||
    /[\\/]/.test(value)
  ) {
    error('Project origin mapping is invalid.');
  }
  return value;
}

function text(value, field) {
  if (typeof value !== 'string' || !value.trim())
    error(`${field} is required.`);
  return value.trim();
}

function slug(value) {
  const normalized = value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return normalized || 'requirement';
}

function requirementId(value) {
  const id = text(value, 'requirement_id');
  if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(id)) {
    error('requirement_id must be kebab-case.');
  }
  return id;
}

async function readConfig() {
  let value;
  try {
    value = JSON.parse(await readFile(configPath, 'utf8'));
  } catch {
    error(
      'PM Copilot repository is not configured. Set repositoryRoot in ~/.config/pm-copilot/config.json.',
    );
  }
  if (
    !value ||
    typeof value.repositoryRoot !== 'string' ||
    !value.repositoryRoot.trim()
  ) {
    error('PM Copilot config must contain repositoryRoot.');
  }
  const repositoryRoot = resolve(value.repositoryRoot);
  try {
    await readFile(
      join(repositoryRoot, 'packages', 'core', 'dist', 'index.js'),
    );
  } catch {
    error(
      'PM Copilot repository is missing packages/core/dist/index.js. Run pnpm build in the configured repository.',
    );
  }
  return repositoryRoot;
}

async function configureRepository(args) {
  const repositoryRoot = resolve(text(args.repository_root, 'repository_root'));
  try {
    await readFile(
      join(repositoryRoot, 'packages', 'core', 'dist', 'index.js'),
    );
  } catch {
    error(
      'PM Copilot repository is missing packages/core/dist/index.js. Run pnpm build in the selected repository first.',
    );
  }
  await writeAtomic(
    configPath,
    `${JSON.stringify({ repositoryRoot }, null, 2)}\n`,
  );
  return { ok: true, configured: true };
}

async function coreFor(repositoryRoot) {
  return import(
    pathToFileURL(join(repositoryRoot, 'packages', 'core', 'dist', 'index.js'))
      .href
  );
}

async function projectKey(projectRoot) {
  const root = resolve(text(projectRoot, 'project_root'));
  try {
    const { stdout } = await execute('git', [
      '-C',
      root,
      'config',
      '--get',
      'remote.origin.url',
    ]);
    const remote = stdout
      .trim()
      .replace(/\/$/, '')
      .replace(/\.git$/, '');
    const name = remote.split(/[/:"]/).filter(Boolean).at(-1);
    if (name) return name;
  } catch {
    // A project without an origin is intentionally grouped by its directory name.
  }
  return basename(root);
}

async function requirementRoot(repositoryRoot, key) {
  const managerDirectory = join(repositoryRoot, 'requirements', '.manager');
  for (const transaction of ['project-rename.json', 'project-delete.json']) {
    try {
      if ((await stat(join(managerDirectory, transaction))).isFile()) {
        error(
          'Project transaction recovery is pending. Restart the manager first.',
        );
      }
    } catch (caught) {
      if (
        caught instanceof Error &&
        caught.message ===
          'Project transaction recovery is pending. Restart the manager first.'
      ) {
        throw caught;
      }
      if (caught?.code !== 'ENOENT') {
        error('Project transaction recovery cannot be read.');
      }
    }
  }
  const aliasesFile = join(
    repositoryRoot,
    'requirements',
    '.manager',
    'project-origins.json',
  );
  let content;
  try {
    content = await readFile(aliasesFile, 'utf8');
  } catch (caught) {
    if (caught?.code === 'ENOENT')
      return join(repositoryRoot, 'requirements', key);
    error('Project origin mapping cannot be read.');
  }
  let origins;
  try {
    const value = JSON.parse(content);
    origins = value?.origins;
  } catch {
    error('Project origin mapping is invalid.');
  }
  if (!origins || typeof origins !== 'object' || Array.isArray(origins)) {
    error('Project origin mapping is invalid.');
  }
  const entries = Object.entries(origins).filter(([directory, origin]) => {
    if (typeof origin !== 'string' || !origin) {
      error('Project origin mapping is invalid.');
    }
    projectDirectory(directory);
    return origin === key;
  });
  if (entries.length > 1) error('Project origin mapping is ambiguous.');
  if (entries.length === 1) {
    const root = join(
      repositoryRoot,
      'requirements',
      projectDirectory(entries[0][0]),
    );
    try {
      if (!(await stat(root)).isDirectory()) {
        error('Mapped project directory is missing.');
      }
    } catch (caught) {
      if (
        caught instanceof Error &&
        caught.message === 'Mapped project directory is missing.'
      ) {
        throw caught;
      }
      error('Mapped project directory is missing.');
    }
    return root;
  }
  return join(repositoryRoot, 'requirements', projectDirectory(key));
}

async function loadRequirements(repositoryRoot, key, core) {
  const root = await requirementRoot(repositoryRoot, key);
  let entries;
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return [];
  }
  const requirements = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const filename = join(root, entry.name, 'requirement.md');
    try {
      const document = core.parseRequirementMarkdown(
        await readFile(filename, 'utf8'),
      );
      if (document.id !== entry.name) continue;
      requirements.push({
        directory: join(root, entry.name),
        document,
        filename,
      });
    } catch {
      // A malformed document is not a valid write target.
    }
  }
  return requirements;
}

function selectRequirement(requirements, args) {
  const id =
    typeof args.requirement_id === 'string' ? args.requirement_id.trim() : '';
  const targetTitle =
    typeof args.target_title === 'string' ? args.target_title.trim() : '';
  if (!id && !targetTitle) error('requirement_id or target_title is required.');
  const matches = requirements.filter(({ document }) =>
    id ? document.id === id : document.title === targetTitle,
  );
  if (!matches.length) error('No matching requirement was found.');
  if (matches.length > 1)
    error('Requirement target is ambiguous. Use requirement_id.');
  return matches[0];
}

function allImages(document) {
  return document.sections.flatMap((section) =>
    section.images.map((image) => image.path),
  );
}

function contentSections(
  input,
  existingImages,
  requireImageMapping,
  allowImages,
) {
  if (!Array.isArray(input) || !input.length)
    error('sections must not be empty.');
  const sections = input.map((section, index) => {
    if (!section || typeof section !== 'object')
      error(`sections[${index}] is invalid.`);
    const title = typeof section.title === 'string' ? section.title.trim() : '';
    const description = text(
      section.description,
      `sections[${index}].description`,
    );
    const paths = section.image_paths ?? [];
    if (
      !Array.isArray(paths) ||
      paths.some((path) => typeof path !== 'string')
    ) {
      error(`sections[${index}].image_paths is invalid.`);
    }
    if (/\r|\n/u.test(title))
      error(`sections[${index}].title must be single-line.`);
    if (/^#{1,6}\s/mu.test(description)) {
      error(
        `sections[${index}].description must not contain Markdown headings.`,
      );
    }
    if (!allowImages && paths.length) {
      error('Pure text requirements must not contain image paths.');
    }
    return {
      title,
      description,
      images: paths.map((path) => ({ path: path.trim() })),
    };
  });
  const supplied = sections.flatMap((section) =>
    section.images.map((image) => image.path),
  );
  if (new Set(supplied).size !== supplied.length)
    error('Each image path may belong to only one section.');
  if (sections.filter((section) => !section.title).length > 1) {
    error('Only one top-level content section is allowed.');
  }
  if (
    requireImageMapping &&
    (supplied.length !== existingImages.length ||
      supplied.some((path) => !existingImages.includes(path)))
  ) {
    error('Every existing image path must be assigned to exactly one section.');
  }
  return sections.map((section) => ({
    ...section,
    images: section.images.map((image) => ({
      path: image.path,
      alt:
        image.path
          .split('/')
          .at(-1)
          ?.replace(/\.[^.]+$/, '') || '需求图示',
    })),
  }));
}

async function writeAtomic(filename, content) {
  await mkdir(resolve(filename, '..'), { recursive: true });
  const temporary = `${filename}.${process.pid}-${randomBytes(6).toString('hex')}.tmp`;
  await writeFile(temporary, content, 'utf8');
  await rename(temporary, filename);
}

function responseDocument(projectKey, document) {
  return {
    id: document.id,
    project_key: projectKey,
    status: document.status,
    title: document.title,
  };
}

async function inspect(args) {
  const repositoryRoot = await readConfig();
  const core = await coreFor(repositoryRoot);
  const key = await projectKey(args.project_root);
  const requirements = await loadRequirements(repositoryRoot, key, core);
  return {
    ok: true,
    project_key: key,
    requirements: requirements.map(({ document }) => ({
      id: document.id,
      title: document.title,
      status: document.status,
      sections: document.sections.map((section) => ({
        title: section.title,
        description: section.description,
        image_paths: section.images.map((image) => image.path),
      })),
    })),
  };
}

function assertUniqueTitle(requirements, title, target) {
  if (
    requirements.some(
      (candidate) => candidate !== target && candidate.document.title === title,
    )
  ) {
    error('A requirement with this title already exists.');
  }
}

async function completeImplemented(args) {
  const repositoryRoot = await readConfig();
  const core = await coreFor(repositoryRoot);
  const key = await projectKey(args.project_root);
  const requirements = await loadRequirements(repositoryRoot, key, core);
  const target = selectRequirement(requirements, args);
  const images = allImages(target.document);
  if (!images.length)
    error(
      'The selected requirement has no images. Create the requirement and add visuals in the manager first.',
    );
  const title = text(args.title, 'title');
  assertUniqueTitle(requirements, title, target);
  // The timeline belongs to creation: a content update never rewrites it.
  const document = {
    ...target.document,
    title,
    status: 'defined',
    sections: contentSections(args.sections, images, true, true),
  };
  await writeAtomic(target.filename, core.createRequirementMarkdown(document));
  return { ok: true, requirement: responseDocument(key, document) };
}

async function createText(args) {
  const repositoryRoot = await readConfig();
  const core = await coreFor(repositoryRoot);
  const key = await projectKey(args.project_root);
  const requirements = await loadRequirements(repositoryRoot, key, core);
  const title = text(args.title, 'title');
  if (requirements.some(({ document }) => document.title === title))
    error('A requirement with this title already exists.');
  const id = args.requirement_id
    ? requirementId(args.requirement_id)
    : `${slug(title)}-${Date.now().toString(36)}`;
  if (requirements.some(({ document }) => document.id === id))
    error('A requirement with this id already exists.');
  const root = await requirementRoot(repositoryRoot, key);
  try {
    await stat(join(root, id));
    error('A requirement directory with this id already exists.');
  } catch (caught) {
    if (
      caught instanceof Error &&
      caught.message === 'A requirement directory with this id already exists.'
    ) {
      throw caught;
    }
    if (caught?.code !== 'ENOENT') {
      error('Requirement directory cannot be checked.');
    }
  }
  const timestamp = new Date().toISOString();
  const document = {
    id,
    title,
    status: 'defined',
    createdAt: timestamp,
    updatedAt: timestamp,
    updatedAtTimestamp: Date.parse(timestamp),
    sections: contentSections(args.sections, [], false, false),
  };
  await writeAtomic(
    join(root, id, 'requirement.md'),
    core.createRequirementMarkdown(document),
  );
  return { ok: true, requirement: responseDocument(key, document) };
}

async function updateContent(args) {
  const repositoryRoot = await readConfig();
  const core = await coreFor(repositoryRoot);
  const key = await projectKey(args.project_root);
  const requirements = await loadRequirements(repositoryRoot, key, core);
  const target = selectRequirement(requirements, args);
  const title =
    typeof args.title === 'string' && args.title.trim()
      ? args.title.trim()
      : target.document.title;
  assertUniqueTitle(requirements, title, target);
  // The timeline belongs to creation: a content update never rewrites it.
  const document = {
    ...target.document,
    title,
    sections: contentSections(
      args.sections,
      allImages(target.document),
      true,
      true,
    ),
  };
  await writeAtomic(target.filename, core.createRequirementMarkdown(document));
  return { ok: true, requirement: responseDocument(key, document) };
}

async function callTool(name, args) {
  if (name === 'configure_pm_copilot') return configureRepository(args);
  if (name === 'inspect_project_requirements') return inspect(args);
  if (name === 'complete_implemented_requirement')
    return completeImplemented(args);
  if (name === 'create_text_requirement') return createText(args);
  if (name === 'update_requirement_content') return updateContent(args);
  error('Unknown tool.');
}

async function handle(message) {
  if (message.method === 'notifications/initialized') return undefined;
  if (message.method === 'initialize') {
    return {
      jsonrpc: '2.0',
      id: message.id,
      result: {
        protocolVersion: '2024-11-05',
        capabilities: { tools: {} },
        serverInfo: { name: 'pm-copilot', version: '0.1.0' },
      },
    };
  }
  if (message.method === 'tools/list') {
    return { jsonrpc: '2.0', id: message.id, result: { tools } };
  }
  if (message.method !== 'tools/call') return undefined;
  try {
    const payload = await callTool(
      message.params?.name,
      message.params?.arguments ?? {},
    );
    return {
      jsonrpc: '2.0',
      id: message.id,
      result: { content: [{ type: 'text', text: JSON.stringify(payload) }] },
    };
  } catch (caught) {
    const messageText =
      caught instanceof Error ? caught.message : 'Unexpected MCP failure.';
    return {
      jsonrpc: '2.0',
      id: message.id,
      result: {
        content: [
          {
            type: 'text',
            text: JSON.stringify({ ok: false, error: messageText }),
          },
        ],
        isError: true,
      },
    };
  }
}

let buffer = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', async (chunk) => {
  buffer += chunk;
  const lines = buffer.split('\n');
  buffer = lines.pop() ?? '';
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      const response = await handle(JSON.parse(line));
      if (response) process.stdout.write(`${JSON.stringify(response)}\n`);
    } catch {
      process.stdout.write(
        `${JSON.stringify({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error.' } })}\n`,
      );
    }
  }
});
