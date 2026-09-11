import { describe, expect, it } from 'vitest';

import {
  createEmptyRequirementSnapshot,
  createRequirementMarkdown,
  parseHistoricalRequirementMarkdown,
  parseRequirementMarkdown,
  readHistoricalRequirementTimeline,
  requirementStatuses,
} from './index.js';

describe('createEmptyRequirementSnapshot', () => {
  it('provides the front-end requirement board with no persisted items', () => {
    expect(createEmptyRequirementSnapshot()).toEqual({
      statuses: requirementStatuses,
      items: [],
    });
  });
});

describe('parseHistoricalRequirementMarkdown', () => {
  it('renders only the requirement-detail table cell from a historical 需求文档', () => {
    const requirements = parseHistoricalRequirementMarkdown(
      `# 历史 需求文档

## 五、需求详情

### 5.1 编辑入口

| 维度 | 需求说明 |
| --- | --- |
| 用户与场景 | 不应显示。 |
| 需求入口 | 不应显示。 |
| 需求详情 | ![入口图](./assets/entry.png)<br>展示编辑入口。 |
| 设计与交互 | 不应显示。 |`,
      {
        idPrefix: 'legacy-table',
        updatedAt: '2026-09-10T10:00:00.000Z',
      },
    );

    expect(requirements[0]?.sections).toEqual([
      {
        title: '需求详情',
        description: '展示编辑入口。',
        images: [{ alt: '入口图', path: 'assets/entry.png' }],
      },
    ]);
  });

  it('keeps only independent requirements from the historical detail section', () => {
    const requirements = parseHistoricalRequirementMarkdown(
      `# 历史 需求文档

## 一、背景

不应显示。

## 五、需求详情

### 5.1 编辑入口

![入口图](./assets/entry.png)

展示编辑入口。<br>支持键盘操作。

### 5.2 保存反馈

<img src="./assets/saved.png" alt="保存反馈" />

保存后提示成功。

## 六、数据指标

不应显示。`,
      {
        idPrefix: 'legacy-editor',
        updatedAt: '2026-09-09T18:00:00.000Z',
      },
    );

    expect(requirements).toHaveLength(2);
    expect(requirements[0]).toMatchObject({
      id: 'legacy-editor-1',
      title: '编辑入口',
      status: 'defined',
      sections: [
        {
          title: '需求详情',
          description: '展示编辑入口。\n支持键盘操作。',
          images: [{ alt: '入口图', path: 'assets/entry.png' }],
        },
      ],
    });
    expect(requirements[1]?.sections[0]?.images).toEqual([
      { alt: '需求图示', path: 'assets/saved.png' },
    ]);
  });

  it('uses a sibling assets path for legacy placeholder images', () => {
    const requirements = parseHistoricalRequirementMarkdown(
      `# 历史 需求文档

## 五、需求详情

### 5.1 节点搜索清单

| 维度 | 需求说明 |
| --- | --- |
| 需求详情 | 展示节点列表。<br><br>占位图：节点搜索清单-状态.png |`,
      {
        idPrefix: 'legacy-placeholder',
        updatedAt: '2026-09-10T10:00:00.000Z',
      },
    );

    expect(requirements[0]).toMatchObject({
      title: '节点搜索清单',
      sections: [
        {
          description: '展示节点列表。',
          images: [
            {
              alt: '节点搜索清单-状态',
              path: 'assets/节点搜索清单-状态.png',
            },
          ],
        },
      ],
    });
  });
});

describe('readHistoricalRequirementTimeline', () => {
  it('uses the first and latest dates in the version record', () => {
    expect(
      readHistoricalRequirementTimeline(
        `# 示例需求 - 2026-07-09

### 2. 版本记录

| 版本 | 日期 | 变更内容 |
| --- | --- | --- |
| v0.1 | 2026-06-30 | 首次创建 |
| v0.2 | 2026-07-09 | 补充交互说明 |`,
        '2026-09-10T10:00:00.000Z',
      ),
    ).toEqual({
      createdAt: '2026-06-30T00:00:00.000Z',
      updatedAt: '2026-07-09T00:00:00.000Z',
    });
  });

  it('falls back to the document title date before the filesystem time', () => {
    expect(
      readHistoricalRequirementTimeline(
        '# 示例需求 - 2026-07-09',
        '2026-09-10T10:00:00.000Z',
      ),
    ).toEqual({
      createdAt: '2026-07-09T00:00:00.000Z',
      updatedAt: '2026-07-09T00:00:00.000Z',
    });
  });
});

