import { createHash, randomBytes } from 'node:crypto';
import {
  cp,
  mkdir,
  readdir,
  readFile,
  rename,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
import { createServer } from 'node:http';
import { homedir } from 'node:os';
import { extname, join, normalize, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  createRequirementMarkdown,
  parseHistoricalRequirementMarkdown,
  parseRequirementMarkdown,
  type RequirementDocument,
  type RequirementImage,
  type RequirementSection,
  type RequirementStatus,
  readHistoricalRequirementTimeline,
  requirementStatuses,
} from '@pm-copilot/core';

type LoadedRequirement = Readonly<{
  assetDirectory: string;
  assetKey: string;
  document: RequirementDocument;
}>;
type ProjectRequirements = Readonly<{
  projectName: string;
  requirements: readonly LoadedRequirement[];
}>;
type Draft = Readonly<{
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  images: readonly RequirementImage[];
}>;

const port = Number.parseInt(process.env.PM_COPILOT_PORT ?? '57391', 10);
const host = process.env.PM_COPILOT_HOST ?? '0.0.0.0';
const workspaceRoot = resolve(
  fileURLToPath(new URL('../../..', import.meta.url)),
);
const libraryRoot = resolve(
  process.env.PM_COPILOT_LIBRARY_ROOT ?? join(workspaceRoot, 'requirements'),
);
const migrationScanRoot = resolve(
  process.env.PM_COPILOT_HISTORY_ROOT ?? join(homedir(), 'Desktop'),
);
const staticRoot = join(workspaceRoot, 'apps/manager-web/dist');
const contentTypes: Readonly<Record<string, string>> = {
  '.css': 'text/css; charset=utf-8',
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.png': 'image/png',
  '.svg': 'image/svg+xml',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
};
let projects: readonly ProjectRequirements[] = [];
let assets = new Map<string, string>();
let targets = new Map<string, string>();
const editorSessions = new Set<string>();
const editorSessionsFilename = join(
  libraryRoot,
  '.manager',
  'editor-sessions.json',
);

function inside(parent: string, target: string): boolean {
  const path = relative(parent, target);
  return path !== '' && !path.startsWith('..') && !path.includes('/../');
}
function slug(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '') || 'requirement'
  );
}
function assetKey(projectKey: string, id: string): string {
  return `${projectKey}:${id}`;
}
function now(): string {
  return new Date().toISOString();
}
function isStatus(value: unknown): value is RequirementStatus {
  return (
    typeof value === 'string' &&
    requirementStatuses.some((item) => item.id === value)
  );
}
function readCookie(
  request: import('node:http').IncomingMessage,
  name: string,
): string | undefined {
  const value = request.headers.cookie
    ?.split(';')
    .map((item) => item.trim().split('='))
    .find(([key]) => key === name)?.[1];
  return value ? decodeURIComponent(value) : undefined;
}
function canEdit(request: import('node:http').IncomingMessage): boolean {
  const session = readCookie(request, 'requirement_manager_editor');
  return Boolean(session && editorSessions.has(session));
}
function safeFilename(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const filename = value.trim();
  return filename && filename === filename.split(/[\\/]/).at(-1)
    ? filename
    : undefined;
}
function requirementDirectory(projectKey: string, id: string): string {
  return join(libraryRoot, 'projects', projectKey, 'requirements', id);
}
function projectExists(projectName: string): boolean {
  return projects.some((project) => project.projectName === projectName);
}
function safeProjectName(value: unknown): string | undefined {
  if (typeof value !== 'string') return undefined;
  const projectName = value.trim();
  if (
    !projectName ||
    projectName === '.' ||
    projectName === '..' ||
    projectName.includes('\0') ||
    /[\\/]/.test(projectName)
  ) {
    return undefined;
  }
  return projectName;
}
function draftDirectory(id: string): string {
  return join(libraryRoot, 'inbox', id);
}
function json(
  response: import('node:http').ServerResponse,
  value: unknown,
  statusCode = 200,
): void {
  response.writeHead(statusCode, {
    'Cache-Control': 'no-store',
    'Content-Type': 'application/json; charset=utf-8',
  });
  response.end(JSON.stringify(value));
}

