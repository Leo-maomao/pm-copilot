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
  /** Project directory name -> Git repository name the plugin looks up. */
  origins: Readonly<Record<string, string>>;
  projects: readonly ProjectRequirements[];
}>;

export type CreatedRequirementCollection = ScannedRequirements &
  Readonly<{
    created: Readonly<{ id: string; projectName: string }>;
  }>;

export async function scanProjectCollection(): Promise<ScannedRequirements> {
  const response = await fetch('/api/index');
  if (!response.ok) {
    throw new Error('Unable to load the local requirement index.');
  }
  return (await response.json()) as ScannedRequirements;
}

export async function unlockEditor(passcode: string): Promise<void> {
  const response = await fetch('/api/edit-session', {
    body: JSON.stringify({ passcode }),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('Unable to unlock editor.');
  }
}

export async function refreshProjectCollection(): Promise<ScannedRequirements> {
  const response = await fetch('/api/refresh', { method: 'POST' });
  if (!response.ok) {
    throw new Error('Unable to refresh the local requirement index.');
  }
  return (await response.json()) as ScannedRequirements;
}

export async function createRequirement(
  input: Readonly<{
    projectName: string;
    title: string;
  }>,
): Promise<CreatedRequirementCollection> {
  const response = await fetch('/api/requirements', {
    body: JSON.stringify(input),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });
  if (!response.ok) throw new Error('Unable to create requirement.');
  return (await response.json()) as CreatedRequirementCollection;
}

export async function createProject(
  projectName: string,
  origin?: string,
): Promise<ScannedRequirements> {
  const response = await fetch('/api/projects', {
    body: JSON.stringify(origin ? { projectName, origin } : { projectName }),
    headers: { 'Content-Type': 'application/json' },
    method: 'POST',
  });
  if (!response.ok) throw new Error('Unable to create project.');
  return (await response.json()) as ScannedRequirements;
}

/** Record which Git repository the plugin should resolve this project by. */
export async function setProjectOrigin(
  projectName: string,
  origin: string,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectName)}/origin`,
    {
      body: JSON.stringify({ origin }),
      headers: { 'Content-Type': 'application/json' },
      method: 'PUT',
    },
  );
  if (!response.ok) throw new Error('Unable to update the project origin.');
  return (await response.json()) as ScannedRequirements;
}

export async function renameProject(
  projectName: string,
  nextProjectName: string,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectName)}`,
    {
      body: JSON.stringify({ projectName: nextProjectName }),
      headers: { 'Content-Type': 'application/json' },
      method: 'PATCH',
    },
  );
  if (!response.ok) throw new Error('Unable to rename project.');
  return (await response.json()) as ScannedRequirements;
}

export async function deleteProject(
  projectName: string,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/projects/${encodeURIComponent(projectName)}`,
    { method: 'DELETE' },
  );
  if (!response.ok) throw new Error('Unable to delete project.');
  return (await response.json()) as ScannedRequirements;
}

export async function deleteRequirement(
  requirement: LoadedRequirement,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    { method: 'DELETE' },
  );
  if (!response.ok) throw new Error('Unable to delete requirement.');
  return (await response.json()) as ScannedRequirements;
}

export async function updateRequirementStatus(
  requirement: LoadedRequirement,
  status: RequirementStatus,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    {
      body: JSON.stringify({ status }),
      headers: { 'Content-Type': 'application/json' },
      method: 'PUT',
    },
  );
  if (!response.ok) {
    throw new Error('Unable to update the requirement status.');
  }
  return (await response.json()) as ScannedRequirements;
}

/** Write the section descriptions edited in the manager. */
export async function updateRequirementContent(
  requirement: LoadedRequirement,
  descriptions: readonly string[],
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    {
      body: JSON.stringify({
        sections: descriptions.map((description) => ({ description })),
      }),
      headers: { 'Content-Type': 'application/json' },
      method: 'PUT',
    },
  );
  if (!response.ok) {
    throw new Error('Unable to update the requirement content.');
  }
  return (await response.json()) as ScannedRequirements;
}

export async function updateRequirementTitle(
  requirement: LoadedRequirement,
  title: string,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}`,
    {
      body: JSON.stringify({ title }),
      headers: { 'Content-Type': 'application/json' },
      method: 'PUT',
    },
  );
  if (!response.ok) throw new Error('Unable to update the requirement title.');
  return (await response.json()) as ScannedRequirements;
}

export async function addRequirementVisual(
  requirement: LoadedRequirement,
  input: Readonly<{ data: string; filename: string; sectionTitle: string }>,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visuals`,
    {
      body: JSON.stringify(input),
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
    },
  );
  if (!response.ok) {
    throw new Error('Unable to add requirement visual.');
  }
  return (await response.json()) as ScannedRequirements;
}

export async function deleteRequirementVisual(
  requirement: LoadedRequirement,
  path: string,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visuals`,
    {
      body: JSON.stringify({ path }),
      headers: { 'Content-Type': 'application/json' },
      method: 'DELETE',
    },
  );
  if (!response.ok) throw new Error('Unable to delete requirement visual.');
  return (await response.json()) as ScannedRequirements;
}

export async function updateRequirementVisualName(
  requirement: LoadedRequirement,
  input: Readonly<{ alt: string; path: string }>,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visuals`,
    {
      body: JSON.stringify(input),
      headers: { 'Content-Type': 'application/json' },
      method: 'PUT',
    },
  );
  if (!response.ok) {
    throw new Error('Unable to update requirement visual name.');
  }
  return (await response.json()) as ScannedRequirements;
}

export async function updateVisualGroups(
  requirement: LoadedRequirement,
  input: Readonly<{ action: 'add' | 'remove'; sectionIndex?: number }>,
): Promise<ScannedRequirements> {
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visual-groups`,
    {
      body: JSON.stringify(input),
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
    },
  );
  if (!response.ok) throw new Error('Unable to update visual groups.');
  return (await response.json()) as ScannedRequirements;
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
  const response = await fetch(
    `/api/requirements/${encodeURIComponent(requirement.assetKey)}/visual-order`,
    {
      body: JSON.stringify(input),
      headers: { 'Content-Type': 'application/json' },
      method: 'POST',
    },
  );
  if (!response.ok) throw new Error('Unable to update visual order.');
  return (await response.json()) as ScannedRequirements;
}

export function readImageUrl(
  requirement: LoadedRequirement,
  assetPath: string,
): string {
  return `/api/assets/${encodeURIComponent(requirement.assetKey)}?path=${encodeURIComponent(assetPath)}`;
}
