import { describe, expect, it } from 'vitest';

import {
  createEmptyRequirementSnapshot,
  createRequirementClipboardMarkdown,
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
      '### 一、入口、展示与检索\n1. 入口与任务队列可见。\n2. 支持实时筛选。',
    );
  });

  it('keeps a heading on its own line and separates it from the block above', () => {
    expect(
      normalizeRequirementDescription(
        '### 一、素材识别\n\n1. 类型标识可见。\n2. 名称可见。\n### 二、卡片操作\n\n1. 卡片可预览。',
      ),
    ).toBe(
      '### 一、素材识别\n1. 类型标识可见。\n2. 名称可见。\n\n### 二、卡片操作\n1. 卡片可预览。',
    );
  });

  it('collapses the blank lines that would render a loose ordered list', () => {
    expect(
      normalizeRequirementDescription(
        '### 一、列表\n\n1. 第一条。\n\n\n2. 第二条。\n\n3. 第三条。',
      ),
    ).toBe('### 一、列表\n1. 第一条。\n2. 第二条。\n3. 第三条。');
  });

  it('keeps exactly one blank line between prose blocks', () => {
    expect(normalizeRequirementDescription('第一段。\n\n\n\n第二段。')).toBe(
      '第一段。\n\n第二段。',
    );
  });

  it('restarts ordered items under every heading', () => {
    expect(
      normalizeRequirementDescription(
        '### 一、核心内容\n1. 查看类型与关键信息。\n### 二、状态与边界\n2. 可添加到画布。\n### 三、反馈与恢复\n3. 保留原因提示。',
      ),
    ).toBe(
      '### 一、核心内容\n1. 查看类型与关键信息。\n\n### 二、状态与边界\n1. 可添加到画布。\n\n### 三、反馈与恢复\n1. 保留原因提示。',
    );
  });

  it('is stable when it runs again', () => {
    const once = normalizeRequirementDescription(
      '一、范围\n\n1. 第一项。\n### 二、状态\n\n1. 第二项。',
    );
    expect(normalizeRequirementDescription(once)).toBe(once);
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

describe('createRequirementClipboardMarkdown', () => {
  it('copies only the title and section text without metadata or image paths', () => {
    const markdown = createRequirementClipboardMarkdown({
      id: 'clipboard-copy',
      title: '可复制需求',
      status: 'defined',
      createdAt: '2026-09-10T10:00:00.000Z',
      updatedAt: '2026-09-10T10:00:00.000Z',
      updatedAtTimestamp: 1_789_034_400_000,
      sections: [
        {
          title: '需求说明',
          description: '一、需求说明\n\n开发时保留这个行为。',
          images: [{ alt: '参考图', path: 'assets/reference.png' }],
        },
      ],
    });

    expect(markdown).toBe(
      '# 可复制需求\n\n### 一、需求说明\n\n开发时保留这个行为。\n',
    );
    expect(markdown).toContain('开发时保留这个行为。');
    expect(markdown).not.toContain('assets/reference.png');
    expect(markdown).not.toContain('![参考图]');
    expect(markdown).not.toContain('id:');
    expect(markdown).not.toContain('status:');
    expect(markdown).not.toContain('## 需求说明');
  });
});

describe('createRequirementMarkdown', () => {
  it('separates every block with exactly one blank line', () => {
    const markdown = createRequirementMarkdown({
      id: 'file-shape',
      title: '文件形态',
      status: 'defined',
      createdAt: '2026-09-10T10:00:00.000Z',
      updatedAt: '2026-09-10T10:00:00.000Z',
      updatedAtTimestamp: 1_789_034_400_000,
      sections: [
        {
          title: '素材识别',
          description: '### 一、素材识别\n1. 类型标识可见。',
          images: [{ alt: '卡片', path: 'assets/card.png' }],
        },
        {
          title: '卡片操作',
          description: '### 一、卡片操作\n1. 卡片可预览。',
          images: [],
        },
      ],
    });

    expect(markdown).toBe(
      '---\nid: "file-shape"\ntitle: "文件形态"\nstatus: "defined"\ncreatedAt: "2026-09-10T10:00:00.000Z"\nupdatedAt: "2026-09-10T10:00:00.000Z"\n---\n\n## 素材识别\n\n![卡片](assets/card.png)\n\n### 一、素材识别\n1. 类型标识可见。\n\n## 卡片操作\n\n### 一、卡片操作\n1. 卡片可预览。\n',
    );
    expect(markdown).not.toMatch(/\n{3,}/);
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
