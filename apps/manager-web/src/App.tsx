import {
  type RequirementImage,
  type RequirementStatus,
  requirementStatuses,
} from '@pm-copilot/core';
import DOMPurify from 'dompurify';
import {
  ChevronDown,
  ClipboardPaste,
  Ellipsis,
  ImagePlus,
  ListFilter,
  Maximize2,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { marked } from 'marked';
import { useEffect, useMemo, useRef, useState } from 'react';

import {
  addRequirementVisual,
  createProject,
  createRequirement,
  deleteProject,
  deleteRequirementVisual,
  type LoadedRequirement,
  type ProjectRequirements,
  readImageUrl,
  refreshProjectCollection,
  renameProject,
  scanProjectCollection,
  unlockEditor,
  updateRequirementStatus,
  updateRequirementTitle,
  updateVisualGroups,
  updateVisualOrder,
} from './requirement-source.js';

type DisplayRequirement = Readonly<{
  projectName: string;
  requirement: LoadedRequirement;
  status: RequirementStatus;
}>;

type PreviewImage = Readonly<{
  alt: string;
  src: string;
}>;

type PersistedManagerView = Readonly<{
  activeProjectName: string | undefined;
  collapsedProjects: Readonly<Record<string, boolean>>;
  detailScrollTop: number;
  isNavigatorCollapsed: boolean;
  query: string;
  statusFilter: RequirementStatus | 'all';
  treeScrollTop: number;
}>;

const managerViewStorageKey = 'pm-copilot:view';
const editorDigitPositions = [
  { id: 'one', position: 0 },
  { id: 'two', position: 1 },
  { id: 'three', position: 2 },
  { id: 'four', position: 3 },
] as const;

function readPersistedManagerView(): PersistedManagerView {
  const fallback: PersistedManagerView = {
    activeProjectName: undefined,
    collapsedProjects: {},
    detailScrollTop: 0,
    isNavigatorCollapsed: false,
    query: '',
    statusFilter: 'all',
    treeScrollTop: 0,
  };
  try {
    const saved = sessionStorage.getItem(managerViewStorageKey);
    if (!saved) return fallback;
    const value = JSON.parse(saved) as Partial<PersistedManagerView>;
    const statusFilter = value.statusFilter;
    return {
      activeProjectName:
        typeof value.activeProjectName === 'string'
          ? value.activeProjectName
          : undefined,
      collapsedProjects: value.collapsedProjects ?? {},
      detailScrollTop: value.detailScrollTop ?? 0,
      isNavigatorCollapsed: value.isNavigatorCollapsed === true,
      query: value.query ?? '',
      statusFilter:
        statusFilter === 'all' ||
        requirementStatuses.some((status) => status.id === statusFilter)
          ? (statusFilter ?? 'all')
          : 'all',
      treeScrollTop: value.treeScrollTop ?? 0,
    };
  } catch {
    return fallback;
  }
}

function persistManagerView(update: Partial<PersistedManagerView>): void {
  const current = readPersistedManagerView();
  try {
    sessionStorage.setItem(
      managerViewStorageKey,
      JSON.stringify({ ...current, ...update }),
    );
  } catch {
    // A disabled browser storage should not prevent the manager from working.
  }
}

function getRequirementKey(projectName: string, requirementId: string): string {
  return `${projectName}:${requirementId}`;
}

function getStatusLabel(status: RequirementStatus): string {
  return (
    requirementStatuses.find((definition) => definition.id === status)?.label ??
    status
  );
}

function normalizeRequirementMarkdown(markdown: string): string {
  // Historical requirements sometimes place the list marker and its content on separate lines.
  // Join only that form so Marked can restore the intended ordered-list structure.
  return markdown.replace(
    /(^|\n)([ \t]*)(\d+[.)])(?:[ \t]*\n)+[ \t]*/gu,
    '$1$2$3 ',
  );
}

function findDisplayRequirement(
  projects: readonly ProjectRequirements[],
  target: DisplayRequirement,
): DisplayRequirement {
  const requirement = projects
    .find((project) => project.projectName === target.projectName)
    ?.requirements.find(
      (item) => item.assetKey === target.requirement.assetKey,
    );
  if (!requirement) throw new Error('Updated requirement was not returned.');
  return { ...target, requirement };
}

function matchesRequirement(
  item: DisplayRequirement,
  normalizedQuery: string,
): boolean {
  if (!normalizedQuery) return false;
  const { document } = item.requirement;
  return [
    document.title,
    document.summary,
    ...document.sections.map((section) => section.description),
  ]
    .join('\n')
    .toLocaleLowerCase()
    .includes(normalizedQuery);
}

function RequirementTreeItem({
  item,
  onNavigate,
}: {
  item: DisplayRequirement;
  onNavigate: (item: DisplayRequirement) => void;
}): React.JSX.Element {
  return (
    <button
      className="tree-item"
      onClick={() => onNavigate(item)}
      type="button"
    >
      <span className="tree-item-title">{item.requirement.document.title}</span>
      <span className={`tree-status tree-status--${item.status}`}>
        {getStatusLabel(item.status)}
      </span>
      <small>
        {new Date(item.requirement.document.updatedAt).toLocaleDateString(
          'zh-CN',
        )}
      </small>
    </button>
  );
}

