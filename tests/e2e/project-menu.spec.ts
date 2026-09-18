import { expect, type Page, test } from '@playwright/test';

const menuEntries = ['新建需求', '重命名', '删除项目'];

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

async function readAssetKeys(page: Page): Promise<readonly string[]> {
  const payload = await (await page.request.get('/api/index')).json();
  return payload.projects.flatMap(
    (project: { requirements: { assetKey: string }[] }) =>
      project.requirements.map((requirement) => requirement.assetKey),
  );
}

/** The tree body clips its own overflow, so a menu sticking out of it loses an
 * entry. A ratio of 1 means every pixel of the entry is on screen. */
async function expectMenuFullyVisible(page: Page): Promise<void> {
  for (const name of menuEntries) {
    await expect(page.getByRole('menuitem', { name })).toBeInViewport({
      ratio: 1,
    });
  }
}

test('keeps every project action in view at the top of the tree', async ({
  page,
}) => {
  await unlockEditing(page);
  await page.reload();
  const knownKeys = await readAssetKeys(page);

  try {
    // The project sits against the top of the tree, which is where a menu
    // opening upwards used to disappear behind the scroll container's edge.
    const project = page.locator('.tree-project').first();
    await project.locator('.tree-project-more').click();
    await expectMenuFullyVisible(page);

    // The first entry has to stay reachable, not just painted.
    await page.getByRole('menuitem', { name: '新建需求' }).click();
    const editor = page.getByRole('dialog', { name: '编辑图示' });
    await expect(editor).toBeVisible();
    await editor.getByLabel('关闭编辑图示').click();
    await expect(editor).toHaveCount(0);
    await expect(
      page.locator('.tree-item-title').filter({ hasText: '未命名需求' }),
    ).toHaveCount(1);
  } finally {
    for (const assetKey of await readAssetKeys(page)) {
      if (knownKeys.includes(assetKey)) continue;
      const removed = await page.request.delete(
        `/api/requirements/${encodeURIComponent(assetKey)}`,
      );
      expect(removed.ok()).toBeTruthy();
    }
  }
});

test('opens a low project action menu above its row', async ({ page }) => {
  await unlockEditing(page);
  const fillerKeys = await readAssetKeys(page);

  try {
    // A tree taller than the navigator, so its last project can be scrolled to
    // the bottom edge where a menu opening downwards would be cut off.
    for (let index = 0; index < 14; index += 1) {
      const response = await page.request.post('/api/requirements', {
        data: { projectName: 'demo-project', title: `菜单撑高用例 ${index}` },
      });
      expect(response.status()).toBe(201);
    }
    const projectResponse = await page.request.post('/api/projects', {
      data: { projectName: 'menu-bottom-project' },
    });
    expect(projectResponse.ok()).toBeTruthy();

    await page.reload();
    const lastProject = page
      .locator('.tree-project')
      .filter({ hasText: 'menu-bottom-project' });
    const tree = page.locator('.tree-groups');
    await tree.evaluate((element) =>
      element.scrollTo({ top: element.scrollHeight }),
    );
    await expect(lastProject.locator('summary')).toBeVisible();

    await lastProject.locator('.tree-project-more').click();
    await expectMenuFullyVisible(page);

    // Anchored above the row it belongs to, not dropped off the bottom.
    const rowBox = await lastProject
      .locator('.tree-project-actions')
      .boundingBox();
    const menuBox = await lastProject
      .locator('.tree-project-action-menu')
      .boundingBox();
    expect(menuBox?.y ?? 0).toBeLessThan(rowBox?.y ?? 0);
  } finally {
    const removed = await page.request.delete(
      '/api/projects/menu-bottom-project',
    );
    expect(removed.ok()).toBeTruthy();
    for (const assetKey of await readAssetKeys(page)) {
      if (fillerKeys.includes(assetKey)) continue;
      const cleanup = await page.request.delete(
        `/api/requirements/${encodeURIComponent(assetKey)}`,
      );
      expect(cleanup.ok()).toBeTruthy();
    }
  }
});

test('paints the project menu above the row it covers', async ({ page }) => {
  await unlockEditing(page);
  const knownKeys = await readAssetKeys(page);
  const response = await page.request.post('/api/projects', {
    data: { projectName: 'menu-overlap-project' },
  });
  expect(response.ok()).toBeTruthy();

  try {
    await page.reload();
    // Collapsing the first project puts the second one's `...` button directly
    // under the menu the first one opens.
    const firstProject = page
      .locator('.tree-project')
      .filter({ hasText: 'demo-project' });
    await firstProject.locator('summary').click();
    await firstProject.locator('.tree-project-more').click();
    await expectMenuFullyVisible(page);

    const covered = page
      .locator('.tree-project')
      .filter({ hasText: 'menu-overlap-project' })
      .locator('.tree-project-more');
    const coveredBox = await covered.boundingBox();
    const menuBox = await firstProject
      .locator('.tree-project-action-menu')
      .boundingBox();
    expect(coveredBox).not.toBeNull();
    expect(menuBox).not.toBeNull();
    // Without an overlap this test would prove nothing.
    expect(menuBox?.y ?? 0).toBeLessThan(coveredBox?.y ?? 0);

    // Its own stacking box would otherwise paint the button over the menu, and
    // hit testing follows paint order.
    const hitIsMenu = await page.evaluate(
      ([x, y]) =>
        document
          .elementFromPoint(x ?? 0, y ?? 0)
          ?.closest('.tree-project-action-menu') !== null,
      [
        (coveredBox?.x ?? 0) + (coveredBox?.width ?? 0) / 2,
        (coveredBox?.y ?? 0) + (coveredBox?.height ?? 0) / 2,
      ],
    );
    expect(hitIsMenu).toBe(true);
  } finally {
    const removed = await page.request.delete(
      '/api/projects/menu-overlap-project',
    );
    expect(removed.ok()).toBeTruthy();
    for (const assetKey of await readAssetKeys(page)) {
      if (knownKeys.includes(assetKey)) continue;
      const cleanup = await page.request.delete(
        `/api/requirements/${encodeURIComponent(assetKey)}`,
      );
      expect(cleanup.ok()).toBeTruthy();
    }
  }
});