async function writeAtomic(filename: string, content: string): Promise<void> {
  await mkdir(resolve(filename, '..'), { recursive: true });
  const temporary = `${filename}.${process.pid}-${Date.now()}.tmp`;
  await writeFile(temporary, content, 'utf8');
  await rename(temporary, filename);
}
async function loadEditorSessions(): Promise<void> {
  try {
    const value: unknown = JSON.parse(
      await readFile(editorSessionsFilename, 'utf8'),
    );
    if (!value || typeof value !== 'object' || !('sessions' in value)) return;
    const sessions = (value as { sessions?: unknown }).sessions;
    if (!Array.isArray(sessions)) return;
    for (const session of sessions) {
      if (typeof session === 'string' && /^[a-f0-9]{48}$/.test(session))
        editorSessions.add(session);
    }
  } catch {
    /* A missing local editor-session store means every browser starts read-only. */
  }
}
async function persistEditorSessions(): Promise<void> {
  await writeAtomic(
    editorSessionsFilename,
    `${JSON.stringify({ sessions: [...editorSessions] }, null, 2)}\n`,
  );
}
async function readBody(
  request: import('node:http').IncomingMessage,
): Promise<Record<string, unknown>> {
  let body = '';
  for await (const chunk of request) {
    body += chunk;
    if (body.length > 2_000_000) throw new Error('Payload too large.');
  }
  const result: unknown = JSON.parse(body);
  if (!result || typeof result !== 'object' || Array.isArray(result))
    throw new Error('Invalid request.');
  return result as Record<string, unknown>;
}

async function readDrafts(): Promise<readonly Draft[]> {
  try {
    const entries = await readdir(join(libraryRoot, 'inbox'), {
      withFileTypes: true,
    });
    return await Promise.all(
      entries
        .filter((entry) => entry.isDirectory())
        .map(
          async (entry) =>
            JSON.parse(
              await readFile(
                join(libraryRoot, 'inbox', entry.name, 'draft.json'),
                'utf8',
              ),
            ) as Draft,
        ),
    );
  } catch {
    return [];
  }
}

async function refreshIndex(): Promise<void> {
  projects = [];
  assets = new Map();
  targets = new Map();
  let projectEntries: readonly import('node:fs').Dirent[] = [];
  try {
    projectEntries = await readdir(join(libraryRoot, 'projects'), {
      withFileTypes: true,
    });
  } catch {
    return;
  }
  for (const project of projectEntries.filter((entry) => entry.isDirectory())) {
    const records: LoadedRequirement[] = [];
    try {
      const entries = await readdir(
        join(libraryRoot, 'projects', project.name, 'requirements'),
        { withFileTypes: true },
      );
      for (const entry of entries.filter((item) => item.isDirectory())) {
        const directory = requirementDirectory(project.name, entry.name);
        try {
          const parsedDocument = parseRequirementMarkdown(
            await readFile(join(directory, 'requirement.md'), 'utf8'),
          );
          const document: RequirementDocument = {
            ...parsedDocument,
            sections: await Promise.all(
              parsedDocument.sections.map(async (section) => ({
                ...section,
                images: await filterExistingImages(directory, section.images),
              })),
            ),
          };
          const key = assetKey(project.name, document.id);
          records.push({ assetDirectory: directory, assetKey: key, document });
          assets.set(key, directory);
          targets.set(key, join(directory, 'requirement.md'));
        } catch {
          /* ignore one malformed record */
        }
      }
    } catch {
      /* empty project */
    }
    projects = [
      ...projects,
      {
        projectName: project.name,
        requirements: records.sort(
          (a, b) =>
            b.document.updatedAtTimestamp - a.document.updatedAtTimestamp,
        ),
      },
    ];
  }
  projects = [...projects].sort(
    (a, b) =>
      (b.requirements[0]?.document.updatedAtTimestamp ?? 0) -
      (a.requirements[0]?.document.updatedAtTimestamp ?? 0),
  );
}

async function filterExistingImages(
  directory: string,
  images: readonly RequirementImage[],
): Promise<readonly RequirementImage[]> {
  const available = await Promise.all(
    images.map(async (image) => {
      const target = resolve(directory, image.path);
      if (!inside(directory, target)) return undefined;
      try {
        const info = await stat(target);
        return info.isFile() ? image : undefined;
      } catch {
        return undefined;
      }
    }),
  );
  return available.filter(
    (image): image is RequirementImage => image !== undefined,
  );
}

