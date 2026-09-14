export const requirementStatuses = [
  { id: 'scheduled', label: '已排期' },
  { id: 'defined', label: '需求中' },
  { id: 'planning', label: '待规划' },
  { id: 'completed', label: '已上线' },
] as const;

export type RequirementStatus = (typeof requirementStatuses)[number]['id'];
export type RequirementStatusDefinition = (typeof requirementStatuses)[number];

export type RequirementImage = Readonly<{
  alt: string;
  path: string;
}>;

export type RequirementSection = Readonly<{
  title: string;
  description: string;
  images: readonly RequirementImage[];
}>;

export type RequirementDocument = Readonly<{
  id: string;
  title: string;
  status: RequirementStatus;
  createdAt: string;
  updatedAt: string;
  updatedAtTimestamp: number;
  sections: readonly RequirementSection[];
}>;

export type RequirementSnapshot = Readonly<{
  statuses: readonly RequirementStatusDefinition[];
  items: readonly RequirementDocument[];
}>;

/** Convert legacy prose numbering into Markdown paragraphs and ordered lists. */
export function normalizeRequirementDescription(description: string): string {
  return description
    .replace(/(^|\n)([ \t]*)(\d+[.)])(?:[ \t]*\n)+[ \t]*/gu, '$1$2$3 ')
    .replace(
      /(?<=[\u4e00-\u9fff。；：])(?=(?:[1-9]|1[0-9])[.)](?=[\u4e00-\u9fff「“]))/gu,
      '\n',
    )
    .replace(/(^|\n)([ \t]*)(\d+[.)])[ \t]*/gu, '$1$2$3 ')
    .replace(/(^|\n)([ \t]*)([一二三四五六七八九十]+、)(?=\S)/gu, '$1$2### $3')
    .replace(/^(### [^\n]+)\n(?=\d)/gmu, '$1\n\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function createRequirementMarkdown(
  document: RequirementDocument,
): string {
  const sections = document.sections
    .map((section) => {
      const heading = section.title ? `## ${section.title}\n\n` : '';
      const images = section.images
        .map((image) => `![${image.alt}](${image.path})`)
        .join('\n\n');
      const description = normalizeRequirementDescription(section.description);
      return [heading, images, description].filter(Boolean).join('\n\n');
    })
    .join('\n\n');
  return `---\nid: ${frontMatterValue(document.id)}\ntitle: ${frontMatterValue(document.title)}\nstatus: ${frontMatterValue(document.status)}\ncreatedAt: ${frontMatterValue(document.createdAt)}\nupdatedAt: ${frontMatterValue(document.updatedAt)}\n---\n\n${sections}\n`;
}

/** Create a text-only Markdown copy for handing a requirement to an AI assistant. */
export function createRequirementClipboardMarkdown(
  document: RequirementDocument,
): string {
  const sections = document.sections
    .map((section) => normalizeRequirementDescription(section.description))
    .filter(Boolean)
    .join('\n\n');
  return `# ${document.title}\n\n${sections}\n`;
}

const frontMatterPattern = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/;
const imagePattern = /!\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g;

function readFrontMatter(frontMatter: string): Record<string, string> {
  const fields: Record<string, string> = {};

  for (const line of frontMatter.split(/\r?\n/)) {
    const separatorIndex = line.indexOf(':');
    if (separatorIndex <= 0) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    fields[key] = parseFrontMatterValue(value);
  }

  return fields;
}

function frontMatterValue(value: string): string {
  if (/\r|\n/u.test(value)) {
    throw new Error('Requirement front matter values must be single-line.');
  }
  return JSON.stringify(value);
}

function parseFrontMatterValue(value: string): string {
  if (value.startsWith('"')) {
    try {
      const parsed: unknown = JSON.parse(value);
      if (typeof parsed === 'string') return parsed;
    } catch {
      // Unquoted scalar fields remain valid persisted input.
    }
  }
  return value.replace(/^['"]|['"]$/g, '');
}

function isRequirementStatus(value: string): value is RequirementStatus {
  return requirementStatuses.some((status) => status.id === value);
}

function parseSection(title: string, content: string): RequirementSection {
  const images = readImages(content);
  const description = content
    .replace(imagePattern, '')
    .replace(/\r?\n{3,}/g, '\n\n')
    .trim();

  return { title, description, images };
}

function normalizeAssetPath(path: string): string {
  return path.replace(/^\.\//, '').trim();
}

function imageName(path: string): string {
  const filename = path.split('/').at(-1) ?? '';
  return filename.replace(/\.[^.]+$/, '').trim() || '需求图示';
}

function imageAlt(alt: string | undefined, path: string): string {
  const name = alt?.trim();
  return name && name !== '需求图示' ? name : imageName(path);
}

function readImages(content: string): readonly RequirementImage[] {
  const markdownImages = Array.from(content.matchAll(imagePattern)).map(
    (match) => {
      const path = normalizeAssetPath(match[2] ?? '');
      return { alt: imageAlt(match[1], path), path };
    },
  );
  const images = markdownImages.filter((image) => image.path);
  return images.filter(
    (image, index) =>
      images.findIndex((candidate) => candidate.path === image.path) === index,
  );
}

export function parseRequirementMarkdown(
  markdown: string,
): RequirementDocument {
  const match = markdown.match(frontMatterPattern);
  if (!match) {
    throw new Error('Requirement Markdown must start with front matter.');
  }

  const fields = readFrontMatter(match[1] ?? '');
  const id = fields.id;
  const title = fields.title;
  const status = fields.status;
  const updatedAt = fields.updatedAt;
  const createdAt = fields.createdAt ?? updatedAt;
  const updatedAtTimestamp = Date.parse(updatedAt ?? '');

  if (
    !id ||
    !title ||
    !status ||
    !updatedAt ||
    !createdAt ||
    !isRequirementStatus(status)
  ) {
    throw new Error('Requirement front matter is missing a required field.');
  }
  if (Number.isNaN(updatedAtTimestamp)) {
    throw new Error('Requirement updatedAt must be an ISO 8601 timestamp.');
  }

  const body = match[2] ?? '';
  const headings = Array.from(body.matchAll(/^##\s+(.+)\r?$/gm));
  const sections = headings.length
    ? [
        ...(body.slice(0, headings[0]?.index ?? 0).trim()
          ? [parseSection('', body.slice(0, headings[0]?.index ?? 0))]
          : []),
        ...headings.map((heading, index) => {
          const contentStart = (heading.index ?? 0) + heading[0].length;
          const contentEnd = headings[index + 1]?.index ?? body.length;
          return parseSection(
            heading[1]?.trim() ?? '未命名单元',
            body.slice(contentStart, contentEnd),
          );
        }),
      ]
    : [parseSection('', body)];

  return {
    id,
    title,
    status,
    createdAt,
    updatedAt,
    updatedAtTimestamp,
    sections,
  };
}

export function createEmptyRequirementSnapshot(): RequirementSnapshot {
  return { statuses: requirementStatuses, items: [] };
}