function RequirementTree({
  projects,
  statusOverrides,
  onNavigate,
  activeProjectName,
  onSelectProject,
  collapsedProjects,
  onToggleProject,
  canCreate,
  onCreate,
  onCreateProject,
  onDeleteProject,
  onRenameProject,
  onRequestEditing,
}: {
  projects: readonly ProjectRequirements[];
  statusOverrides: Readonly<Record<string, RequirementStatus>>;
  onNavigate: (item: DisplayRequirement) => void;
  activeProjectName: string | undefined;
  onSelectProject: (projectName: string) => void;
  collapsedProjects: Readonly<Record<string, boolean>>;
  onToggleProject: (projectName: string, collapsed: boolean) => void;
  canCreate: boolean;
  onCreate: (projectName: string) => void;
  onCreateProject: () => void;
  onDeleteProject: (project: ProjectRequirements) => void;
  onRenameProject: (project: ProjectRequirements) => void;
  onRequestEditing: () => void;
}): React.JSX.Element {
  const [actionProjectName, setActionProjectName] = useState<string>();

  return (
    <nav aria-label="需求目录">
      {canCreate && (
        <button
          className="tree-create-project"
          onClick={onCreateProject}
          type="button"
        >
          <Plus aria-hidden="true" size={15} />
          <span>新增项目</span>
        </button>
      )}
      {projects.map((project) => {
        const projectItems = project.requirements
          .map((requirement) => ({
            projectName: project.projectName,
            requirement,
            status:
              statusOverrides[
                getRequirementKey(project.projectName, requirement.document.id)
              ] ?? requirement.document.status,
          }))
          .sort(
            (left, right) =>
              right.requirement.document.updatedAtTimestamp -
              left.requirement.document.updatedAtTimestamp,
          );
        return (
          <div
            className={`tree-project ${activeProjectName === project.projectName ? 'tree-project--active' : ''}`}
            key={project.projectName}
          >
            <details
              onToggle={(event) => {
                onToggleProject(project.projectName, !event.currentTarget.open);
              }}
              open={!collapsedProjects[project.projectName]}
            >
              {/* biome-ignore lint/a11y/noStaticElementInteractions: summary is the native keyboard-accessible toggle control. */}
              <summary onClick={() => onSelectProject(project.projectName)}>
                <ChevronDown aria-hidden="true" size={15} />
                <span>{project.projectName}</span>
                <small>{projectItems.length}</small>
              </summary>
              <div className="tree-project-content">
                {projectItems.map((item) => (
                  <RequirementTreeItem
                    item={item}
                    key={item.requirement.document.id}
                    onNavigate={onNavigate}
                  />
                ))}
              </div>
            </details>
            <div
              className={`tree-project-actions ${actionProjectName === project.projectName ? 'tree-project-actions--open' : ''}`}
            >
              <button
                aria-expanded={
                  canCreate && actionProjectName === project.projectName
                }
                aria-haspopup={canCreate ? 'menu' : undefined}
                aria-label={
                  canCreate ? `${project.projectName} 更多操作` : '进入编辑状态'
                }
                className="tree-project-more"
                onClick={(event) => {
                  event.preventDefault();
                  event.stopPropagation();
                  if (!canCreate) {
                    onRequestEditing();
                    return;
                  }
                  setActionProjectName((current) =>
                    current === project.projectName
                      ? undefined
                      : project.projectName,
                  );
                }}
                title={canCreate ? '更多操作' : '进入编辑状态'}
                type="button"
              >
                <Ellipsis aria-hidden="true" size={18} />
              </button>
              {canCreate && (
                <div className="tree-project-action-menu" role="menu">
                  <button
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setActionProjectName(undefined);
                      onCreate(project.projectName);
                    }}
                    role="menuitem"
                    title="新建需求"
                    type="button"
                  >
                    <Plus aria-hidden="true" size={15} />
                    <span>新建需求</span>
                  </button>
                  <button
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setActionProjectName(undefined);
                      onRenameProject(project);
                    }}
                    role="menuitem"
                    title="重命名项目"
                    type="button"
                  >
                    <Pencil aria-hidden="true" size={14} />
                    <span>重命名</span>
                  </button>
                  <button
                    className="tree-project-action-menu-delete"
                    onClick={(event) => {
                      event.preventDefault();
                      event.stopPropagation();
                      setActionProjectName(undefined);
                      onDeleteProject(project);
                    }}
                    role="menuitem"
                    title="删除项目"
                    type="button"
                  >
                    <Trash2 aria-hidden="true" size={14} />
                    <span>删除项目</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        );
      })}
    </nav>
  );
}

function RequirementBody({
  images,
  requirement,
  description,
  isChild,
  onPreview,
}: {
  images: readonly RequirementImage[];
  requirement: LoadedRequirement;
  description: string;
  isChild: boolean;
  onPreview: (image: PreviewImage) => void;
}): React.JSX.Element {
  const renderedDescription = DOMPurify.sanitize(
    marked.parse(
      normalizeRequirementMarkdown(description || '该需求仅包含图示。'),
      {
        async: false,
      },
    ),
  );

  return (
    <div
      className={`requirement-body ${isChild ? 'requirement-body--child' : ''} ${images.length > 0 ? 'requirement-body--visual' : ''}`}
    >
      {images.length > 0 && (
        <section aria-label="图示" className="section-images">
          {images.map((image) => (
            <button
              aria-label={`查看图示：${image.alt}`}
              className="requirement-image-trigger"
              key={image.path}
              onClick={() =>
                onPreview({
                  alt: image.alt,
                  src: readImageUrl(requirement, image.path),
                })
              }
              type="button"
            >
              <img
                alt=""
                onError={(event) => {
                  event.currentTarget.closest('button')?.remove();
                }}
                src={readImageUrl(requirement, image.path)}
              />
            </button>
          ))}
        </section>
      )}
      <div
        className="requirement-markdown"
        // biome-ignore lint/security/noDangerouslySetInnerHtml: DOMPurify sanitizes the rendered Markdown before insertion.
        dangerouslySetInnerHTML={{ __html: renderedDescription }}
      />
    </div>
  );
}

function ImagePreview({
  image,
  onClose,
}: {
  image: PreviewImage | undefined;
  onClose: () => void;
}): React.JSX.Element | null {
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const isOpen = Boolean(image);

  useEffect(() => {
    if (isOpen) closeButtonRef.current?.focus();
  }, [isOpen]);

  if (!image) return null;

  return (
    <dialog
      aria-label={`图示预览：${image.alt}`}
      className="image-preview"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      open
    >
      <button
        aria-label="关闭图示预览"
        className="image-preview-close"
        onClick={onClose}
        ref={closeButtonRef}
        type="button"
      >
        <X aria-hidden="true" size={20} />
      </button>
      <img alt={image.alt} src={image.src} />
    </dialog>
  );
}

