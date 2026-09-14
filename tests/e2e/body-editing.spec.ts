import { expect, type Page, test } from '@playwright/test';

/** In-manager body editing must round-trip to requirement.md. */
async function unlockEditing(page: Page): Promise<void> {
  await page.goto('/');
  await page.locator('.navigator-heading').click();
  const digits = ['9', '5', '2', '7'];
  for (const [index, digit] of digits.entries()) {
    await page.getByLabel(`第 ${index + 1} 位编辑口令`).fill(digit);
  }
  await expect(page.getByRole('dialog', { name: '进入编辑状态' })).toHaveCount(
    0,
  );
}

async function createRequirement(page: Page, title: string): Promise<string> {
  const response = await page.request.post('/api/requirements', {
    data: { projectName: 'demo-project', title },
  });
  expect(response.status()).toBe(201);
  const { created: record } = await response.json();
  return `${record.projectName}:${record.id}`;
}

async function readStored(
  page: Page,
  assetKey: string,
): Promise<Record<string, unknown>> {
  const payload = await (await page.request.get('/api/index')).json();
  return payload.projects
    .flatMap((project: { requirements: unknown[] }) => project.requirements)
    .find(
      (requirement: { assetKey: string }) => requirement.assetKey === assetKey,
    );
}

test('edits a requirement body and writes it back to requirement.md', async ({
  page,
}) => {
  await unlockEditing(page);
  const assetKey = await createRequirement(page, '正文编辑用例');

  try {
    await page.reload();
    await page
      .locator('.tree-project summary')
      .filter({ hasText: 'demo-project' })
      .click();
    const card = page
      .locator('.requirement-card')
      .filter({ hasText: '正文编辑用例' });
    await expect(card).toHaveCount(1);

    // Reading is the default; the pencil opens the editor and jumps into it.
    await expect(card.getByLabel('需求正文')).toHaveCount(0);
    await card.getByTitle('编辑正文').click();
    const editor = card.getByLabel('需求正文');
    await expect(editor).toBeVisible();
    await expect(editor).toBeFocused();
    await expect(editor).toBeInViewport();
    await expect(editor).toHaveValue('');

    const before = await readStored(page, assetKey);
    const beforeTimestamp = before.document.updatedAtTimestamp;
    const beforeUpdatedAt = before.document.updatedAt;

    await editor.fill(
      '一、列表规则\n\n1. 编辑后的第一行。\n2. 编辑后的第二行。',
    );
    await card.getByRole('button', { name: '保存', exact: true }).click();

    await expect(card.getByLabel('需求正文')).toHaveCount(0);
    await expect(card.locator('.requirement-markdown')).toContainText(
      '编辑后的第二行',
    );

    const stored = await readStored(page, assetKey);
    expect(stored.document.sections[0].description).toContain('编辑后的第二行');
    // A body fix must not move the requirement in the updatedAt-sorted tree.
    expect(stored.document.updatedAtTimestamp).toBe(beforeTimestamp);
    expect(stored.document.updatedAt).toBe(beforeUpdatedAt);

    // Reopening shows what is stored, not the raw draft.
    await card.getByTitle('编辑正文').click();
    await expect(card.getByLabel('需求正文')).toHaveValue(/### 一、列表规则/);
    await card.getByRole('button', { name: '取消', exact: true }).click();
    await expect(card.getByLabel('需求正文')).toHaveCount(0);

    // Every other manager write keeps the timeline too: the date and the tree
    // position belong to creation, not to editing.
    await page.request.put(
      `/api/requirements/${encodeURIComponent(assetKey)}`,
      { data: { title: '正文编辑用例改名' } },
    );
    const renamed = await readStored(page, assetKey);
    expect(renamed.document.title).toBe('正文编辑用例改名');
    expect(renamed.document.updatedAtTimestamp).toBe(beforeTimestamp);
    expect(renamed.document.updatedAt).toBe(beforeUpdatedAt);
  } finally {
    const removed = await page.request.delete(
      `/api/requirements/${encodeURIComponent(assetKey)}`,
    );
    expect(removed.ok()).toBeTruthy();
  }
});

test('keeps unsaved drafts while another requirement is saved', async ({
  page,
}) => {
  await unlockEditing(page);
  const assetKeys = [
    await createRequirement(page, '草稿保留用例 A'),
    await createRequirement(page, '草稿保留用例 B'),
  ];

  try {
    await page.reload();
    await page
      .locator('.tree-project summary')
      .filter({ hasText: 'demo-project' })
      .click();
    const cardA = page
      .locator('.requirement-card')
      .filter({ hasText: '草稿保留用例 A' });
    const cardB = page
      .locator('.requirement-card')
      .filter({ hasText: '草稿保留用例 B' });

    await cardA.getByTitle('编辑正文').click();
    await cardB.getByTitle('编辑正文').click();
    await cardA.getByLabel('需求正文').fill('A 的未保存草稿。');
    await cardB.getByLabel('需求正文').fill('B 的正文。');
    await cardB.getByRole('button', { name: '保存', exact: true }).click();
    await expect(cardB.getByLabel('需求正文')).toHaveCount(0);

    await expect(cardA.getByLabel('需求正文')).toHaveValue('A 的未保存草稿。');

    const stored = await readStored(page, assetKeys[0]);
    expect(stored.document.sections[0].description).not.toContain(
      'A 的未保存草稿',
    );
  } finally {
    for (const assetKey of assetKeys) {
      const removed = await page.request.delete(
        `/api/requirements/${encodeURIComponent(assetKey)}`,
      );
      expect(removed.ok()).toBeTruthy();
    }
  }
});

test('keeps the body read-only without an edit session', async ({ page }) => {
  await page.goto('/');
  await page
    .locator('.tree-project summary')
    .filter({ hasText: 'demo-project' })
    .click();
  await expect(page.locator('.requirement-card').first()).toBeVisible();
  await expect(page.getByTitle('编辑正文')).toHaveCount(0);
  await expect(page.getByLabel('需求正文')).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: '保存', exact: true }),
  ).toHaveCount(0);
});