function indexPayload(request: import('node:http').IncomingMessage): object {
  return {
    canEdit: canEdit(request),
    projects: projects.map((project) => ({
      projectName: project.projectName,
      requirements: project.requirements.map(({ assetKey: key, document }) => ({
        assetKey: key,
        document,
      })),
    })),
  };
}
async function updateRequirement(
  key: string,
  mutate: (document: RequirementDocument) => RequirementDocument,
): Promise<void> {
  const filename = targets.get(key);
  if (!filename) throw new Error('Requirement not found.');
  const current = parseRequirementMarkdown(await readFile(filename, 'utf8'));
  const next = {
    ...mutate(current),
    updatedAt: now(),
    updatedAtTimestamp: Date.now(),
  };
  await writeAtomic(filename, createRequirementMarkdown(next));
}

async function reconcileHistoricalTimeline(
  projectKey: string,
  id: string,
  timeline: Readonly<{ createdAt: string; updatedAt: string }>,
): Promise<boolean> {
  const filename = join(requirementDirectory(projectKey, id), 'requirement.md');
  try {
    const current = parseRequirementMarkdown(await readFile(filename, 'utf8'));
    if (
      current.createdAt === timeline.createdAt &&
      current.updatedAt === timeline.updatedAt
    ) {
      return true;
    }
    await writeAtomic(
      filename,
      createRequirementMarkdown({
        ...current,
        createdAt: timeline.createdAt,
        updatedAt: timeline.updatedAt,
        updatedAtTimestamp: Date.parse(timeline.updatedAt),
      }),
    );
    return true;
  } catch {
    return false;
  }
}

