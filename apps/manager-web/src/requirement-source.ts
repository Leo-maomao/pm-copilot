import type { RequirementDocument, RequirementStatus } from '@pm-copilot/core';

export type LoadedRequirement = Readonly<{
  document: RequirementDocument;
  assetKey: string;
}>;

export type ProjectRequirements = Readonly<{
  projectName: string;
  requirements: readonly LoadedRequirement[];
}>;

export type ScannedRequirements = Readonly<{
  canEdit: boolean;
  /** Origins this manager answers on from another machine, for shared links. */
  lanOrigins?: readonly string[];
  /** Project directory name -> Git repository name the plugin looks up. */
  origins: Readonly<Record<string, string>>;
  projects: readonly ProjectRequirements[];
}>;

export type CreatedRequirementCollection = ScannedRequirements &
  Readonly<{
    created: Readonly<{ id: string; projectName: string }>;
  }>;

async function request(
  path: string,
  errorMessage: string,
  method = 'GET',
  body?: unknown,
): Promise<Response> {
  const options =
    method === 'GET'
      ? undefined
      : body === undefined
        ? { method }
        : {
            body: JSON.stringify(body),
            headers: { 'Content-Type': 'application/json' },
            method,
          };
  const response = await fetch(path, options);
  if (!response.ok) throw new Error(errorMessage);
  return response;
}

async function requestJson<Result = ScannedRequirements>(
  path: string,
  errorMessage: string,
  method = 'GET',
  body?: unknown,
): Promise<Result> {
  const response = await request(path, errorMessage, method, body);
  return (await response.json()) as Result;
}

export async function scanProjectCollection(): Promise<ScannedRequirements> {
  return requestJson(
    '/api/index',
    'Unable to load the local requirement index.',
  );
}

export async function unlockEditor(passcode: string): Promise<void> {
  await request('/api/edit-session', 'Unable to unlock editor.', 'POST', {
    passcode,
  });
}

export async function refreshProjectCollection(): Promise<ScannedRequirements> {
  return requestJson(
    '/api/refresh',
    'Unable to refresh the local requirement index.',
    'POST',
  );
}

export async function createRequirement(
  input: Readonly<{
    projectName: string;
    title: string;
  }>,
): Promise<CreatedRequirementCollection> {
  return requestJson<CreatedRequirementCollection>(
    '/api/requirements',
    'Unable to create requirement.',
    'POST',
    input,
  );
}

export async function createProject(
  projectName: string,
  origin?: string,
): Promise<ScannedRequirements> {
  return requestJson(
    '/api/projects',
    'Unable to create project.',
    'POST',
    origin ? { projectName, origin } : { projectName },
  );
}

/** Record which Git repository the plugin should resolve this project by. */
export async function setProjectOrigin(
  projectName: string,
  origin: string,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectName)}/origin`,
    'Unable to update the project origin.',
    'PUT',
    { origin },
  );
}

export async function renameProject(
  projectName: string,
  nextProjectName: string,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectName)}`,
    'Unable to rename project.',
    'PATCH',
    { projectName: nextProjectName },
  );
}

export async function deleteProject(
  projectName: string,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/projects/${encodeURIComponent(projectName)}`,
    'Unable to delete project.',
    'DELETE',
  );
}

export async function deleteRequirement(
  requirement: LoadedRequirement,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    'Unable to delete requirement.',
    'DELETE',
  );
}

export async function updateRequirementStatus(
  requirement: LoadedRequirement,
  status: RequirementStatus,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    'Unable to update the requirement status.',
    'PUT',
    { status },
  );
}

/** Write the section descriptions edited in the manager. */
export async function updateRequirementContent(
  requirement: LoadedRequirement,
  descriptions: readonly string[],
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    'Unable to update the requirement content.',
    'PUT',
    {
      sections: descriptions.map((description) => ({ description })),
    },
  );
}

export async function updateRequirementTitle(
  requirement: LoadedRequirement,
  title: string,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    'Unable to update the requirement title.',
    'PUT',
    { title },
  );
}

export async function addRequirementVisual(
  requirement: LoadedRequirement,
  input: Readonly<{ data: string; filename: string; sectionTitle: string }>,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visuals`,
    'Unable to add requirement visual.',
    'POST',
    input,
  );
}

export async function deleteRequirementVisual(
  requirement: LoadedRequirement,
  path: string,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visuals`,
    'Unable to delete requirement visual.',
    'DELETE',
    { path },
  );
}

export async function updateRequirementVisualName(
  requirement: LoadedRequirement,
  input: Readonly<{ alt: string; path: string }>,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visuals`,
    'Unable to update requirement visual name.',
    'PUT',
    input,
  );
}

export async function updateVisualGroups(
  requirement: LoadedRequirement,
  input: Readonly<{ action: 'add' | 'remove'; sectionIndex?: number }>,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visual-groups`,
    'Unable to update visual groups.',
    'POST',
    input,
  );
}

export async function updateVisualOrder(
  requirement: LoadedRequirement,
  input: Readonly<{
    insertAfter?: boolean;
    path: string;
    targetPath?: string;
    targetSectionIndex: number;
  }>,
): Promise<ScannedRequirements> {
  return requestJson(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visual-order`,
    'Unable to update visual order.',
    'POST',
    input,
  );
}

export function readImageUrl(
  requirement: LoadedRequirement,
  assetPath: string,
): string {
  return `/api/assets/${encodeURIComponent(requirement.assetKey)}?path=${encodeURIComponent(assetPath)}`;
}
