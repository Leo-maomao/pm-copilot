import { expect, test } from '@playwright/test';

test('renders the centralized requirement manager shell', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle('需求管理器');
  const response = await page.request.get('/api/index');
  await expect(response).toBeOK();
  const payload = await response.json();
  expect(payload.canEdit).toEqual(expect.any(Boolean));
  expect(JSON.stringify(payload)).not.toContain('assetDirectory');
  await expect(page.locator('.navigator-heading')).toBeVisible();
  await expect(page.getByRole('button', { name: '刷新扫描' })).toBeVisible();
  await expect(page.getByLabel('搜索需求')).toBeVisible();
  await expect(page.getByTitle('进入编辑状态').first()).toBeVisible();
  await expect(page.getByTitle('新建需求')).toHaveCount(0);
  await expect(page.getByRole('button', { name: '新增项目' })).toHaveCount(0);
  await page.locator('.navigator-heading').click();
  await page.getByLabel('第 1 位编辑口令').fill('9');
  await page.getByLabel('第 2 位编辑口令').fill('5');
  await page.getByLabel('第 3 位编辑口令').fill('2');
  await page.getByLabel('第 4 位编辑口令').fill('7');
  await expect(page.getByRole('dialog', { name: '进入编辑状态' })).toHaveCount(
    0,
  );
  await expect(page.getByRole('button', { name: '选择项目目录' })).toHaveCount(
    0,
  );
  await expect(page.getByTitle('更多操作').first()).toBeVisible();
  await page.getByTitle('更多操作').first().click();
  await expect(page.getByTitle('新建需求').first()).toBeVisible();
  await page.getByTitle('删除项目').first().click();
  await expect(page.getByRole('dialog', { name: '删除项目' })).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: '删除项目' })).toHaveCount(0);
  await expect(page.getByRole('button', { name: '新增项目' })).toBeVisible();
  await page.getByRole('button', { name: '新增项目' }).click();
  await expect(page.getByRole('dialog', { name: '新增项目' })).toBeVisible();
  await expect(page.getByLabel('项目名称')).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog', { name: '新增项目' })).toHaveCount(0);
  await page.keyboard.press('Meta+f');
  await expect(page.getByLabel('搜索需求')).toBeFocused();
  await page.getByLabel('搜索需求').fill('不存在的需求');
  await expect(page.getByLabel('搜索结果')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.getByLabel('搜索结果')).toHaveCount(0);
  await page.getByLabel('搜索需求').fill('仅限元数据的搜索词');
  await expect(page.getByLabel('搜索结果')).toHaveCount(0);
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: '收起目录' }).click();
  await expect(page.locator('.manager-shell')).toHaveClass(
    /navigator-collapsed/,
  );
});

test('shows only the selected project requirements in the detail pane', async ({
  page,
}) => {
  await page.goto('/');
  const payload = await (await page.request.get('/api/index')).json();
  const project = payload.projects.find(
    (candidate) => candidate.requirements.length > 0,
  );
  if (!project) return;

  await page
    .locator('.tree-project summary')
    .filter({ hasText: project.projectName })
    .click();
  await expect(page.locator('.requirement-card')).toHaveCount(
    project.requirements.length,
  );
});

test('keeps the selected project after a page refresh', async ({ page }) => {
  await page.goto('/');
  const payload = await (await page.request.get('/api/index')).json();
  const project = payload.projects.find(
    (candidate) => candidate.requirements.length > 0,
  );
  if (!project) return;

  const summary = page
    .locator('.tree-project summary')
    .filter({ hasText: project.projectName });
  await summary.click();
  await expect(page.locator('.tree-project--active summary > span')).toHaveText(
    project.projectName,
  );

  await page.reload();
  await expect(page.locator('.tree-project--active summary > span')).toHaveText(
    project.projectName,
  );
});

test('keeps the project action entry visible after collapsing a project', async ({
  page,
}) => {
  await page.goto('/');
  const project = page.locator('.tree-project').first();
  await project.locator('summary').click();

  await expect(project.locator('details')).not.toHaveAttribute('open', '');
  await expect(project.locator('.tree-project-more')).toBeVisible();
});

