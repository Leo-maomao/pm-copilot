import { randomBytes } from 'node:crypto';
import {
  mkdir,
  readdir,
  readFile,
  rename,
  rm,
  stat,
  writeFile,
} from 'node:fs/promises';
import { createServer } from 'node:http';
import { extname, join, normalize, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

import {
  createRequirementMarkdown,
  parseRequirementMarkdown,
  type RequirementDocument,
  type RequirementImage,
  type RequirementSection,
  type RequirementStatus,
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

const managerPort = 57391;
const port =
  process.env.NODE_ENV === 'test'
    ? Number.parseInt(process.env.PM_COPILOT_PORT ?? String(managerPort), 10)
    : managerPort;
const host = process.env.PM_COPILOT_HOST ?? '0.0.0.0';
const workspaceRoot = resolve(
  fileURLToPath(new URL('../../..', import.meta.url)),
);
const libraryRoot = resolve(
  process.env.PM_COPILOT_LIBRARY_ROOT ?? join(workspaceRoot, 'requirements'),
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
const projectOriginsFilename = join(
  libraryRoot,
  '.manager',
  'project-origins.json',
);
const projectRenameFilename = join(
  libraryRoot,
  '.manager',
  'project-rename.json',
);
const projectDeleteFilename = join(
  libraryRoot,
  '.manager',
  'project-delete.json',
);
const projectOrigins = new Map<string, string>();
let projectOriginsError: string | undefined;

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
  return join(libraryRoot, projectKey, id);
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
    projectName === '.manager' ||
    projectName.includes('\0') ||
    /[\\/]/.test(projectName)
  ) {
    return undefined;
  }
  return projectName;
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
  // Two writes to the same file in the same millisecond would otherwise share a
  // temporary name, and the first rename would make the second one fail.
  const temporary = `${filename}.${process.pid}-${randomBytes(6).toString('hex')}.tmp`;
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
async function loadProjectOrigins(): Promise<void> {
  let content: string;
  try {
    content = await readFile(projectOriginsFilename, 'utf8');
  } catch (caught) {
    if ((caught as { code?: string }).code === 'ENOENT') return;
    projectOriginsError = 'Project origin mapping cannot be read.';
    return;
  }
  try {
    const value: unknown = JSON.parse(content);
    if (!value || typeof value !== 'object' || !('origins' in value)) {
      throw new Error('Invalid mapping.');
    }
    const origins = (value as { origins?: unknown }).origins;
    if (!origins || typeof origins !== 'object' || Array.isArray(origins)) {
      throw new Error('Invalid mapping.');
    }
    for (const [directory, origin] of Object.entries(origins)) {
      if (
        !safeProjectName(directory) ||
        typeof origin !== 'string' ||
        !origin
      ) {
        throw new Error('Invalid mapping.');
      }
      projectOrigins.set(directory, origin);
    }
  } catch {
    projectOrigins.clear();
    projectOriginsError = 'Project origin mapping is invalid.';
  }
}
async function persistProjectOrigins(): Promise<void> {
  await writeAtomic(
    projectOriginsFilename,
    `${JSON.stringify({ origins: Object.fromEntries(projectOrigins) }, null, 2)}\n`,
  );
}
async function projectDirectoryExists(name: string): Promise<boolean> {
  try {
    return (await stat(join(libraryRoot, name))).isDirectory();
  } catch {
    return false;
  }
}
async function ensureProjectMaintenanceAvailable(): Promise<void> {
  if (projectOriginsError) throw new Error(projectOriginsError);
  for (const filename of [projectRenameFilename, projectDeleteFilename]) {
    try {
      if ((await stat(filename)).isFile()) {
        throw new Error(
          'Project transaction recovery is pending. Restart the manager.',
        );
      }
    } catch (caught) {
      if ((caught as { code?: string }).code !== 'ENOENT') throw caught;
    }
  }
}
async function recoverProjectRename(): Promise<void> {
  let content: string;
  try {
    content = await readFile(projectRenameFilename, 'utf8');
  } catch (caught) {
    if ((caught as { code?: string }).code === 'ENOENT') return;
    projectOriginsError = 'Project rename recovery cannot be read.';
    return;
  }
  try {
    const value: unknown = JSON.parse(content);
    if (!value || typeof value !== 'object') throw new Error('Invalid rename.');
    const { from, origins, to } = value as Record<string, unknown>;
    const sourceName = safeProjectName(from);
    const targetName = safeProjectName(to);
    if (
      !sourceName ||
      !targetName ||
      !origins ||
      typeof origins !== 'object' ||
      Array.isArray(origins)
    ) {
      throw new Error('Invalid rename.');
    }
    for (const [directory, origin] of Object.entries(origins)) {
      if (
        !safeProjectName(directory) ||
        typeof origin !== 'string' ||
        !origin
      ) {
        throw new Error('Invalid rename.');
      }
    }
    const sourceExists = await projectDirectoryExists(sourceName);
    const targetExists = await projectDirectoryExists(targetName);
    if (sourceExists === targetExists) throw new Error('Ambiguous rename.');
    if (targetExists) {
      await writeAtomic(
        projectOriginsFilename,
        `${JSON.stringify({ origins }, null, 2)}\n`,
      );
    }
    await rm(projectRenameFilename, { force: true });
  } catch {
    projectOriginsError = 'Project rename recovery is invalid.';
  }
}
async function recoverProjectDelete(): Promise<void> {
  let content: string;
  try {
    content = await readFile(projectDeleteFilename, 'utf8');
  } catch (caught) {
    if ((caught as { code?: string }).code === 'ENOENT') return;
    projectOriginsError = 'Project delete recovery cannot be read.';
    return;
  }
  try {
    const value: unknown = JSON.parse(content);
    if (!value || typeof value !== 'object') throw new Error('Invalid delete.');
    const { origins, projectName } = value as Record<string, unknown>;
    const directory = safeProjectName(projectName);
    if (
      !directory ||
      !origins ||
      typeof origins !== 'object' ||
      Array.isArray(origins)
    ) {
      throw new Error('Invalid delete.');
    }
    for (const [name, origin] of Object.entries(origins)) {
      if (!safeProjectName(name) || typeof origin !== 'string' || !origin) {
        throw new Error('Invalid delete.');
      }
    }
    if (!(await projectDirectoryExists(directory))) {
      await writeAtomic(
        projectOriginsFilename,
        `${JSON.stringify({ origins }, null, 2)}\n`,
      );
    }
    await rm(projectDeleteFilename, { force: true });
  } catch {
    projectOriginsError = 'Project delete recovery is invalid.';
  }
}
async function renameProjectDirectory(
  projectName: string,
  nextProjectName: string,
): Promise<void> {
  const origin = projectOrigins.get(projectName) ?? projectName;
  const previousOrigins = new Map(projectOrigins);
  const nextOrigins = new Map(projectOrigins);
  nextOrigins.delete(projectName);
  nextOrigins.set(nextProjectName, origin);
  await writeAtomic(
    projectRenameFilename,
    `${JSON.stringify(
      {
        from: projectName,
        origins: Object.fromEntries(nextOrigins),
        to: nextProjectName,
      },
      null,
      2,
    )}\n`,
  );
  await rename(
    join(libraryRoot, projectName),
    join(libraryRoot, nextProjectName),
  );
  projectOrigins.clear();
  for (const [directory, projectOrigin] of nextOrigins) {
    projectOrigins.set(directory, projectOrigin);
  }
  try {
    await persistProjectOrigins();
  } catch (caught) {
    try {
      await rename(
        join(libraryRoot, nextProjectName),
        join(libraryRoot, projectName),
      );
    } finally {
      projectOrigins.clear();
      for (const [directory, projectOrigin] of previousOrigins) {
        projectOrigins.set(directory, projectOrigin);
      }
    }
    throw caught;
  }
  await rm(projectRenameFilename, { force: true });
}
async function deleteProjectDirectory(projectName: string): Promise<void> {
  const nextOrigins = new Map(projectOrigins);
  nextOrigins.delete(projectName);
  await writeAtomic(
    projectDeleteFilename,
    `${JSON.stringify(
      {
        origins: Object.fromEntries(nextOrigins),
        projectName,
      },
      null,
      2,
    )}\n`,
  );
  await rm(join(libraryRoot, projectName), { force: true, recursive: true });
  projectOrigins.clear();
  for (const [directory, origin] of nextOrigins) {
    projectOrigins.set(directory, origin);
  }
  await persistProjectOrigins();
  await rm(projectDeleteFilename, { force: true });
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

let indexRefresh: Promise<void> = Promise.resolve();

/**
 * Rebuild the index from disk. Scans are serialized and the finished index is
 * swapped in one step, so a concurrent reader never sees a half-built index and
 * the newest scan always wins.
 */
function refreshIndex(): Promise<void> {
  indexRefresh = indexRefresh.then(scanLibrary, scanLibrary);
  return indexRefresh;
}

async function scanLibrary(): Promise<void> {
  const nextProjects: ProjectRequirements[] = [];
  const nextAssets = new Map<string, string>();
  const nextTargets = new Map<string, string>();
  let projectEntries: readonly import('node:fs').Dirent[] = [];
  try {
    projectEntries = await readdir(libraryRoot, {
      withFileTypes: true,
    });
  } catch {
    projects = nextProjects;
    assets = nextAssets;
    targets = nextTargets;
    return;
  }
  for (const project of projectEntries.filter(
    (entry) => entry.isDirectory() && !entry.name.startsWith('.'),
  )) {
    const records: LoadedRequirement[] = [];
    try {
      const entries = await readdir(join(libraryRoot, project.name), {
        withFileTypes: true,
      });
      for (const entry of entries.filter((item) => item.isDirectory())) {
        const directory = requirementDirectory(project.name, entry.name);
        try {
          const parsedDocument = parseRequirementMarkdown(
            await readFile(join(directory, 'requirement.md'), 'utf8'),
          );
          if (
            parsedDocument.id !== entry.name ||
            records.some(({ document }) => document.id === parsedDocument.id)
          ) {
            continue;
          }
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
          nextAssets.set(key, directory);
          nextTargets.set(key, join(directory, 'requirement.md'));
        } catch {
          /* ignore one malformed record */
        }
      }
    } catch {
      /* empty project */
    }
    nextProjects.push({
      projectName: project.name,
      requirements: records.sort(
        (a, b) => b.document.updatedAtTimestamp - a.document.updatedAtTimestamp,
      ),
    });
  }
  projects = nextProjects.sort(
    (a, b) =>
      (b.requirements[0]?.document.updatedAtTimestamp ?? 0) -
      (a.requirements[0]?.document.updatedAtTimestamp ?? 0),
  );
  assets = nextAssets;
  targets = nextTargets;
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
    // The manager shows and edits the Git origin mapping the plugin looks up.
    origins: Object.fromEntries(projectOrigins),
    projects: projects.map((project) => ({
      projectName: project.projectName,
      requirements: project.requirements.map(({ assetKey: key, document }) => ({
        assetKey: key,
        document,
      })),
    })),
  };
}
/**
 * Requirements are ordered and dated by creation, so no manager write touches
 * the timeline: status, title, body and figures all leave `updatedAt` alone.
 */
async function updateRequirement(
  key: string,
  mutate: (document: RequirementDocument) => RequirementDocument,
): Promise<RequirementDocument> {
  const filename = targets.get(key);
  if (!filename) throw new Error('Requirement not found.');
  const current = parseRequirementMarkdown(await readFile(filename, 'utf8'));
  const next = mutate(current);
  await writeAtomic(filename, createRequirementMarkdown(next));
  return next;
}

/**
 * In-manager body editing: replace every section description by index.
 * Section titles and image ownership stay untouched.
 */
function withEditedSectionDescriptions(
  current: RequirementDocument,
  raw: unknown,
): readonly RequirementSection[] {
  if (!Array.isArray(raw) || raw.length !== current.sections.length) {
    throw new Error('Invalid sections payload.');
  }
  return current.sections.map((section, index) => {
    const candidate: unknown = raw[index];
    if (
      typeof candidate !== 'object' ||
      candidate === null ||
      typeof (candidate as { description?: unknown }).description !== 'string'
    ) {
      throw new Error('Invalid sections payload.');
    }
    return {
      ...section,
      description: (candidate as { description: string }).description.trim(),
    };
  });
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

await recoverProjectRename();
await recoverProjectDelete();
await loadProjectOrigins();
await refreshIndex();
await loadEditorSessions();
createServer(async (request, response) => {
  const url = new URL(
    request.url ?? '/',
    `http://${request.headers.host ?? 'localhost'}`,
  );
  // The plugin MCP writes requirement files straight to disk, so a cached index
  // would hide them until someone pressed the manager's refresh button.
  if (url.pathname === '/api/index' && request.method === 'GET') {
    await refreshIndex();
    return void json(response, indexPayload(request));
  }
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
  if (url.pathname === '/api/projects' && request.method === 'POST') {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      await ensureProjectMaintenanceAvailable();
      const body = await readBody(request);
      const projectName = safeProjectName(body.projectName);
      const requestedOrigin =
        body.origin === undefined ? undefined : safeProjectName(body.origin);
      if (body.origin !== undefined && !requestedOrigin) {
        throw new Error('Invalid Git origin.');
      }
      if (!projectName || projectExists(projectName)) {
        throw new Error('Invalid project.');
      }
      await mkdir(join(libraryRoot, projectName), {
        recursive: true,
      });
      // The plugin looks requirements up by Git repository name; when the
      // directory is named differently the mapping has to exist from the start.
      if (requestedOrigin && requestedOrigin !== projectName) {
        projectOrigins.set(projectName, requestedOrigin);
        await persistProjectOrigins();
      }
      await refreshIndex();
      return void json(response, indexPayload(request), 201);
    } catch {
      return void json(response, { error: 'Project creation failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/projects/') &&
    url.pathname.endsWith('/origin') &&
    request.method === 'PUT'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      await ensureProjectMaintenanceAvailable();
      const projectName = safeProjectName(
        decodeURIComponent(
          url.pathname.slice('/api/projects/'.length, -'/origin'.length),
        ),
      );
      if (!projectName || !projectExists(projectName)) {
        throw new Error('Unknown project.');
      }
      const body = await readBody(request);
      const raw = typeof body.origin === 'string' ? body.origin.trim() : '';
      const nextOrigin = raw ? safeProjectName(raw) : undefined;
      if (raw && !nextOrigin) throw new Error('Invalid Git origin.');
      // An origin identical to the directory name needs no mapping: the plugin
      // finds that directory by itself.
      if (!nextOrigin || nextOrigin === projectName) {
        projectOrigins.delete(projectName);
      } else {
        projectOrigins.set(projectName, nextOrigin);
      }
      await persistProjectOrigins();
      return void json(response, indexPayload(request));
    } catch {
      return void json(
        response,
        { error: 'Project origin update failed.' },
        400,
      );
    }
  }
  if (url.pathname.startsWith('/api/projects/') && request.method === 'PATCH') {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    try {
      await ensureProjectMaintenanceAvailable();
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
        await renameProjectDirectory(projectName, nextProjectName);
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
      await ensureProjectMaintenanceAvailable();
      const projectName = safeProjectName(
        decodeURIComponent(url.pathname.slice('/api/projects/'.length)),
      );
      if (!projectName || !projectExists(projectName)) {
        throw new Error('Invalid project deletion.');
      }
      await deleteProjectDirectory(projectName);
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
    !url.pathname.slice('/api/requirements/'.length).includes('/') &&
    request.method === 'DELETE'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length),
    );
    try {
      const directory = assets.get(key);
      if (!directory) throw new Error('Requirement not found.');
      await rm(directory, { force: true, recursive: true });
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(
        response,
        { error: 'Requirement deletion failed.' },
        400,
      );
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    !url.pathname.slice('/api/requirements/'.length).includes('/') &&
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
        ...(body.sections === undefined
          ? {}
          : {
              sections: withEditedSectionDescriptions(current, body.sections),
            }),
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
      const uploaded = join(directory, 'assets', imageName);
      await writeFile(uploaded, Buffer.from(encoded, 'base64'));
      const appendImage = updateRequirement(key, (document) => {
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
      try {
        await appendImage;
      } catch (error) {
        // An image whose reference never landed would sit in assets/ forever.
        await rm(uploaded, { force: true });
        throw error;
      }
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
      const filename = targets.get(key);
      if (!filename) throw new Error('Requirement not found.');
      const directory = resolve(filename, '..');
      const updated = await updateRequirement(key, (document) => ({
        ...document,
        sections: document.sections.map((section) => ({
          ...section,
          images: section.images.filter((image) => image.path !== path),
        })),
      }));
      // Dropping the last reference is what "删除图示" means, so the file goes
      // with it; otherwise every deleted figure stays in assets/ forever.
      const stillReferenced = updated.sections.some((section) =>
        section.images.some((image) => image.path === path),
      );
      const asset = resolve(directory, path);
      if (!stillReferenced && inside(directory, asset)) {
        await rm(asset, { force: true });
      }
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Visual deletion failed.' }, 400);
    }
  }
  if (
    url.pathname.startsWith('/api/requirements/') &&
    url.pathname.endsWith('/visuals') &&
    request.method === 'PUT'
  ) {
    if (!canEdit(request))
      return void json(response, { error: 'Local-only write.' }, 403);
    const key = decodeURIComponent(
      url.pathname.slice('/api/requirements/'.length, -'/visuals'.length),
    );
    try {
      const body = await readBody(request);
      const path = typeof body.path === 'string' ? body.path : '';
      const alt = typeof body.alt === 'string' ? body.alt.trim() : '';
      if (!path.startsWith('assets/') || !alt) {
        throw new Error('Invalid visual name.');
      }
      await updateRequirement(key, (document) => ({
        ...document,
        sections: document.sections.map((section) => ({
          ...section,
          images: section.images.map((image) =>
            image.path === path ? { ...image, alt } : image,
          ),
        })),
      }));
      await refreshIndex();
      return void json(response, indexPayload(request));
    } catch {
      return void json(response, { error: 'Visual name update failed.' }, 400);
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