async function migrateHistory(): Promise<void> {
  const markerRoot = join(libraryRoot, '.migration', 'records');
  const completionMarker = join(libraryRoot, '.migration', 'completed.md');
  let projectEntries: readonly import('node:fs').Dirent[] = [];
  try {
    projectEntries = await readdir(migrationScanRoot, { withFileTypes: true });
  } catch {
    return;
  }
  const historicalDirectory = ['pm', 'copilot', 'outputs'].join('-');
  for (const project of projectEntries.filter((entry) => entry.isDirectory())) {
    let exports: readonly import('node:fs').Dirent[] = [];
    const sourceRoot = join(
      migrationScanRoot,
      project.name,
      historicalDirectory,
    );
    try {
      exports = await readdir(sourceRoot, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const exported of exports.filter((entry) => entry.isDirectory())) {
      const sourceDirectory = join(sourceRoot, exported.name);
      const sourceMarkdown = join(
        sourceDirectory,
        `${['p', 'r', 'd'].join('')}.md`,
      );
      try {
        const fingerprint = createHash('sha256')
          .update(sourceMarkdown)
          .digest('hex');
        const info = await stat(sourceMarkdown);
        const source = await readFile(sourceMarkdown, 'utf8');
        const timeline = readHistoricalRequirementTimeline(
          source,
          info.mtime.toISOString(),
        );
        const documents = parseHistoricalRequirementMarkdown(source, {
          createdAt: timeline.createdAt,
          idPrefix: `history-${slug(exported.name)}`,
          updatedAt: timeline.updatedAt,
        });
        for (const document of documents) {
          const id = `${slug(document.id)}-${fingerprint.slice(0, 8)}`;
          const directory = requirementDirectory(slug(project.name), id);
          if (
            await reconcileHistoricalTimeline(slug(project.name), id, timeline)
          ) {
            continue;
          }
          const rewritten = {
            ...document,
            id,
            createdAt: timeline.createdAt,
            status: 'defined' as const,
            sections: document.sections.map((section) => ({
              ...section,
              images: section.images.map((image) => ({
                ...image,
                path: image.path.replace(/^\.\//, ''),
              })),
            })),
          };
          await mkdir(directory, { recursive: true });
          try {
            await cp(
              join(sourceDirectory, 'assets'),
              join(directory, 'assets'),
              { recursive: true, force: false, errorOnExist: false },
            );
          } catch {
            /* no assets */
          }
          await writeAtomic(
            join(directory, 'requirement.md'),
            createRequirementMarkdown(rewritten),
          );
        }
        await writeAtomic(
          join(markerRoot, `${fingerprint}.md`),
          `source: ${fingerprint}\nimportedAt: ${now()}\n`,
        );
      } catch {
        /* one partial export never blocks startup */
      }
    }
  }
  await writeAtomic(completionMarker, `completedAt: ${now()}\n`);
}

function htmlToText(content: string): string {
  return content
    .replace(/<br\s*\/?\s*>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&quot;/gi, '"')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

function detailTitle(content: string, fallback: string): string {
  const firstLine = htmlToText(content).split(/\r?\n/)[0]?.trim() ?? '';
  const title = firstLine.replace(/^[一二三四五六七八九十]+、\s*/, '');
  return title.length > 0 ? title : fallback;
}

function readHtmlMediaSections(
  html: string,
  title: string,
): readonly RequirementSection[] {
  const escapedTitle = title.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const content = new RegExp(
    `<h3\\b[^>]*>\\s*(?:\\d+(?:\\.\\d+)*\\s+)?${escapedTitle}\\s*<\\/h3>([\\s\\S]*?)(?=<h3\\b|$)`,
    'i',
  ).exec(html)?.[1];
  if (!content) return [];
  const blocks = Array.from(
    content.matchAll(
      /<div class=["'][^"']*detail-media-block[^"']*["'][^>]*>\s*<div class=["'][^"']*detail-media[^"']*["'][^>]*>\s*<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>\s*<\/div>\s*<div class=["'][^"']*detail-copy[^"']*["'][^>]*>([\s\S]*?)<\/div>\s*<\/div>/gi,
    ),
  );
  return blocks.flatMap((block, index) => {
    const path = block[1]?.replace(/^\.\//, '').trim();
    const description = htmlToText(block[2] ?? '');
    if (!path) return [];
    return [
      {
        title: detailTitle(block[2] ?? '', `细化内容 ${index + 1}`),
        description,
        images: [{ alt: '需求图示', path }],
      },
    ];
  });
}

async function repairHistoricalHtmlVisuals(): Promise<void> {
  let projectEntries: readonly import('node:fs').Dirent[] = [];
  try {
    projectEntries = await readdir(migrationScanRoot, { withFileTypes: true });
  } catch {
    return;
  }
  const historicalDirectory = ['pm', 'copilot', 'outputs'].join('-');
  for (const project of projectEntries.filter((entry) => entry.isDirectory())) {
    const sourceRoot = join(
      migrationScanRoot,
      project.name,
      historicalDirectory,
    );
    let exports: readonly import('node:fs').Dirent[] = [];
    try {
      exports = await readdir(sourceRoot, { withFileTypes: true });
    } catch {
      continue;
    }
    for (const exported of exports.filter((entry) => entry.isDirectory())) {
      const sourceDirectory = join(sourceRoot, exported.name);
      try {
        const sourceMarkdown = join(
          sourceDirectory,
          `${['p', 'r', 'd'].join('')}.md`,
        );
        const fingerprint = createHash('sha256')
          .update(sourceMarkdown)
          .digest('hex');
        const info = await stat(sourceMarkdown);
        const html = await readFile(join(sourceDirectory, 'prd.html'), 'utf8');
        const sourceDocuments = parseHistoricalRequirementMarkdown(
          await readFile(sourceMarkdown, 'utf8'),
          {
            idPrefix: `history-${slug(exported.name)}`,
            updatedAt: info.mtime.toISOString(),
          },
        );
        for (const sourceDocument of sourceDocuments) {
          const mediaSections = readHtmlMediaSections(
            html,
            sourceDocument.title,
          );
          if (!mediaSections.length) continue;
          const id = `${slug(sourceDocument.id)}-${fingerprint.slice(0, 8)}`;
          const filename = join(
            requirementDirectory(slug(project.name), id),
            'requirement.md',
          );
          const current = parseRequirementMarkdown(
            await readFile(filename, 'utf8'),
          );
          await writeAtomic(
            filename,
            createRequirementMarkdown({
              ...current,
              sections: mediaSections,
            }),
          );
        }
      } catch {
        // Historical exports without HTML remain unchanged.
      }
    }
  }
}

async function normalizeMigratedStatuses(): Promise<void> {
  const marker = join(libraryRoot, '.migration', 'status-normalized-v1.md');
  try {
    await stat(marker);
    return;
  } catch {
    // Legacy sources have no reliable lifecycle state.
  }
  for (const project of projects) {
    for (const requirement of project.requirements) {
      if (!requirement.document.id.startsWith('history-')) continue;
      if (requirement.document.status !== 'defined') continue;
      await updateRequirement(requirement.assetKey, (document) => ({
        ...document,
        status: 'planning',
      }));
    }
  }
  await writeAtomic(marker, `completedAt: ${now()}\n`);
}

async function sendFile(
  response: import('node:http').ServerResponse,
  filename: string,
): Promise<void> {
  try {
    const content = await readFile(filename);
    response.writeHead(200, {
      'Cache-Control': 'no-store',
      'Content-Type':
        contentTypes[extname(filename).toLowerCase()] ??
        'application/octet-stream',
    });
    response.end(content);
  } catch {
    response.writeHead(404).end();
  }
}

await migrateHistory();
await repairHistoricalHtmlVisuals();
await refreshIndex();
await normalizeMigratedStatuses();
await refreshIndex();
await loadEditorSessions();
createServer(async (request, response) => {
  const url = new URL(
    request.url ?? '/',
    `http://${request.headers.host ?? 'localhost'}`,
  );
  if (url.pathname === '/api/index' && request.method === 'GET')
    return void json(response, indexPayload(request));
  if (url.pathname === '/api/refresh' && request.method === 'POST') {
    await refreshIndex();
    return void json(response, indexPayload(request));
  }
  if (url.pathname === '/api/edit-session' && request.method === 'POST') {
    try {
      const body = await readBody(request);
      if (body.passcode !== '9527') throw new Error('Invalid passcode.');
      const session = randomBytes(24).toString('hex');
      editorSessions.add(session);
      await persistEditorSessions();
      response.writeHead(204, {
        'Cache-Control': 'no-store',
        'Set-Cookie': `requirement_manager_editor=${session}; HttpOnly; SameSite=Strict; Path=/; Max-Age=315360000`,
      });
      response.end();
    } catch {
      json(response, { error: 'Invalid passcode.' }, 401);
    }
    return;
  }
  if (url.pathname === '/api/drafts' && request.method === 'GET')
    return void json(response, {
      canEdit: canEdit(request),
      drafts: await readDrafts(),
    });
  if (url.pathname === '/api/drafts' && request.method === 'POST') {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      const body = await readBody(request);
      const title = typeof body.title === 'string' ? body.title.trim() : '';
      if (!title) throw new Error('Title required.');
      const id = `${slug(title)}-${Date.now().toString(36)}`;
      const timestamp = now();
      const draft: Draft = {
        id,
        title,
        createdAt: timestamp,
        updatedAt: timestamp,
        images: [],
      };
      await writeAtomic(
        join(draftDirectory(id), 'draft.json'),
        JSON.stringify(draft, null, 2),
      );
      return void json(response, draft, 201);
    } catch {
      return void json(response, { error: 'Draft creation failed.' }, 400);
    }
  }
  if (url.pathname === '/api/projects' && request.method === 'POST') {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      const body = await readBody(request);
      const projectName = safeProjectName(body.projectName);
      if (!projectName || projectExists(projectName)) {
        throw new Error('Invalid project.');
      }
      await mkdir(join(libraryRoot, 'projects', projectName, 'requirements'), {
        recursive: true,
      });
      await refreshIndex();
      return void json(response, indexPayload(request), 201);
    } catch {
      return void json(response, { error: 'Project creation failed.' }, 400);
    }
  }
  if (url.pathname.startsWith('/api/projects/') && request.method === 'PATCH') {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      const projectName = safeProjectName(
        decodeURIComponent(url.pathname.slice('/api/projects/'.length)),
      );
      const body = await readBody(request);
      const nextProjectName = safeProjectName(body.projectName);
      if (
        !projectName ||
        !nextProjectName ||
        !projectExists(projectName) ||
        (nextProjectName !== projectName && projectExists(nextProjectName))
      ) {
        throw new Error('Invalid project rename.');
      }
      if (nextProjectName !== projectName) {
        await rename(
          join(libraryRoot, 'projects', projectName),
          join(libraryRoot, 'projects', nextProjectName),
        );
      }
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Project rename failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/projects/') &&
    request.method === 'DELETE'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      const projectName = safeProjectName(
        decodeURIComponent(url.pathname.slice('/api/projects/'.length)),
      );
      if (!projectName || !projectExists(projectName)) {
        throw new Error('Invalid project deletion.');
      }
      await rm(join(libraryRoot, 'projects', projectName), {
        force: true,
        recursive: true,
      });
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Project deletion failed.' }, 400);
    }
  }
  if (url.pathname === '/api/requirements' && request.method === 'POST') {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      const body = await readBody(request);
      const projectName =
        typeof body.projectName === 'string' ? body.projectName.trim() : '';
      const title = typeof body.title === 'string' ? body.title.trim() : '';
      if (!projectName || !title || !projectExists(projectName)) {
        throw new Error('Invalid requirement.');
      }
      const id = `${slug(title)}-${Date.now().toString(36)}`;
      const timestamp = now();
      const document: RequirementDocument = {
        id,
        title,
        status: 'planning',
        createdAt: timestamp,
        updatedAt: timestamp,
        updatedAtTimestamp: Date.now(),
        summary: '待补充需求内容。',
        sections: [{ title: '', description: '', images: [] }],
      };
      await writeAtomic(
        join(requirementDirectory(projectName, id), 'requirement.md'),
        createRequirementMarkdown(document),
      );
      await refreshIndex();
      return void json(
        response,
        { ...indexPayload(request), created: { id, projectName } },
        201,
      );
    } catch {
      return void json(
        response,
        { error: 'Requirement creation failed.' },
        400,
      );
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    request.method === 'PUT'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length),
    );
    try {
      const body = await readBody(request);
      await updateRequirement(key, (current) => ({
        ...current,
        ...(typeof body.title === 'string' && body.title.trim()
          ? { title: body.title.trim() }
          : {}),
        ...(isStatus(body.status) ? { status: body.status } : {}),
      }));
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Requirement update failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    url.pathname.endsWith('/visuals') &&
    request.method === 'POST'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length, -'/visuals'.length),
    );
    const filename = targets.get(key);
    try {
      const body = await readBody(request);
      const imageName = safeFilename(body.filename);
      const data = typeof body.data === 'string' ? body.data : '';
      const sectionTitle =
        typeof body.sectionTitle === 'string'
          ? body.sectionTitle.trim()
          : undefined;
      if (
        !imageName ||
        sectionTitle === undefined ||
        !data.startsWith('data:image/')
      ) {
        throw new Error('Invalid visual.');
      }
      if (!filename) throw new Error('Requirement not found.');
      const directory = resolve(filename, '..');
      const encoded = data.slice(data.indexOf(',') + 1);
      await mkdir(join(directory, 'assets'), { recursive: true });
      await writeFile(
        join(directory, 'assets', imageName),
        Buffer.from(encoded, 'base64'),
      );
      await updateRequirement(key, (document) => {
        const image: RequirementImage = {
          alt: '需求图示',
          path: `assets/${imageName}`,
        };
        const existing = document.sections.findIndex(
          (section) => section.title === sectionTitle,
        );
        if (existing >= 0) {
          return {
            ...document,
            sections: document.sections.map((section, index) =>
              index === existing
                ? { ...section, images: [...section.images, image] }
                : section,
            ),
          };
        }
        return {
          ...document,
          sections: [
            ...document.sections,
            { title: sectionTitle, description: '', images: [image] },
          ],
        };
      });
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Visual update failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    url.pathname.endsWith('/visuals') &&
    request.method === 'DELETE'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length, -'/visuals'.length),
    );
    try {
      const body = await readBody(request);
      const path = typeof body.path === 'string' ? body.path : '';
      if (!path.startsWith('assets/')) throw new Error('Invalid visual path.');
      await updateRequirement(key, (document) => ({
        ...document,
        sections: document.sections.map((section) => ({
          ...section,
          images: section.images.filter((image) => image.path !== path),
        })),
      }));
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Visual deletion failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    url.pathname.endsWith('/visual-groups') &&
    request.method === 'POST'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length, -'/visual-groups'.length),
    );
    try {
      const body = await readBody(request);
      const action = body.action;
      const sectionIndex =
        typeof body.sectionIndex === 'number' &&
        Number.isInteger(body.sectionIndex)
          ? body.sectionIndex
          : undefined;
      await updateRequirement(key, (document) => {
        if (action === 'add') {
          if (
            sectionIndex !== undefined &&
            (sectionIndex < 0 || sectionIndex > document.sections.length)
          ) {
            throw new Error('Invalid visual group position.');
          }
          const generatedIndexes = document.sections
            .map((section) => /^图示\s*(\d+)$/u.exec(section.title)?.[1])
            .map((value) => Number.parseInt(value ?? '0', 10));
          const nextNumber = Math.max(0, ...generatedIndexes) + 1;
          const nextSections = [...document.sections];
          nextSections.splice(sectionIndex ?? nextSections.length, 0, {
            title: `图示 ${nextNumber}`,
            description: '',
            images: [],
          });
          return {
            ...document,
            sections: nextSections,
          };
        }
        if (
          action !== 'remove' ||
          sectionIndex === undefined ||
          sectionIndex <= 0 ||
          sectionIndex >= document.sections.length
        ) {
          throw new Error('Invalid visual group update.');
        }
        const section = document.sections[sectionIndex];
        if (!section) throw new Error('Visual group not found.');
        return {
          ...document,
          sections: document.sections
            .map((current, index) =>
              index === sectionIndex - 1
                ? {
                    ...current,
                    description: [current.description, section.description]
                      .filter(Boolean)
                      .join('\n\n'),
                    images: [...current.images, ...section.images],
                  }
                : current,
            )
            .filter((_, index) => index !== sectionIndex),
        };
      });
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Visual group update failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    url.pathname.endsWith('/visual-order') &&
    request.method === 'POST'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length, -'/visual-order'.length),
    );
    try {
      const body = await readBody(request);
      const path = typeof body.path === 'string' ? body.path : '';
      const targetPath =
        typeof body.targetPath === 'string' ? body.targetPath : undefined;
      const insertAfter = body.insertAfter === true;
      const targetSectionIndex =
        typeof body.targetSectionIndex === 'number' &&
        Number.isInteger(body.targetSectionIndex)
          ? body.targetSectionIndex
          : undefined;
      if (
        !path.startsWith('assets/') ||
        (targetPath !== undefined && !targetPath.startsWith('assets/')) ||
        targetSectionIndex === undefined
      ) {
        throw new Error('Invalid visual order.');
      }
      await updateRequirement(key, (document) => {
        if (
          targetSectionIndex < 0 ||
          targetSectionIndex >= document.sections.length
        ) {
          throw new Error('Visual group not found.');
        }
        const image = document.sections
          .flatMap((section) => section.images)
          .find((candidate) => candidate.path === path);
        if (!image) throw new Error('Visual not found.');
        const sections = document.sections.map((section) => ({
          ...section,
          images: section.images.filter((candidate) => candidate.path !== path),
        }));
        const target = sections[targetSectionIndex];
        if (!target) throw new Error('Visual group not found.');
        const targetIndex = targetPath
          ? target.images.findIndex(
              (candidate) => candidate.path === targetPath,
            )
          : -1;
        if (targetPath && targetIndex < 0)
          throw new Error('Visual target not found.');
        const images = [...target.images];
        images.splice(
          targetIndex < 0 ? images.length : targetIndex + (insertAfter ? 1 : 0),
          0,
          image,
        );
        sections[targetSectionIndex] = { ...target, images };
        return { ...document, sections };
      });
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Visual order update failed.' }, 400);
    }
  }
  if (url.pathname.startsWith('/api/assets/') && request.method === 'GET') {
    const directory = assets.get(
      decodeURIComponent(url.pathname.slice('/api/assets/'.length)),
    );
    const path = url.searchParams.get('path');
    if (!directory || !path) return void response.writeHead(404).end();
    const target = resolve(directory, path);
    if (!inside(directory, target)) return void response.writeHead(404).end();
    return void (await sendFile(response, target));
  }
  const requested =
    url.pathname === '/'
      ? 'index.html'
      : normalize(url.pathname).replace(/^[/\\]+/, '');
  const target = resolve(staticRoot, requested);
  await sendFile(
    response,
    inside(staticRoot, target) ? target : join(staticRoot, 'index.html'),
  );
}).listen(port, host, () =>
  console.log(`Requirement manager available at http://${host}:${port}/`),
);
