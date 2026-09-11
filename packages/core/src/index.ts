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
  summary: string;
  sections: readonly RequirementSection[];
}>;

export type RequirementSnapshot = Readonly<{
  statuses: readonly RequirementStatusDefinition[];
  items: readonly RequirementDocument[];
}>;

export type RequirementDraft = Readonly<{
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  images: readonly RequirementImage[];
}>;

export type HistoricalRequirementTimeline = Readonly<{
  createdAt: string;
  updatedAt: string;
}>;

export function createRequirementMarkdown(
  document: RequirementDocument,
): string {
  const sections = document.sections
    .map((section) => {
      const heading = section.title ? `## ${section.title}\n\n` : '';
      const images = section.images
        .map((image) => `![${image.alt}](${image.path})`)
        .join('\n\n');
      return [heading, images, section.description]
        .filter(Boolean)
        .join('\n\n');
    })
    .join('\n\n');
  return `---\nid: ${document.id}\ntitle: ${document.title}\nstatus: ${document.status}\ncreatedAt: ${document.createdAt}\nupdatedAt: ${document.updatedAt}\nsummary: ${document.summary}\n---\n\n${sections}\n`;
}

const frontMatterPattern = /^---\r?\n([\s\S]*?)\r?\n---\r?\n?([\s\S]*)$/;
const imagePattern = /!\[([^\]]*)\]\(([^\s)]+)(?:\s+"[^"]*")?\)/g;
const htmlImagePattern = /<img\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi;
const placeholderImagePattern =
  /占位图[：:]\s*([^\r\n<|]+?\.(?:png|jpe?g|webp|gif))/gi;
const historicalMediaMarkupPattern = /\[\[[\s\S]*?copy="([\s\S]*?)"\]\]/gi;

