import { expect, type Page, test } from '@playwright/test';

/** The tree follows the detail pane, so it needs the same edit session. */
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

/** A body long enough that one card fills the pane on its own. */
async function createTallRequirement(
  page: Page,
  title: string,
): Promise<string> {
  const response = await page.request.post('/api/requirements', {
    data: { projectName: 'demo-project', title },
  });
  expect(response.status()).toBe(201);
  const { created: record } = await response.json();
  const assetKey = `${record.projectName}:${record.id}`;
  const updated = await page.request.put(
    `/api/requirements/${encodeURIComponent(assetKey)}`,
    {
      data: {
        sections: [{ description: `## 说明\n\n${'正文段落。'.repeat(120)}` }],
      },
    },
  );
  expect(updated.ok()).toBeTruthy();
  return assetKey;
}

/** Aligns a card with the top of the pane, as a manual scroll would. */
async function scrollCardToPaneTop(page: Page, index: number): Promise<void> {
  await page.locator('.detail-pane').evaluate((pane, cardIndex) => {
    const card = pane.querySelectorAll<HTMLElement>('[data-requirement-key]')[
      cardIndex
    ];
    if (!card) throw new Error('Missing card.');
    pane.scrollTo({
      top:
        pane.scrollTop +
        card.getBoundingClientRect().top -
        pane.getBoundingClientRect().top,
    });
  }, index);
}

test('selects the tree entry of the requirement scrolled to in the pane', async ({
  page,
}) => {
  await unlockEditing(page);
  const assetKeys: string[] = [];
  for (const title of ['目录联动 A', '目录联动 B', '目录联动 C']) {
    assetKeys.push(await createTallRequirement(page, title));
  }

  try {
    // A plain reload would land on the link the address bar kept, so open the
    // manager at its root to start the pane at the top.
    await page.goto('/');
    const activeTitle = page.locator(
      '.tree-item[aria-current="true"] .tree-item-title',
    );
    // The tree and the pane sort the same way, so both list the same order.
    const cardTitles = await page
      .locator('.requirement-card h2')
      .allTextContents();
    expect(
      await page.locator('.tree-item .tree-item-title').allTextContents(),
    ).toEqual(cardTitles);
    expect(cardTitles.length).toBeGreaterThanOrEqual(3);

    // Sitting at the top, the pane reads as the first requirement.
    await expect(activeTitle).toHaveText(cardTitles[0] ?? '');

    await scrollCardToPaneTop(page, 1);
    await expect(activeTitle).toHaveText(cardTitles[1] ?? '');

    await scrollCardToPaneTop(page, 2);
    await expect(activeTitle).toHaveText(cardTitles[2] ?? '');

    await page
      .locator('.detail-pane')
      .evaluate((pane) => pane.scrollTo({ top: 0 }));
    await expect(activeTitle).toHaveText(cardTitles[0] ?? '');

    // A tree click parks the card 32px below the pane top, inside the offset the
    // highlight line allows for it.
    await page
      .locator('.tree-item')
      .filter({ hasText: cardTitles[1] ?? '' })
      .click();
    await expect(activeTitle).toHaveText(cardTitles[1] ?? '');

    // Only ever one entry is selected.
    await expect(page.locator('.tree-item[aria-current="true"]')).toHaveCount(
      1,
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