function VisualEditorDialog({
  item,
  onClose,
  onDelete,
  onGroupsChange,
  onPreview,
  onRename,
  onSave,
  onVisualMove,
  startTitleEditing = false,
}: {
  item: DisplayRequirement | undefined;
  onClose: () => void;
  onDelete: (
    item: DisplayRequirement,
    path: string,
  ) => Promise<DisplayRequirement>;
  onGroupsChange: (
    item: DisplayRequirement,
    input: Readonly<{ action: 'add' | 'remove'; sectionIndex?: number }>,
  ) => Promise<DisplayRequirement>;
  onPreview: (image: PreviewImage) => void;
  onRename: (
    item: DisplayRequirement,
    title: string,
  ) => Promise<DisplayRequirement>;
  onSave: (
    item: DisplayRequirement,
    input: Readonly<{ data: string; filename: string; sectionTitle: string }>,
  ) => Promise<DisplayRequirement>;
  onVisualMove: (
    item: DisplayRequirement,
    input: Readonly<{
      insertAfter?: boolean;
      path: string;
      targetPath?: string;
      targetSectionIndex: number;
    }>,
  ) => Promise<DisplayRequirement>;
  startTitleEditing?: boolean;
}): React.JSX.Element | null {
  const [currentItem, setCurrentItem] = useState(item);
  const [title, setTitle] = useState(item?.requirement.document.title ?? '');
  const [pasteTarget, setPasteTarget] = useState(0);
  const [isSaving, setIsSaving] = useState(false);
  const [isTitleEditing, setIsTitleEditing] = useState(false);
  const [draggingPath, setDraggingPath] = useState<string>();
  const [dropTarget, setDropTarget] =
    useState<
      Readonly<{
        insertAfter: boolean;
        path: string;
        sectionIndex: number;
      }>
    >();
  useEffect(() => {
    setCurrentItem(item);
    setTitle(item?.requirement.document.title ?? '');
    setPasteTarget(0);
    setIsTitleEditing(Boolean(item && startTitleEditing));
  }, [item, startTitleEditing]);
  if (!currentItem) return null;
  const activeItem = currentItem;

  async function updateTitle(): Promise<void> {
    const nextTitle = title.trim();
    if (!nextTitle || nextTitle === activeItem.requirement.document.title)
      return;
    setIsSaving(true);
    try {
      setCurrentItem(await onRename(activeItem, nextTitle));
      setIsTitleEditing(false);
    } finally {
      setIsSaving(false);
    }
  }

  function cancelTitleEdit(): void {
    setTitle(activeItem.requirement.document.title);
    setIsTitleEditing(false);
  }

  async function pasteImage(
    event: React.ClipboardEvent<HTMLElement>,
  ): Promise<void> {
    const clipboardImage = Array.from(event.clipboardData.items).find((entry) =>
      entry.type.startsWith('image/'),
    );
    const image = clipboardImage?.getAsFile();
    if (!image) return;
    event.preventDefault();
    setIsSaving(true);
    try {
      const data = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onerror = () => reject(reader.error);
        reader.onload = () => resolve(String(reader.result));
        reader.readAsDataURL(image);
      });
      const extension =
        image.type.split('/')[1]?.replace('jpeg', 'jpg') ?? 'png';
      setCurrentItem(
        await onSave(activeItem, {
          data,
          filename: `image-${Date.now()}.${extension}`,
          sectionTitle:
            activeItem.requirement.document.sections[pasteTarget]?.title ?? '',
        }),
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function changeGroups(
    input: Readonly<{ action: 'add' | 'remove'; sectionIndex?: number }>,
  ): Promise<void> {
    setIsSaving(true);
    try {
      const next = await onGroupsChange(activeItem, input);
      setCurrentItem(next);
      setPasteTarget(
        Math.min(pasteTarget, next.requirement.document.sections.length - 1),
      );
    } finally {
      setIsSaving(false);
    }
  }

  async function deleteImage(path: string): Promise<void> {
    setIsSaving(true);
    try {
      setCurrentItem(await onDelete(activeItem, path));
    } finally {
      setIsSaving(false);
    }
  }

  async function moveImage(
    targetSectionIndex: number,
    targetPath?: string,
    insertAfter?: boolean,
  ): Promise<void> {
    if (!draggingPath || draggingPath === targetPath) return;
    setIsSaving(true);
    try {
      setCurrentItem(
        await onVisualMove(activeItem, {
          path: draggingPath,
          targetSectionIndex,
          ...(insertAfter ? { insertAfter: true } : {}),
          ...(targetPath ? { targetPath } : {}),
        }),
      );
    } finally {
      setDraggingPath(undefined);
      setDropTarget(undefined);
      setIsSaving(false);
    }
  }

  return (
    <dialog
      aria-label="编辑图示"
      className="visual-editor-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
        else if (
          isTitleEditing &&
          !(
            event.target instanceof Element &&
            event.target.closest('.visual-editor-title')
          )
        ) {
          void updateTitle();
        }
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      onPaste={(event) => void pasteImage(event)}
      open
    >
      <section className="visual-editor-content">
        <header>
          {isTitleEditing ? (
            <input
              aria-label="需求名称"
              autoFocus
              className="visual-editor-title"
              disabled={isSaving}
              onBlur={() => void updateTitle()}
              onChange={(event) => setTitle(event.target.value)}
              onFocus={(event) => {
                if (startTitleEditing) event.currentTarget.select();
              }}
              onKeyDown={(event) => {
                if (event.key === 'Enter') event.currentTarget.blur();
                if (event.key === 'Escape') cancelTitleEdit();
              }}
              value={title}
            />
          ) : (
            <button
              aria-label="编辑需求名称"
              className="visual-editor-title-display"
              onClick={() => setIsTitleEditing(true)}
              type="button"
            >
              <span>{activeItem.requirement.document.title}</span>
              <Pencil aria-hidden="true" size={15} />
            </button>
          )}
          <button
            aria-label="关闭编辑图示"
            className="visual-editor-close"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>
        <div className="visual-group-list">
          {activeItem.requirement.document.sections.map((section, index) => (
            <div
              className="visual-group"
              key={[
                section.title,
                ...section.images.map((image) => image.path),
              ].join('|')}
            >
              <div className="visual-group-images">
                {section.images.map((image) => (
                  <fieldset
                    className={`visual-group-image-item ${draggingPath === image.path ? 'visual-group-image-item--dragging' : ''} ${dropTarget?.path === image.path && dropTarget.sectionIndex === index ? 'visual-group-image-item--drop-target' : ''} ${dropTarget?.path === image.path && dropTarget.sectionIndex === index && dropTarget.insertAfter ? 'visual-group-image-item--drop-target-after' : ''}`}
                    draggable={!isSaving}
                    key={image.path}
                    onDragEnd={() => {
                      setDraggingPath(undefined);
                      setDropTarget(undefined);
                    }}
                    onDragOver={(event) => {
                      if (!draggingPath || draggingPath === image.path) return;
                      event.preventDefault();
                      const bounds =
                        event.currentTarget.getBoundingClientRect();
                      setDropTarget({
                        insertAfter:
                          event.clientX >= bounds.left + bounds.width / 2,
                        path: image.path,
                        sectionIndex: index,
                      });
                    }}
                    onDragStart={(event) => {
                      event.dataTransfer.effectAllowed = 'move';
                      event.dataTransfer.setData('text/plain', image.path);
                      setDraggingPath(image.path);
                    }}
                    onDrop={(event) => {
                      event.preventDefault();
                      const bounds =
                        event.currentTarget.getBoundingClientRect();
                      void moveImage(
                        index,
                        image.path,
                        event.clientX >= bounds.left + bounds.width / 2,
                      );
                    }}
                  >
                    <img
                      alt={image.alt}
                      className="visual-group-image"
                      draggable={false}
                      src={readImageUrl(activeItem.requirement, image.path)}
                    />
                    <button
                      aria-label={`查看图示：${image.alt}`}
                      className="preview-visual"
                      disabled={isSaving}
                      onClick={() =>
                        onPreview({
                          alt: image.alt,
                          src: readImageUrl(activeItem.requirement, image.path),
                        })
                      }
                      title="全屏查看图示"
                      type="button"
                    >
                      <Maximize2 aria-hidden="true" size={14} />
                    </button>
                    <button
                      aria-label="删除图示"
                      className="delete-visual"
                      disabled={isSaving}
                      onClick={() => void deleteImage(image.path)}
                      title="删除图示"
                      type="button"
                    >
                      <Trash2 aria-hidden="true" size={14} />
                    </button>
                  </fieldset>
                ))}
                <button
                  aria-label="向此图示层粘贴图片"
                  aria-pressed={pasteTarget === index}
                  className="paste-visual-tile"
                  disabled={isSaving}
                  onClick={() => setPasteTarget(index)}
                  onDragOver={(event) => {
                    if (draggingPath) event.preventDefault();
                  }}
                  onDrop={(event) => {
                    event.preventDefault();
                    void moveImage(index);
                  }}
                  onPaste={(event) => void pasteImage(event)}
                  title="选择此图示层后粘贴图片"
                  type="button"
                >
                  <ClipboardPaste aria-hidden="true" size={24} />
                </button>
              </div>
              {index < activeItem.requirement.document.sections.length - 1 && (
                <div className="visual-group-divider">
                  <button
                    aria-label="在此插入分割线"
                    disabled={isSaving}
                    onClick={() =>
                      void changeGroups({
                        action: 'add',
                        sectionIndex: index + 1,
                      })
                    }
                    title="在此插入分割线"
                    type="button"
                  >
                    +
                  </button>
                  <button
                    aria-label="移除分割线"
                    disabled={isSaving}
                    onClick={() =>
                      void changeGroups({
                        action: 'remove',
                        sectionIndex: index + 1,
                      })
                    }
                    title="移除分割线"
                    type="button"
                  >
                    −
                  </button>
                </div>
              )}
            </div>
          ))}
          <div className="visual-group-divider visual-group-divider--add">
            <button
              aria-label="添加分割线"
              disabled={isSaving}
              onClick={() => void changeGroups({ action: 'add' })}
              title="添加分割线"
              type="button"
            >
              +
            </button>
          </div>
        </div>
      </section>
    </dialog>
  );
}

function EditorUnlockDialog({
  onClose,
  onUnlocked,
}: {
  onClose: () => void;
  onUnlocked: () => Promise<void>;
}): React.JSX.Element {
  const [digits, setDigits] = useState(['', '', '', '']);
  const [error, setError] = useState(false);
  const inputRefs = useRef<Array<HTMLInputElement | null>>([]);

  useEffect(() => {
    inputRefs.current[0]?.focus();
  }, []);

  async function verify(nextDigits: readonly string[]): Promise<void> {
    const passcode = nextDigits.join('');
    if (passcode.length !== 4) return;
    try {
      await unlockEditor(passcode);
      await onUnlocked();
      onClose();
    } catch {
      setError(true);
      setDigits(['', '', '', '']);
      inputRefs.current[0]?.focus();
    }
  }

  function changeDigit(index: number, value: string): void {
    const digit = value.replace(/\D/g, '').at(-1) ?? '';
    const nextDigits = digits.map((current, currentIndex) =>
      currentIndex === index ? digit : current,
    );
    setDigits(nextDigits);
    setError(false);
    if (digit && index < nextDigits.length - 1) {
      inputRefs.current[index + 1]?.focus();
    }
    if (nextDigits.every(Boolean)) void verify(nextDigits);
  }

  function handleKeyDown(
    event: React.KeyboardEvent<HTMLInputElement>,
    index: number,
  ): void {
    if (event.key === 'Backspace' && !digits[index] && index > 0) {
      inputRefs.current[index - 1]?.focus();
    }
  }

  return (
    <dialog
      aria-label="进入编辑状态"
      className={`editor-unlock-dialog ${error ? 'editor-unlock-dialog--error' : ''}`}
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      open
    >
      <fieldset className="editor-unlock-digits">
        <legend className="visually-hidden">四位编辑口令</legend>
        {editorDigitPositions.map(({ id, position }) => (
          <input
            aria-label={`第 ${position + 1} 位编辑口令`}
            inputMode="numeric"
            key={id}
            maxLength={1}
            onChange={(event) => changeDigit(position, event.target.value)}
            onKeyDown={(event) => handleKeyDown(event, position)}
            ref={(element) => {
              inputRefs.current[position] = element;
            }}
            type="text"
            value={digits[position]}
          />
        ))}
      </fieldset>
      {error && <p role="alert">口令不正确</p>}
    </dialog>
  );
}

function RequirementSearchResults({
  onSelect,
  results,
}: {
  onSelect: (item: DisplayRequirement) => void;
  results: readonly DisplayRequirement[];
}): React.JSX.Element {
  return (
    <ul aria-label="搜索结果" className="requirement-search-results">
      {results.length > 0 ? (
        results.map((item) => (
          <li
            key={getRequirementKey(
              item.projectName,
              item.requirement.document.id,
            )}
          >
            <button
              onClick={() => onSelect(item)}
              onMouseDown={(event) => event.preventDefault()}
              type="button"
            >
              <span className="search-result-heading">
                <span className="search-result-title">
                  {item.requirement.document.title}
                </span>
                <span
                  className={`search-result-status search-result-status--${item.status}`}
                >
                  {getStatusLabel(item.status)}
                </span>
                <time dateTime={item.requirement.document.updatedAt}>
                  {new Date(
                    item.requirement.document.updatedAt,
                  ).toLocaleDateString('zh-CN')}
                </time>
              </span>
              <small className="search-result-project">
                {item.projectName}
              </small>
            </button>
          </li>
        ))
      ) : (
        <li className="search-results-empty">未找到需求</li>
      )}
    </ul>
  );
}

function NewProjectDialog({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (projectName: string) => Promise<void>;
}): React.JSX.Element {
  const [projectName, setProjectName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  async function submit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    const nextProjectName = projectName.trim();
    if (!nextProjectName || isCreating) return;
    setIsCreating(true);
    try {
      await onCreate(nextProjectName);
      onClose();
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <dialog
      aria-label="新增项目"
      className="new-project-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      open
    >
      <form
        className="new-project-surface"
        onSubmit={(event) => void submit(event)}
      >
        <header>
          <h2>新增项目</h2>
          <button
            aria-label="关闭新增项目"
            className="new-project-close"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>
        <input
          aria-label="项目名称"
          disabled={isCreating}
          onChange={(event) => setProjectName(event.target.value)}
          placeholder="输入项目名称"
          ref={inputRef}
          value={projectName}
        />
        <footer>
          <button
            className="new-project-submit"
            disabled={!projectName.trim() || isCreating}
            type="submit"
          >
            创建项目
          </button>
        </footer>
      </form>
    </dialog>
  );
}

function RenameProjectDialog({
  project,
  onClose,
  onRename,
}: {
  project: ProjectRequirements;
  onClose: () => void;
  onRename: (projectName: string) => Promise<void>;
}): React.JSX.Element {
  const [projectName, setProjectName] = useState(project.projectName);
  const [isSaving, setIsSaving] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  async function submit(
    event: React.FormEvent<HTMLFormElement>,
  ): Promise<void> {
    event.preventDefault();
    const nextProjectName = projectName.trim();
    if (!nextProjectName || isSaving) return;
    setIsSaving(true);
    try {
      await onRename(nextProjectName);
      onClose();
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <dialog
      aria-label="重命名项目"
      className="new-project-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      open
    >
      <form
        className="new-project-surface"
        onSubmit={(event) => void submit(event)}
      >
        <header>
          <h2>重命名项目</h2>
          <button
            aria-label="关闭重命名项目"
            className="new-project-close"
            onClick={onClose}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>
        <input
          aria-label="项目名称"
          disabled={isSaving}
          onChange={(event) => setProjectName(event.target.value)}
          ref={inputRef}
          value={projectName}
        />
        <footer>
          <button
            className="new-project-submit"
            disabled={!projectName.trim() || isSaving}
            type="submit"
          >
            保存
          </button>
        </footer>
      </form>
    </dialog>
  );
}

function DeleteProjectDialog({
  project,
  onClose,
  onDelete,
}: {
  project: ProjectRequirements;
  onClose: () => void;
  onDelete: () => Promise<void>;
}): React.JSX.Element {
  const [isDeleting, setIsDeleting] = useState(false);
  const closeButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    closeButtonRef.current?.focus();
  }, []);

  async function confirm(): Promise<void> {
    if (isDeleting) return;
    setIsDeleting(true);
    try {
      await onDelete();
      onClose();
    } finally {
      setIsDeleting(false);
    }
  }

  return (
    <dialog
      aria-label="删除项目"
      className="new-project-dialog project-delete-dialog"
      onCancel={(event) => {
        event.preventDefault();
        onClose();
      }}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
      onKeyDown={(event) => {
        if (event.key === 'Escape') onClose();
      }}
      open
    >
      <section className="new-project-surface project-delete-surface">
        <header>
          <h2 className="project-delete-title">
            <Trash2 aria-hidden="true" size={17} />
            <span>删除项目</span>
          </h2>
          <button
            aria-label="关闭删除项目"
            className="new-project-close"
            onClick={onClose}
            ref={closeButtonRef}
            type="button"
          >
            <X aria-hidden="true" size={18} />
          </button>
        </header>
        <p>
          将删除“{project.projectName}”及其 {project.requirements.length}{' '}
          条需求和图示，此操作无法恢复。
        </p>
        <footer>
          <button
            className="project-delete-cancel"
            disabled={isDeleting}
            onClick={onClose}
            type="button"
          >
            取消
          </button>
          <button
            className="project-delete-confirm"
            disabled={isDeleting}
            onClick={() => void confirm()}
            type="button"
          >
            <Trash2 aria-hidden="true" size={14} />
            删除项目
          </button>
        </footer>
      </section>
    </dialog>
  );
}

function RequirementCard({
  canEdit,
  item,
  onStatusChange,
  onVisualEdit,
  onPreview,
}: {
  canEdit: boolean;
  item: DisplayRequirement;
  onStatusChange: (item: DisplayRequirement, status: RequirementStatus) => void;
  onVisualEdit: (item: DisplayRequirement) => void;
  onPreview: (image: PreviewImage) => void;
}): React.JSX.Element {
  const { document } = item.requirement;
  const hasChildSections = document.sections.length > 1;
  const cardId = `requirement-${encodeURIComponent(
    getRequirementKey(item.projectName, document.id),
  )}`;

  return (
    <article className="requirement-card" id={cardId}>
      <header className="requirement-card-header">
        <div className="requirement-title-meta">
          <h2>{document.title}</h2>
          <time dateTime={document.updatedAt}>
            {new Date(document.updatedAt).toLocaleDateString('zh-CN')}
          </time>
        </div>
        {canEdit ? (
          <div className="requirement-edit-controls">
            <fieldset className="status-picker">
              <legend className="visually-hidden">
                {document.title} 的需求状态
              </legend>
              {requirementStatuses.map((status) => (
                <button
                  aria-pressed={item.status === status.id}
                  key={status.id}
                  onClick={() => onStatusChange(item, status.id)}
                  type="button"
                >
                  {status.label}
                </button>
              ))}
            </fieldset>
            <button
              aria-label={`${document.title} 添加图示`}
              className="add-visual"
              onClick={() => onVisualEdit(item)}
              title="添加图示"
              type="button"
            >
              <ImagePlus aria-hidden="true" size={16} />
            </button>
          </div>
        ) : (
          <span
            className={`requirement-status requirement-status--${item.status}`}
          >
            {getStatusLabel(item.status)}
          </span>
        )}
      </header>
      <div
        className={`requirement-content ${hasChildSections ? 'requirement-content--sections' : ''}`}
      >
        {document.sections.map((section) => (
          <RequirementBody
            description={section.description}
            images={section.images}
            isChild={hasChildSections}
            key={`${document.id}-${section.title}-${section.images.map((image) => image.path).join('-')}`}
            onPreview={onPreview}
            requirement={item.requirement}
          />
        ))}
      </div>
    </article>
  );
}

export function App(): React.JSX.Element {
  const [persistedView] = useState(readPersistedManagerView);
  const [projects, setProjects] = useState<readonly ProjectRequirements[]>([]);
  const [activeProjectName, setActiveProjectName] = useState(
    persistedView.activeProjectName,
  );
  const [statusOverrides, setStatusOverrides] = useState<
    Readonly<Record<string, RequirementStatus>>
  >({});
  const [collapsedProjects, setCollapsedProjects] = useState<
    Readonly<Record<string, boolean>>
  >(persistedView.collapsedProjects);
  const [isNavigatorCollapsed, setIsNavigatorCollapsed] = useState(
    persistedView.isNavigatorCollapsed,
  );
  const [canEdit, setCanEdit] = useState(false);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isStatusFilterOpen, setIsStatusFilterOpen] = useState(false);
  const [query, setQuery] = useState(persistedView.query);
  const [statusFilter, setStatusFilter] = useState<RequirementStatus | 'all'>(
    persistedView.statusFilter,
  );
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isIndexLoaded, setIsIndexLoaded] = useState(false);
  const [error, setError] = useState<string>();
  const [previewImage, setPreviewImage] = useState<PreviewImage>();
  const [visualEditItem, setVisualEditItem] = useState<DisplayRequirement>();
  const [isVisualTitleEditing, setIsVisualTitleEditing] = useState(false);
  const [isNewProjectOpen, setIsNewProjectOpen] = useState(false);
  const [renameProjectTarget, setRenameProjectTarget] =
    useState<ProjectRequirements>();
  const [deleteProjectTarget, setDeleteProjectTarget] =
    useState<ProjectRequirements>();
  const [isEditorUnlockOpen, setIsEditorUnlockOpen] = useState(false);
  const detailPaneRef = useRef<HTMLElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const treeGroupsRef = useRef<HTMLDivElement>(null);
  const restoredScrollRef = useRef(false);

  const displayRequirements = useMemo(
    () =>
      projects.flatMap((project) =>
        [...project.requirements]
          .sort(
            (left, right) =>
              right.document.updatedAtTimestamp -
              left.document.updatedAtTimestamp,
          )
          .map((requirement) => ({
            projectName: project.projectName,
            requirement,
            status:
              statusOverrides[
                getRequirementKey(project.projectName, requirement.document.id)
              ] ?? requirement.document.status,
          })),
      ),
    [projects, statusOverrides],
  );

  const currentProject =
    projects.find((project) => project.projectName === activeProjectName) ??
    projects[0];
  const currentProjectName = currentProject?.projectName;

  const currentProjectRequirements = useMemo(
    () =>
      [...(currentProject?.requirements ?? [])]
        .sort(
          (left, right) =>
            right.document.updatedAtTimestamp -
            left.document.updatedAtTimestamp,
        )
        .map((requirement) => ({
          projectName: currentProject?.projectName ?? '',
          requirement,
          status:
            statusOverrides[
              getRequirementKey(
                currentProject?.projectName ?? '',
                requirement.document.id,
              )
            ] ?? requirement.document.status,
        })),
    [currentProject, statusOverrides],
  );

  const filteredRequirements = useMemo(
    () =>
      statusFilter === 'all'
        ? currentProjectRequirements
        : currentProjectRequirements.filter(
            (item) => item.status === statusFilter,
          ),
    [currentProjectRequirements, statusFilter],
  );

  const searchResults = useMemo(() => {
    const normalizedQuery = query.trim().toLocaleLowerCase();
    return displayRequirements.filter((item) =>
      matchesRequirement(item, normalizedQuery),
    );
  }, [displayRequirements, query]);

  async function loadScan(refresh = false): Promise<void> {
    setIsRefreshing(true);
    try {
      const scanned = refresh
        ? await refreshProjectCollection()
        : await scanProjectCollection();
      setCanEdit(scanned.canEdit);
      setProjects(scanned.projects);
      setError(undefined);
    } catch {
      setError('无法读取本机需求索引。请确认管理器启动器仍在运行。');
    } finally {
      setIsRefreshing(false);
      setIsIndexLoaded(true);
    }
  }

  function selectProject(projectName: string): void {
    setActiveProjectName(projectName);
    persistManagerView({ activeProjectName: projectName });
  }

  function navigateToRequirement(item: DisplayRequirement): void {
    selectProject(item.projectName);
    requestAnimationFrame(() => {
      document
        .getElementById(
          `requirement-${encodeURIComponent(
            getRequirementKey(item.projectName, item.requirement.document.id),
          )}`,
        )
        ?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  }

  async function changeStatus(
    item: DisplayRequirement,
    status: RequirementStatus,
  ): Promise<void> {
    if (!canEdit || item.status === status) return;
    setStatusOverrides((current) => ({
      ...current,
      [getRequirementKey(item.projectName, item.requirement.document.id)]:
        status,
    }));
    try {
      const scanned = await updateRequirementStatus(item.requirement, status);
      setCanEdit(scanned.canEdit);
      setProjects(scanned.projects);
      setStatusOverrides({});
      setError(undefined);
    } catch {
      setStatusOverrides((current) => {
        const next = { ...current };
        delete next[
          getRequirementKey(item.projectName, item.requirement.document.id)
        ];
        return next;
      });
      setError('无法保存需求状态。请确认正在通过本机地址访问管理器。');
    }
  }

  async function saveVisual(
    item: DisplayRequirement,
    input: Readonly<{ data: string; filename: string; sectionTitle: string }>,
  ): Promise<DisplayRequirement> {
    try {
      const scanned = await addRequirementVisual(item.requirement, input);
      setProjects(scanned.projects);
      setCanEdit(scanned.canEdit);
      setError(undefined);
      return findDisplayRequirement(scanned.projects, item);
    } catch {
      setError('无法保存图示。请确认正在通过本机地址访问管理器。');
      throw new Error('Visual save failed.');
    }
  }

  async function renameRequirement(
    item: DisplayRequirement,
    title: string,
  ): Promise<DisplayRequirement> {
    const scanned = await updateRequirementTitle(item.requirement, title);
    setProjects(scanned.projects);
    setCanEdit(scanned.canEdit);
    return findDisplayRequirement(scanned.projects, item);
  }

  async function changeVisualGroups(
    item: DisplayRequirement,
    input: Readonly<{ action: 'add' | 'remove'; sectionIndex?: number }>,
  ): Promise<DisplayRequirement> {
    const scanned = await updateVisualGroups(item.requirement, input);
    setProjects(scanned.projects);
    setCanEdit(scanned.canEdit);
    return findDisplayRequirement(scanned.projects, item);
  }

  async function moveVisual(
    item: DisplayRequirement,
    input: Readonly<{
      insertAfter?: boolean;
      path: string;
      targetPath?: string;
      targetSectionIndex: number;
    }>,
  ): Promise<DisplayRequirement> {
    const scanned = await updateVisualOrder(item.requirement, input);
    setProjects(scanned.projects);
    setCanEdit(scanned.canEdit);
    return findDisplayRequirement(scanned.projects, item);
  }

  async function deleteVisual(
    item: DisplayRequirement,
    path: string,
  ): Promise<DisplayRequirement> {
    const scanned = await deleteRequirementVisual(item.requirement, path);
    setProjects(scanned.projects);
    setCanEdit(scanned.canEdit);
    return findDisplayRequirement(scanned.projects, item);
  }

  async function createNewRequirement(projectName: string): Promise<void> {
    try {
      const scanned = await createRequirement({
        projectName,
        title: '未命名需求',
      });
      const created = scanned.projects
        .find((project) => project.projectName === scanned.created.projectName)
        ?.requirements.find(
          (requirement) => requirement.document.id === scanned.created.id,
        );
      if (!created) throw new Error('Created requirement was not returned.');
      const item: DisplayRequirement = {
        projectName: scanned.created.projectName,
        requirement: created,
        status: created.document.status,
      };
      setProjects(scanned.projects);
      setCanEdit(scanned.canEdit);
      setError(undefined);
      setStatusFilter('all');
      requestAnimationFrame(() => navigateToRequirement(item));
      setIsVisualTitleEditing(true);
      setVisualEditItem(item);
    } catch {
      setError('无法新建需求。请确认正在通过本机地址访问管理器。');
      throw new Error('Requirement creation failed.');
    }
  }

  async function createNewProject(projectName: string): Promise<void> {
    try {
      const scanned = await createProject(projectName);
      setProjects(scanned.projects);
      setCanEdit(scanned.canEdit);
      setError(undefined);
    } catch {
      setError('无法新增项目。请确认项目名称未重复。');
      throw new Error('Project creation failed.');
    }
  }

  async function renameExistingProject(nextProjectName: string): Promise<void> {
    const project = renameProjectTarget;
    if (!project) return;
    try {
      const scanned = await renameProject(project.projectName, nextProjectName);
      setProjects(scanned.projects);
      setCanEdit(scanned.canEdit);
      setActiveProjectName(nextProjectName);
      setCollapsedProjects((current) => {
        const next = { ...current };
        const collapsed = next[project.projectName];
        delete next[project.projectName];
        if (collapsed !== undefined) next[nextProjectName] = collapsed;
        return next;
      });
      setError(undefined);
    } catch {
      setError('无法重命名项目。请确认项目名称未重复。');
      throw new Error('Project rename failed.');
    }
  }

  async function deleteExistingProject(): Promise<void> {
    const project = deleteProjectTarget;
    if (!project) return;
    try {
      const scanned = await deleteProject(project.projectName);
      setProjects(scanned.projects);
      setCanEdit(scanned.canEdit);
      setActiveProjectName(scanned.projects[0]?.projectName);
      setCollapsedProjects((current) => {
        const next = { ...current };
        delete next[project.projectName];
        return next;
      });
      setError(undefined);
    } catch {
      setError('无法删除项目。请确认正在通过本机地址访问管理器。');
      throw new Error('Project deletion failed.');
    }
  }

  function openVisualEditor(item: DisplayRequirement): void {
    setIsVisualTitleEditing(false);
    setVisualEditItem(item);
  }

  function toggleProject(projectName: string, collapsed: boolean): void {
    setCollapsedProjects((current) => ({
      ...current,
      [projectName]: collapsed,
    }));
  }

  function changeStatusFilter(status: RequirementStatus | 'all'): void {
    setStatusFilter(status);
    setIsStatusFilterOpen(false);
  }

  function selectSearchResult(item: DisplayRequirement): void {
    if (statusFilter !== 'all' && item.status !== statusFilter) {
      setStatusFilter('all');
    }
    setIsSearchOpen(false);
    setQuery('');
    requestAnimationFrame(() => navigateToRequirement(item));
  }

  useEffect(() => {
    if (!isIndexLoaded) return;
    persistManagerView({
      activeProjectName: currentProjectName,
      collapsedProjects,
      isNavigatorCollapsed,
      query,
      statusFilter,
    });
  }, [
    collapsedProjects,
    currentProjectName,
    isIndexLoaded,
    isNavigatorCollapsed,
    query,
    statusFilter,
  ]);

  useEffect(() => {
    function openRequirementSearch(event: KeyboardEvent): void {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'f') {
        event.preventDefault();
        setIsSearchOpen(true);
        requestAnimationFrame(() => searchInputRef.current?.focus());
      }
    }

    window.addEventListener('keydown', openRequirementSearch);
    return () => window.removeEventListener('keydown', openRequirementSearch);
  }, []);

  useEffect(() => {
    if (!projects.length || restoredScrollRef.current) return;
    const animationFrame = requestAnimationFrame(() => {
      treeGroupsRef.current?.scrollTo({ top: persistedView.treeScrollTop });
      detailPaneRef.current?.scrollTo({ top: persistedView.detailScrollTop });
      restoredScrollRef.current = true;
    });
    return () => cancelAnimationFrame(animationFrame);
  }, [persistedView.detailScrollTop, persistedView.treeScrollTop, projects]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: Initial local index loads once.
  useEffect(() => {
    void loadScan();
  }, []);

  return (
    <main
      className={`manager-shell ${isNavigatorCollapsed ? 'manager-shell--navigator-collapsed' : ''}`}
    >
      <aside
        className={`navigator ${isNavigatorCollapsed ? 'navigator--collapsed' : ''}`}
        aria-label="需求目录"
      >
        <header className="navigator-header">
          <div className="navigator-title">
            <button
              aria-label="进入编辑状态"
              className="navigator-heading"
              onClick={() => setIsEditorUnlockOpen(true)}
              type="button"
            >
              需求管理器
            </button>
            <div className="navigator-actions">
              <button
                className="refresh-directory"
                aria-label="刷新扫描"
                disabled={isRefreshing}
                onClick={() => void loadScan(true)}
                title="刷新扫描"
                type="button"
              >
                <RefreshCw aria-hidden="true" size={17} />
              </button>
            </div>
            <button
              aria-expanded={!isNavigatorCollapsed}
              aria-label={isNavigatorCollapsed ? '展开目录' : '收起目录'}
              className="toggle-navigator"
              onClick={() => setIsNavigatorCollapsed((collapsed) => !collapsed)}
              title={isNavigatorCollapsed ? '展开目录' : '收起目录'}
              type="button"
            >
              {isNavigatorCollapsed ? (
                <PanelLeftOpen aria-hidden="true" size={17} />
              ) : (
                <PanelLeftClose aria-hidden="true" size={17} />
              )}
            </button>
          </div>
        </header>
        {error && (
          <p className="navigator-error" role="alert">
            {error}
          </p>
        )}
        {projects.length > 0 || canEdit ? (
          <div
            className="tree-groups"
            onScroll={(event) =>
              persistManagerView({
                treeScrollTop: event.currentTarget.scrollTop,
              })
            }
            ref={treeGroupsRef}
          >
            <RequirementTree
              canCreate={canEdit}
              collapsedProjects={collapsedProjects}
              activeProjectName={currentProjectName}
              onCreate={(projectName) => void createNewRequirement(projectName)}
              onCreateProject={() => setIsNewProjectOpen(true)}
              onDeleteProject={setDeleteProjectTarget}
              onNavigate={navigateToRequirement}
              onRenameProject={setRenameProjectTarget}
              onRequestEditing={() => setIsEditorUnlockOpen(true)}
              onSelectProject={selectProject}
              onToggleProject={toggleProject}
              projects={projects}
              statusOverrides={statusOverrides}
            />
          </div>
        ) : (
          <p className="navigator-empty">暂无已归档的需求。</p>
        )}
      </aside>
      <section
        aria-label="需求展示区"
        className="detail-pane"
        onScroll={(event) =>
          persistManagerView({ detailScrollTop: event.currentTarget.scrollTop })
        }
        ref={detailPaneRef}
      >
        <header className="detail-toolbar">
          <div className="toolbar-search">
            <Search aria-hidden="true" size={17} />
            <input
              aria-label="搜索需求"
              onBlur={() => {
                window.setTimeout(() => setIsSearchOpen(false), 120);
              }}
              onChange={(event) => {
                setQuery(event.target.value);
                setIsSearchOpen(true);
              }}
              onFocus={() => setIsSearchOpen(true)}
              onKeyDown={(event) => {
                if (event.key === 'Escape') {
                  setIsSearchOpen(false);
                  event.currentTarget.blur();
                }
              }}
              placeholder="搜索需求"
              ref={searchInputRef}
              type="search"
              value={query}
            />
            {isSearchOpen && query.trim() && (
              <div className="toolbar-search-results">
                <RequirementSearchResults
                  onSelect={selectSearchResult}
                  results={searchResults}
                />
              </div>
            )}
          </div>
          <div className="status-filter-dropdown">
            <button
              aria-expanded={isStatusFilterOpen}
              aria-haspopup="menu"
              aria-label="筛选状态"
              className={`open-status-filter ${statusFilter !== 'all' ? 'open-status-filter--active' : ''}`}
              onClick={() => setIsStatusFilterOpen((open) => !open)}
              title="筛选状态"
              type="button"
            >
              <ListFilter aria-hidden="true" size={17} />
              <span>
                {statusFilter === 'all' ? '全部' : getStatusLabel(statusFilter)}
              </span>
            </button>
            {isStatusFilterOpen && (
              <div
                aria-label="按状态筛选需求"
                className="status-filter-menu"
                role="menu"
              >
                <button
                  aria-checked={statusFilter === 'all'}
                  onClick={() => changeStatusFilter('all')}
                  role="menuitemradio"
                  type="button"
                >
                  全部
                </button>
                {requirementStatuses.map((status) => (
                  <button
                    aria-checked={statusFilter === status.id}
                    key={status.id}
                    onClick={() => changeStatusFilter(status.id)}
                    role="menuitemradio"
                    type="button"
                  >
                    {status.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        </header>
        <div className="requirement-list">
          {filteredRequirements.length > 0 ? (
            <div className="requirement-results">
              {filteredRequirements.map((item) => (
                <RequirementCard
                  canEdit={canEdit}
                  item={item}
                  key={getRequirementKey(
                    item.projectName,
                    item.requirement.document.id,
                  )}
                  onStatusChange={changeStatus}
                  onVisualEdit={openVisualEditor}
                  onPreview={setPreviewImage}
                />
              ))}
            </div>
          ) : (
            <section className="detail-empty" aria-live="polite">
              <h2>未找到需求</h2>
              <p>调整关键词或状态筛选后重试。</p>
            </section>
          )}
        </div>
      </section>
      <ImagePreview
        image={previewImage}
        onClose={() => setPreviewImage(undefined)}
      />
      <VisualEditorDialog
        item={visualEditItem}
        onClose={() => {
          setIsVisualTitleEditing(false);
          setVisualEditItem(undefined);
        }}
        onDelete={deleteVisual}
        onGroupsChange={changeVisualGroups}
        onPreview={setPreviewImage}
        onRename={renameRequirement}
        onSave={saveVisual}
        onVisualMove={moveVisual}
        startTitleEditing={isVisualTitleEditing}
      />
      {isEditorUnlockOpen && (
        <EditorUnlockDialog
          onClose={() => setIsEditorUnlockOpen(false)}
          onUnlocked={() => loadScan()}
        />
      )}
      {isNewProjectOpen && (
        <NewProjectDialog
          onClose={() => setIsNewProjectOpen(false)}
          onCreate={createNewProject}
        />
      )}
      {renameProjectTarget && (
        <RenameProjectDialog
          onClose={() => setRenameProjectTarget(undefined)}
          onRename={renameExistingProject}
          project={renameProjectTarget}
        />
      )}
      {deleteProjectTarget && (
        <DeleteProjectDialog
          onClose={() => setDeleteProjectTarget(undefined)}
          onDelete={deleteExistingProject}
          project={deleteProjectTarget}
        />
      )}
    </main>
  );
}