function readFrontMatter(frontMatter: string): Record<string, string> {
  const fields: Record<string, string> = {};

  for (const line of frontMatter.split(/\r?\n/)) {
    const separatorIndex = line.indexOf(':');
    if (separatorIndex <= 0) {
      continue;
    }

    const key = line.slice(0, separatorIndex).trim();
    const value = line.slice(separatorIndex + 1).trim();
    fields[key] = value.replace(/^['"]|['"]$/g, '');
  }

  return fields;
}

function isRequirementStatus(value: string): value is RequirementStatus {
  return requirementStatuses.some((status) => status.id === value);
}

function parseSection(title: string, content: string): RequirementSection {
  const images = readImages(content);
  const description = content
    .replace(historicalMediaMarkupPattern, '$1')
    .replace(imagePattern, '')
    .replace(htmlImagePattern, '')
    .replace(placeholderImagePattern, '')
    .replace(/\r?\n{3,}/g, '\n\n')
    .trim();

  return { title, description, images };
}

function normalizeAssetPath(path: string): string {
  return path.replace(/^\.\//, '').trim();
}

function readImages(content: string): readonly RequirementImage[] {
  const markdownImages = Array.from(content.matchAll(imagePattern)).map(
    (match) => ({
      alt: match[1]?.trim() || '需求图示',
      path: normalizeAssetPath(match[2] ?? ''),
    }),
  );
  const htmlImages = Array.from(content.matchAll(htmlImagePattern)).map(
    (match) => ({
      alt: '需求图示',
      path: normalizeAssetPath(match[1] ?? ''),
    }),
  );
  const placeholderImages = Array.from(
    content.matchAll(placeholderImagePattern),
  ).map((match) => {
    const filename = normalizeAssetPath(match[1] ?? '');
    return {
      alt: filename.replace(/\.[^.]+$/, '') || '需求图示',
      path: `assets/${filename}`,
    };
  });

  const images = [
    ...markdownImages,
    ...htmlImages,
    ...placeholderImages,
  ].filter((image) => image.path);
  return images.filter(
    (image, index) =>
      images.findIndex((candidate) => candidate.path === image.path) === index,
  );
}

function toPlainText(content: string): string {
  return content
    .replace(historicalMediaMarkupPattern, '$1')
    .replace(imagePattern, '')
    .replace(htmlImagePattern, '')
    .replace(placeholderImagePattern, '')
    .replace(/<br\s*\/?\s*>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/\r?\n{3,}/g, '\n\n')
    .trim();
}

function stripLegacyRequirementNumber(title: string): string {
  return title.replace(/^\d+(?:\.\d+)*\s+/, '').trim();
}

function legacyTitleFromMarkdown(markdown: string): string {
  return markdown.match(/^#\s+(.+)\r?$/m)?.[1]?.trim() || '历史需求';
}

function isoDateToTimestamp(value: string): number | undefined {
  const match = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$/u.exec(value.trim());
  if (!match) return undefined;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const day = Number(match[3]);
  const timestamp = Date.UTC(year, month - 1, day);
  const date = new Date(timestamp);
  return date.getUTCFullYear() === year &&
    date.getUTCMonth() === month - 1 &&
    date.getUTCDate() === day
    ? timestamp
    : undefined;
}

function versionRecordDates(markdown: string): readonly number[] {
  let dateColumn: number | undefined;
  const timestamps: number[] = [];

  for (const line of markdown.split(/\r?\n/)) {
    if (!/^\s*\|/.test(line)) {
      dateColumn = undefined;
      continue;
    }
    const cells = line
      .trim()
      .replace(/^\||\|$/g, '')
      .split('|')
      .map((cell) => cell.trim());
    const headerIndex = cells.indexOf('日期');
    if (headerIndex >= 0) {
      dateColumn = headerIndex;
      continue;
    }
    if (dateColumn === undefined) continue;
    const date = cells[dateColumn]?.match(
      /\d{4}[-/.]\d{1,2}[-/.]\d{1,2}/u,
    )?.[0];
    if (!date) continue;
    const timestamp = isoDateToTimestamp(date);
    if (timestamp !== undefined) timestamps.push(timestamp);
  }

  return timestamps;
}

export function readHistoricalRequirementTimeline(
  markdown: string,
  fallbackUpdatedAt: string,
): HistoricalRequirementTimeline {
  const versionDates = versionRecordDates(markdown);
  const titleDate = legacyTitleFromMarkdown(markdown).match(
    /\d{4}[-/.]\d{1,2}[-/.]\d{1,2}/u,
  )?.[0];
  const titleTimestamp = titleDate ? isoDateToTimestamp(titleDate) : undefined;
  const fallbackTimestamp = Date.parse(fallbackUpdatedAt);
  if (Number.isNaN(fallbackTimestamp)) {
    throw new Error('Historical requirement fallback time must be ISO 8601.');
  }
  const timestamps = versionDates.length
    ? versionDates
    : titleTimestamp === undefined
      ? [fallbackTimestamp]
      : [titleTimestamp];
  const createdAtTimestamp = Math.min(...timestamps);
  const updatedAtTimestamp = Math.max(...timestamps);

  return {
    createdAt: new Date(createdAtTimestamp).toISOString(),
    updatedAt: new Date(updatedAtTimestamp).toISOString(),
  };
}

function extractLegacyRequirementDetail(content: string): string {
  const detailRow = content
    .split(/\r?\n/)
    .find((line) => /^\s*\|\s*需求详情\s*\|/.test(line));
  if (!detailRow) {
    return content;
  }

  return detailRow
    .replace(/^\s*\|\s*需求详情\s*\|\s*/, '')
    .replace(/\|\s*$/, '')
    .trim();
}

export function parseHistoricalRequirementMarkdown(
  markdown: string,
  options: Readonly<{
    idPrefix: string;
    updatedAt: string;
    createdAt?: string;
  }>,
): readonly RequirementDocument[] {
  const detailHeading =
    /^##\s+(?:[一二三四五六七八九十]+、\s*)?需求详情\s*\r?$/gm;
  const detailMatch = detailHeading.exec(markdown);
  if (!detailMatch || detailMatch.index === undefined) {
    return [];
  }

  const detailStart = detailMatch.index + detailMatch[0].length;
  const remaining = markdown.slice(detailStart);
  const nextHeading = /^##\s+/m.exec(remaining);
  const detailBody = remaining.slice(0, nextHeading?.index);
  const requirementHeadings = Array.from(
    detailBody.matchAll(/^###\s+(.+)\r?$/gm),
  );
  const updatedAtTimestamp = Date.parse(options.updatedAt);
  if (Number.isNaN(updatedAtTimestamp)) {
    throw new Error('Legacy 需求文档 updatedAt must be an ISO 8601 timestamp.');
  }

  const blocks = requirementHeadings.length
    ? requirementHeadings.map((heading, index) => ({
        title: heading[1]?.trim() || '未命名需求',
        content: detailBody.slice(
          (heading.index ?? 0) + heading[0].length,
          requirementHeadings[index + 1]?.index ?? detailBody.length,
        ),
      }))
    : [{ title: legacyTitleFromMarkdown(markdown), content: detailBody }];

  return blocks.map((block, index) => {
    const detailContent = extractLegacyRequirementDetail(block.content);
    const description = toPlainText(detailContent);
    return {
      id: `${options.idPrefix}-${index + 1}`,
      title: stripLegacyRequirementNumber(block.title),
      status: 'defined',
      createdAt: options.createdAt ?? options.updatedAt,
      updatedAt: options.updatedAt,
      updatedAtTimestamp,
      summary:
        description.split(/\r?\n/).find(Boolean)?.slice(0, 120) ||
        '历史 需求文档 导入',
      sections: [
        {
          title: '需求详情',
          description,
          images: readImages(detailContent),
        },
      ],
    };
  });
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
  const summary = fields.summary
    ?.replace(historicalMediaMarkupPattern, '$1')
    .replace(/^\[\[[\s\S]*$/, '历史需求');
  const updatedAtTimestamp = Date.parse(updatedAt ?? '');

  if (
    !id ||
    !title ||
    !status ||
    !updatedAt ||
    !createdAt ||
    !summary ||
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
    summary,
    sections,
  };
}

export function createEmptyRequirementSnapshot(): RequirementSnapshot {
  return { statuses: requirementStatuses, items: [] };
}