test('keeps status, search and directory order consistent after refresh', async ({
  page,
}) => {
  await page.goto('/');
  await page.locator('.navigator-heading').click();
  for (const [index, digit] of ['9', '5', '2', '7'].entries()) {
    await page.getByLabel(`第 ${index + 1} 位编辑口令`).fill(digit);
  }
  await expect(page.getByRole('dialog', { name: '进入编辑状态' })).toHaveCount(
    0,
  );

  const keys: string[] = [];
  try {
    for (const title of ['状态同步验证 A', '状态同步验证 B']) {
      const response = await page.request.post('/api/requirements', {
        data: { projectName: 'demo-project', title },
      });
      expect(response.status()).toBe(201);
      const { created } = await response.json();
      keys.push(`${created.projectName}:${created.id}`);
    }
    await page.goto('/');
    await expect(
      page.getByRole('heading', { name: '状态同步验证 B', exact: true }),
    ).toBeVisible();
    const titles = await page.locator('.requirement-card h2').allTextContents();
    expect(await page.locator('.tree-item-title').allTextContents()).toEqual(
      titles,
    );

    const card = page.locator('.requirement-card').filter({
      has: page.getByRole('heading', { name: '状态同步验证 A', exact: true }),
    });
    const treeItem = page.locator('.tree-item').filter({
      has: page.getByText('状态同步验证 A', { exact: true }),
    });
    await card.getByRole('button', { name: '已排期', exact: true }).click();
    await expect(treeItem.locator('.tree-status')).toHaveText('已排期');
    await expect(card.getByRole('button', { name: '已排期' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );
    expect(
      await page.locator('.requirement-card h2').allTextContents(),
    ).toEqual(titles);

    await page.getByLabel('筛选状态', { exact: true }).click();
    await page.getByRole('menuitemradio', { name: '已排期' }).click();
    await expect(page.locator('.requirement-card h2')).toHaveText([
      '状态同步验证 A',
    ]);
    await page.getByLabel('搜索需求', { exact: true }).fill('状态同步验证 B');
    await expect(page.getByLabel('搜索结果')).toContainText('待规划');
    await page.getByLabel('搜索结果').getByRole('button').click();
    await expect(page.getByLabel('搜索需求', { exact: true })).toHaveValue('');
    await expect(page.getByLabel('筛选状态', { exact: true })).toHaveText(
      '全部',
    );
    await expect(page.locator('.requirement-card h2')).toHaveText(titles);

    await page.getByLabel('搜索需求', { exact: true }).fill('状态同步验证 A');
    await expect(page.getByLabel('搜索结果')).toContainText('已排期');
    await page.getByLabel('筛选状态', { exact: true }).click();
    await page.getByRole('menuitemradio', { name: '已排期' }).click();
    await expect(page.getByLabel('搜索需求', { exact: true })).toHaveValue(
      '状态同步验证 A',
    );
    await expect
      .poll(() =>
        page.evaluate(() => {
          const stored = JSON.parse(
            sessionStorage.getItem('pm-copilot:view') ?? '{}',
          );
          return { query: stored.query, statusFilter: stored.statusFilter };
        }),
      )
      .toEqual({ query: '状态同步验证 A', statusFilter: 'scheduled' });
    await page.reload();
    await expect(page.getByLabel('搜索需求', { exact: true })).toHaveValue(
      '状态同步验证 A',
    );
    await expect(page.getByLabel('筛选状态', { exact: true })).toHaveText(
      '已排期',
    );
    await expect(page.locator('.requirement-card h2')).toHaveText([
      '状态同步验证 A',
    ]);
    await expect(treeItem.locator('.tree-status')).toHaveText('已排期');
  } finally {
    for (const key of keys) {
      const removed = await page.request.delete(
        `/api/requirements/${encodeURIComponent(key)}`,
      );
      expect(removed.ok()).toBeTruthy();
    }
  }
});
