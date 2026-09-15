import { expect, type Page, test } from '@playwright/test';

/**
 * Pasting into a visual group used to fire the dialog handler and the tile
 * handler, uploading the same image twice and leaving an orphan file behind.
 */
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

async function pasteIntoPasteTarget(page: Page): Promise<void> {
  await page.evaluate(() => {
    const tile = document.querySelector('.paste-visual-tile');
    if (!tile) throw new Error('paste tile is missing');
    const base64 =
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==';
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    const transfer = new DataTransfer();
    transfer.items.add(
      new File([bytes], 'paste-probe.png', { type: 'image/png' }),
    );
    tile.dispatchEvent(
      new ClipboardEvent('paste', {
        bubbles: true,
        cancelable: true,
        clipboardData: transfer,
      }),
    );
  });
}

test('uploads a pasted image exactly once', async ({ page }) => {
  await unlockEditing(page);

  const created = await page.request.post('/api/requirements', {
    data: { projectName: 'demo-project', title: '粘贴用例' },
  });
  expect(created.status()).toBe(201);
  const { created: record } = await created.json();
  const assetKey = `${record.projectName}:${record.id}`;

  try {
    const uploads: string[] = [];
    page.on('request', (request) => {
      if (request.method() === 'POST' && request.url().endsWith('/visuals')) {
        uploads.push(request.url());
      }
    });

    await page.reload();
    const card = page
      .locator('.requirement-card')
      .filter({ hasText: '粘贴用例' });
    await card.locator('.add-visual').dispatchEvent('click');
    const dialog = page.getByRole('dialog', { name: '编辑图示' });
    await expect(dialog).toBeVisible();
    await dialog.getByLabel('向此图示层粘贴图片').first().click();

    await pasteIntoPasteTarget(page);
    await expect
      .poll(async () => {
        const payload = await (await page.request.get('/api/index')).json();
        return payload.projects
          .flatMap(
            (project: { requirements: readonly unknown[] }) =>
              project.requirements,
          )
          .find(
            (requirement: { assetKey: string }) =>
              requirement.assetKey === assetKey,
          )
          .document.sections.reduce(
            (total: number, section: { images: readonly unknown[] }) =>
              total + section.images.length,
            0,
          );
      })
      .toBe(1);

    expect(uploads).toHaveLength(1);
  } finally {
    const removed = await page.request.delete(
      `/api/requirements/${encodeURIComponent(assetKey)}`,
    );
    expect(removed.ok()).toBeTruthy();
  }
});
