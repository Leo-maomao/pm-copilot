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