describe('parseRequirementMarkdown', () => {
  it('preserves semantic visual groups without splitting by image count', () => {
    const markdown = createRequirementMarkdown({
      id: 'subtitle-removal',
      title: '字幕擦除',
      status: 'defined',
      createdAt: '2026-09-10T10:00:00.000Z',
      updatedAt: '2026-09-10T10:00:00.000Z',
      updatedAtTimestamp: 1_789_034_400_000,
      summary: '提供三种字幕处理交互。',
      sections: [
        {
          title: '工具入口',
          description: '显示处理入口。',
          images: [{ alt: '需求图示', path: 'assets/entry.png' }],
        },
        {
          title: '智能擦除',
          description: '确认后执行智能擦除。',
          images: [
            { alt: '需求图示', path: 'assets/smart.png' },
            { alt: '需求图示', path: 'assets/select.png' },
          ],
        },
      ],
    });

    expect(parseRequirementMarkdown(markdown).sections).toHaveLength(2);
    expect(
      parseRequirementMarkdown(markdown).sections.map(
        (section) => section.title,
      ),
    ).toEqual(['工具入口', '智能擦除']);
    expect(parseRequirementMarkdown(markdown).sections[1]?.images).toHaveLength(
      2,
    );
  });

  it('parses requirement metadata, text-only sections, and image sections', () => {
    const document = parseRequirementMarkdown(`---
id: profile-editor
title: 个人资料编辑
status: defined
updatedAt: 2026-09-09T18:00:00+08:00
summary: 编辑个人资料。
---

## 基础信息

用户可以修改昵称。

## 编辑态

![编辑表单](assets/profile-editor.png)

保存前校验昵称。`);

    expect(document).toMatchObject({
      id: 'profile-editor',
      title: '个人资料编辑',
      status: 'defined',
      summary: '编辑个人资料。',
    });
    expect(document.sections).toEqual([
      { title: '基础信息', description: '用户可以修改昵称。', images: [] },
      {
        title: '编辑态',
        description: '保存前校验昵称。',
        images: [{ alt: '编辑表单', path: 'assets/profile-editor.png' }],
      },
    ]);
  });

  it('keeps body content on the top-level requirement without subheadings', () => {
    const document = parseRequirementMarkdown(`---
id: profile-editor
title: 个人资料编辑
status: defined
updatedAt: 2026-09-10T10:30:00+08:00
summary: 编辑个人资料。
---

用户可以修改昵称。

![编辑表单](assets/profile-editor.png)`);

    expect(document.sections).toEqual([
      {
        title: '',
        description: '用户可以修改昵称。',
        images: [{ alt: '编辑表单', path: 'assets/profile-editor.png' }],
      },
    ]);
  });

  it('keeps top-level content when visual groups are added', () => {
    const document = parseRequirementMarkdown(`---
id: profile-editor
title: 个人资料编辑
status: defined
updatedAt: 2026-09-10T10:30:00+08:00
summary: 编辑个人资料。
---

顶部说明。

![顶部图示](assets/top-level.png)

## 图示 1

![二级图示](assets/second-level.png)`);

    expect(document.sections).toEqual([
      {
        title: '',
        description: '顶部说明。',
        images: [{ alt: '顶部图示', path: 'assets/top-level.png' }],
      },
      {
        title: '图示 1',
        description: '',
        images: [{ alt: '二级图示', path: 'assets/second-level.png' }],
      },
    ]);
  });

  it('rejects documents without the required front matter', () => {
    expect(() => parseRequirementMarkdown('# Missing metadata')).toThrow(
      'Requirement Markdown must start with front matter.',
    );
  });
});
