import { expect, type Page, test } from '@playwright/test';

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

async function createRequirement(
  page: Page,
  title: string,
): Promise<Readonly<{ id: string; path: string }>> {
  const response = await page.request.post('/api/requirements', {
    data: { projectName: 'demo-project', title },
  });
  expect(response.status()).toBe(201);
  const { created: record } = await response.json();
  return {
    id: record.id,
    path: `/r/${encodeURIComponent(record.projectName)}/${encodeURIComponent(record.id)}`,
  };
}

async function removeRequirements(
  page: Page,
  created: readonly Readonly<{ id: string }>[],
): Promise<void> {
  for (const item of created) {
    const removed = await page.request.delete(
      `/api/requirements/${encodeURIComponent(`demo-project:${item.id}`)}`,
    );
    expect(removed.ok()).toBeTruthy();
  }
}

async function expectSelected(page: Page, title: string): Promise<void> {
  await expect(
    page.locator('.tree-item[aria-current="true"] .tree-item-title'),
  ).toHaveText(title);
}

test('opens the requirement a link points at', async ({ page }) => {
  await unlockEditing(page);
  // The linked requirement sits in the middle of a list longer than the pane,
  // so reaching it means the pane scrolled rather than started there.
  const below: Awaited<ReturnType<typeof createRequirement>>[] = [];
  for (let index = 0; index < 4; index += 1) {
    below.push(await createRequirement(page, `链接用例 下方 ${index}`));
  }
  const target = await createRequirement(page, '链接用例 目标');
  const above: Awaited<ReturnType<typeof createRequirement>>[] = [];
  for (let index = 0; index < 4; index += 1) {
    above.push(await createRequirement(page, `链接用例 上方 ${index}`));
  }

  try {
    await page.goto(target.path);

    const card = page
      .locator('.requirement-card')
      .filter({ hasText: '链接用例 目标' });
    await expect(card).toBeVisible();
    // The linked card is the one the pane opens on, not merely present.
    const paneBox = await page.locator('.detail-pane').boundingBox();
    const cardBox = await card.boundingBox();
    expect((cardBox?.y ?? 0) - (paneBox?.y ?? 0)).toBeLessThan(60);
    await expectSelected(page, '链接用例 目标');

    // The address bar keeps the link, so it can be copied from the browser.
    expect(new URL(page.url()).pathname).toBe(target.path);

    // The copy button carries the same link, on an address others can open.
    const shareUrl = await card
      .getByRole('button', { name: '链接用例 目标 复制链接' })
      .getAttribute('title');
    expect(shareUrl?.startsWith('http')).toBe(true);
    expect(shareUrl?.endsWith(target.path)).toBe(true);

    // Browsing on keeps the address bar truthful.
    await page
      .locator('.tree-item')
      .filter({ hasText: '链接用例 上方 0' })
      .click();
    await expect.poll(() => new URL(page.url()).pathname).toBe(above[0]?.path);
  } finally {
    await removeRequirements(page, [target, ...below, ...above]);
  }
});

test('keeps a linked requirement selected when the list cannot scroll', async ({
  page,
}) => {
  await unlockEditing(page);
  const target = await createRequirement(page, '链接用例 短列表');

  try {
    // A handful of short cards leave nothing to scroll, so the linked card can
    // never become the topmost one and the link has to select it itself.
    await page.goto(target.path);

    await expectSelected(page, '链接用例 短列表');
    expect(new URL(page.url()).pathname).toBe(target.path);
  } finally {
    await removeRequirements(page, [target]);
  }
});

test('reports a link whose requirement is gone', async ({ page }) => {
  await page.goto('/r/demo-project/deleted-requirement');

  await expect(page.getByRole('alert')).toContainText(
    '链接中的需求不存在，可能已被重命名或删除。',
  );
  await expect(page.locator('.requirement-card').first()).toBeVisible();
});
