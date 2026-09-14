# 统一需求库规范

产品助理仓库是需求的唯一存储位置。`requirements/` 是本机私有数据，必须被 Git 忽略；目标代码仓库只作为插件读取和验证的来源。

```text
requirements/
  <project-key>/
    <requirement-id>/
      requirement.md
      assets/
```

## 正式需求

正文必须使用 Markdown 结构保存，不把多个编号事项连续写在同一行。推荐使用中文序号作为主题、阿拉伯数字作为事项：

```md
### 一、入口、展示与检索

1. 入口与任务队列可见。
2. 支持实时筛选。
3. 列表内容按规则排序。
```

每份 `requirement.md` 使用以下 front matter：

```md
---
id: profile-editor-a1b2c3d4
title: 个人资料编辑
status: defined
createdAt: 2026-09-10T10:00:00.000Z
updatedAt: 2026-09-10T10:00:00.000Z
---

## 基础信息

![编辑表单](assets/edit-form.png)

用户可直接编辑昵称和简介，保存前完成校验。
```

- `id` 是稳定 kebab-case 标识；目录名与其一致。
- `project-key` 优先来自 Git `origin`，没有远端时回退当前目录名。
- `status` 只能是 `planning`、`defined`、`scheduled` 或 `completed`。
- `createdAt` 与 `updatedAt` 都只在创建时写入。`updatedAt` 是需求目录的排序依据和卡片日期，任何编辑（状态、标题、正文、图示）都不改写它。
- 没有二级标题时，正文和图示属于一级需求；有二级标题时，图示必须属于同一二级内容。
- 二级内容按实现边界、交互目标和状态链划分，不按图片数量划分。每张图必须归属一个明确内容；同一内容可包含多张状态图，不同内容不能合并为连续图文。
- 图片始终在同目录 `assets/`，Markdown 只使用相对路径。

管理器只渲染正文和图示；文件名不在阅读页展示。
