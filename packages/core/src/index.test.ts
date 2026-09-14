import { describe, expect, it } from 'vitest';

import {
  createEmptyRequirementSnapshot,
  createRequirementMarkdown,
  normalizeRequirementDescription,
  parseRequirementMarkdown,
  requirementStatuses,
} from './index.js';

describe('normalizeRequirementDescription', () => {
  it('restores structure from legacy continuous numbering', () => {
    expect(
      normalizeRequirementDescription(
        '一、入口、展示与检索1.入口与任务队列可见。2.支持实时筛选。',
      ),
    ).toBe(
      '### 一、入口、展示与检索\n\n1. 入口与任务队列可见。\n2. 支持实时筛选。',
    );
  });
});

describe('createEmptyRequirementSnapshot', () => {
  it('provides the front-end requirement board with no persisted items', () => {
    expect(createEmptyRequirementSnapshot()).toEqual({
      statuses: requirementStatuses,
      items: [],
    });
  });
});

describe('parseRequirementMarkdown', () => {
  it('serializes front matter safely and rejects multiline metadata', () => {
    const document = {
      id: 'quoted-title',
      title: '标题: "含引号"',
      status: 'defined' as const,
      createdAt: '2026-09-10T10:00:00.000Z',
      updatedAt: '2026-09-10T10:00:00.000Z',
      updatedAtTimestamp: 1_789_034_400_000,
      sections: [{ title: '', description: '正文。', images: [] }],
    };
    expect(
      parseRequirementMarkdown(createRequirementMarkdown(document)),
    ).toMatchObject({
      title: document.title,
    });
    expect(() =>
      createRequirementMarkdown({ ...document, title: '第一行\n第二行' }),
    ).toThrow('single-line');
  });

  it('uses image filenames when image alt text is generic', () => {
    const document = parseRequirementMarkdown(
      '---\nid: image-names\ntitle: 图片名称\nstatus: defined\ncreatedAt: 2026-09-10T10:00:00.000Z\nupdatedAt: 2026-09-10T10:00:00.000Z\n---\n\n![需求图示](assets/节点搜索清单.png)',
    );

    expect(document.sections[0]?.images).toEqual([
      { alt: '节点搜索清单', path: 'assets/节点搜索清单.png' },
    ]);
  });

  it('preserves semantic visual groups without splitting by image count', () => {
    const markdown = createRequirementMarkdown({
      id: 'subtitle-removal',
      title: '字幕擦除',
      status: 'defined',
      createdAt: '2026-09-10T10:00:00.000Z',
      updatedAt: '2026-09-10T10:00:00.000Z',
      updatedAtTimestamp: 1_789_034_400_000,
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
