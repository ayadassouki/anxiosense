/**
 * Crisis override report.
 *
 * Composed here rather than inline in the route so the exact wording is
 * single-sourced and can be pinned by tests — the crisis guidance is the most
 * safety-critical text in the product and must not drift.
 *
 * The crisis override deliberately bypasses the entire AI pipeline: no
 * Assessment Overview, no Supporting Findings, no Recommendation, no Evidence
 * Agreement, no Limitations, no Clinician Summary. Only the safety alert and,
 * for traceability, the submission that triggered it.
 *
 * The Submitted Input section is added through the SAME `insertSubmittedInput`
 * used by normal reports, so sanitisation, fencing, line-break preservation and
 * markdown/HTML containment are identical by construction rather than by
 * duplicated logic.
 */

import { CRISIS_RESPONSE_TEXT } from './safetyCheck.js';
import { insertSubmittedInput, type SubmissionMode } from './submittedInput.js';

/**
 * The crisis report body, excluding the Submitted Input section.
 * Wording is unchanged from the original inline template — do not edit without
 * supervisory sign-off; `crisisReport.test.ts` pins it verbatim.
 */
export const CRISIS_REPORT_BODY =
  `# AnxioSense Screening Support Report\n\n` +
  `## Important — Safety Alert\n\n` +
  `${CRISIS_RESPONSE_TEXT}\n\n` +
  `---\n\n` +
  `*This screening tool is not a crisis service. If you are in immediate danger, ` +
  `please call your local emergency number now.*\n\n` +
  `*This report has not been generated. When a safety concern is identified, ` +
  `your wellbeing takes priority. Please seek support now.*`;

/**
 * Builds the crisis override report.
 *
 * The Submitted Input section lands immediately after the title and before the
 * Safety Alert, because `insertSubmittedInput` anchors on the leading `# `
 * heading and the alert is the next section.
 *
 * @param submittedText  The RAW submission, exactly as the user typed it.
 * @param mode           Journal or social-media, used only for the caption label.
 */
export function buildCrisisReport(submittedText: string, mode: SubmissionMode): string {
  return insertSubmittedInput(CRISIS_REPORT_BODY, submittedText, mode);
}
