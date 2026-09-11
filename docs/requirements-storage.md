# 统一需求库规范

产品助理仓库是需求的唯一存储位置。`requirements/` 是本机私有数据，必须被 Git 忽略；目标代码仓库只作为插件读取和验证的来源。

```text
requirements/
  inbox/
    <draft-id>/
      draft.json
      assets/
  projects/
    <project-key>/
      requirements/
        <requirement-id>/
          requirement.md
          assets/
  .migration/records/
```

`inbox` 仅保存口语标题和人工图示草稿，不是正式需求。插件完成正式化时按口语标题匹配草稿，移动图示到对应项目目录。多个候选或图示归属不清时必须询问。

## 正式需求

每份 `requirement.md` 使用以下 front matter：

```md
---
id: profile-editor-a1b2c3d4
title: 个人资料编辑
status: defined
createdAt: 2026-09-10T10:00:00.000Z
updatedAt: 2026-09-10T10:00:00.000Z
summary: 用户可编辑昵称、头像和个人简介。
---

## 基础信息

![编辑表单](assets/edit-form.png)

用户可直接编辑昵称和简介，保存前完成校验。
```

- `id` 是稳定 kebab-case 标识；目录名与其一致。
- `project-key` 优先来自 Git `origin`，没有远端时回退当前目录名。
- `status` 只能是 `planning`、`defined`、`scheduled` 或 `completed`。
- `createdAt` 创建后不变；任何写入都更新 `updatedAt`。
- 没有二级标题时，正文和图示属于一级需求；有二级标题时，图示必须属于同一二级内容。
- 二级内容按实现边界、交互目标和状态链划分，不按图片数量划分。每张图必须归属一个明确内容；同一内容可包含多张状态图，不同内容不能合并为连续图文。
- 图片始终在同目录 `assets/`，Markdown 只使用相对路径。

管理器只渲染正文和图示；文件名不在阅读页展示。

## 历史需求时间

历史来源保留只读。服务每次启动会重新扫描其中的 `prd.md`，仅校准已迁移需求的 `createdAt` 与 `updatedAt`，不会覆盖本地状态、标题、正文或图示调整。

- 优先使用“版本记录”表的日期列：最早日期为创建时间，最晚日期为更新时间。
- 没有版本记录时，使用文档一级标题中记录的日期。
- 两者都缺失时，才回退为历史文件的修改时间。
