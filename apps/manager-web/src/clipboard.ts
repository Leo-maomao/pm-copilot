/**
 * Copy text to the clipboard.
 *
 * `navigator.clipboard` only exists in secure contexts, so the manager opened
 * over the LAN (`http://<host>:57391`) falls back to the legacy
 * `document.execCommand('copy')` path. Returns whether the text was written.
 */
export async function copyTextToClipboard(text: string): Promise<boolean> {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to the legacy path below.
    }
  }
  const scratch = document.createElement('textarea');
  scratch.value = text;
  scratch.setAttribute('readonly', '');
  scratch.style.position = 'fixed';
  scratch.style.insetBlockStart = '-1000px';
  scratch.style.opacity = '0';
  document.body.append(scratch);
  scratch.select();
  scratch.setSelectionRange(0, scratch.value.length);
  try {
    return document.execCommand('copy');
  } catch {
    return false;
  } finally {
    scratch.remove();
  }
}
