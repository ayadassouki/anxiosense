/**
 * Submitted Input section builder.
 *
 * Adds the user's original submission to the generated report so the reader can
 * see exactly what was analysed. Composed in the Express layer because that is
 * the only place the RAW submission exists — the Mastra workflow receives
 * `analysisText` (emoji-replaced and, in social-media mode, normalised), not the
 * text the user typed.
 *
 * ── Ordering contract ────────────────────────────────────────────────────────
 * This must run AFTER concern-pattern/referral derivation, AFTER the grounding
 * evaluation and AFTER summary extraction. Inserting earlier would place the
 * submission inside the text those steps read, which would corrupt the grounding
 * score (lexical overlap with the user's own words would approach 1.0) and could
 * change the extracted summary. Nothing here influences any assessment output.
 *
 * ── Injection safety ─────────────────────────────────────────────────────────
 * The report renderers already HTML-escape every value they interpolate, so
 * script injection is not the exposure. The real risk is MARKDOWN STRUCTURE
 * injection: a submitted line beginning "## " or "1. " would be parsed by
 * ReportPage's parseSections as a genuine report section, letting a user forge
 * a "Recommendation" heading inside their own report.
 *
 * The submission is therefore emitted inside a fenced block. The fence is made
 * longer than the longest backtick run in the submission, so the text cannot
 * close its own fence, and the renderers treat everything between the fences as
 * preformatted text — no headings, no bullets, no emphasis.
 */

export type SubmissionMode = 'journal' | 'social-media';

/** Heading used for the section. Also the idempotency marker. */
export const SUBMITTED_INPUT_HEADING = '## Submitted Input';

/**
 * Normalises line endings and removes control characters.
 *
 * Deliberately does NOT alter the visible text: no trimming of internal
 * whitespace, no case changes, no truncation. Submissions are already capped at
 * 5,000 characters by validateText, and blank lines and indentation are part of
 * how the entry was written.
 */
export function normaliseSubmittedText(text: string): string {
  return text
    .replace(/\r\n?/g, '\n')
    // Strip C0/C1 control characters, keeping newline (\n) and tab (\t).
    .replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F-\u009F]/g, '');
}

/**
 * Returns a fence long enough that `text` cannot terminate it early.
 * CommonMark allows a closing fence only when it is at least as long as the
 * opening one, so opening with (longest run + 1) backticks is always safe.
 */
export function fenceFor(text: string): string {
  const runs = text.match(/`+/g) ?? [];
  const longest = runs.reduce((max, run) => Math.max(max, run.length), 0);
  return '`'.repeat(Math.max(3, longest + 1));
}

/** Builds the Submitted Input markdown section. */
export function buildSubmittedInputSection(text: string, mode: SubmissionMode): string {
  const body = normaliseSubmittedText(text);
  const fence = fenceFor(body);
  const label = mode === 'social-media' ? 'Social media post' : 'Journal entry';

  return [
    SUBMITTED_INPUT_HEADING,
    '',
    `*${label} — ${body.length.toLocaleString('en-CA')} characters, reproduced exactly as submitted.*`,
    '',
    fence,
    body,
    fence,
  ].join('\n');
}

/**
 * Inserts the Submitted Input section immediately after the report title, so it
 * appears near the beginning and before the Assessment Overview.
 *
 * Idempotent: a report that already carries the section is returned unchanged,
 * so re-processing a stored report cannot duplicate it. Empty or whitespace-only
 * submissions are skipped rather than producing an empty block.
 */
export function insertSubmittedInput(
  report: string,
  submittedText: string,
  mode: SubmissionMode
): string {
  if (!submittedText || !submittedText.trim()) return report;
  if (report.includes(SUBMITTED_INPUT_HEADING)) return report;

  const section = buildSubmittedInputSection(submittedText, mode);
  const titleMatch = report.match(/^#\s+[^\n]*\n/);

  if (!titleMatch) return `${section}\n\n${report}`;

  const afterTitle = titleMatch[0].length;
  return (
    report.slice(0, afterTitle) +
    '\n' + section + '\n\n' +
    report.slice(afterTitle).replace(/^\n+/, '')
  );
}
