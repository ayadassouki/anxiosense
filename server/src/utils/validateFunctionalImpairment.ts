/**
 * Server-side validation for the functionalImpairment field.
 *
 * Design:
 *   - Self-assessment (journal) mode: MUST supply one of the four valid values.
 *   - Social-media mode: impairment is NEVER collected — any submitted value is
 *     silently discarded and null is returned, preventing client-side spoofing.
 *   - Crisis override (safety agent path): always stores null; this function is
 *     not called on the crisis path (the safety check fires first and returns
 *     early before this validation is reached).
 *
 * Extracted into this module so it can be unit-tested independently of the
 * full HTTP route (which requires a running Mastra instance and SQLite DB).
 */

export type FunctionalImpairmentValue =
  | 'not_difficult_at_all'
  | 'somewhat_difficult'
  | 'very_difficult'
  | 'extremely_difficult';

export const VALID_IMPAIRMENTS: ReadonlySet<FunctionalImpairmentValue> = new Set([
  'not_difficult_at_all',
  'somewhat_difficult',
  'very_difficult',
  'extremely_difficult',
]);

export type ImpairmentValidationResult =
  | { ok: true;  value: FunctionalImpairmentValue | null }
  | { ok: false; message: string };

/**
 * Validates and normalises the functionalImpairment field for a given mode.
 *
 * @param mode  The assessment mode from the request body.
 * @param raw   The raw functionalImpairment value from the request body (may be
 *              undefined/null/string/any).
 * @returns     { ok: true, value } on success or { ok: false, message } on failure.
 *
 * Social-media mode always returns { ok: true, value: null } regardless of what
 * the client sends — the field is irrelevant and must not be persisted.
 */
export function validateFunctionalImpairment(
  mode: 'journal' | 'social-media',
  raw: unknown,
): ImpairmentValidationResult {
  if (mode === 'social-media') {
    // Social-media never collects impairment — force null regardless of client input.
    return { ok: true, value: null };
  }

  // Self-assessment mode: require a valid value.
  if (raw === undefined || raw === null || raw === '') {
    return {
      ok: false,
      message: 'functionalImpairment is required for self-assessment mode.',
    };
  }

  if (typeof raw !== 'string') {
    return {
      ok: false,
      message: 'functionalImpairment must be a string.',
    };
  }

  if (!VALID_IMPAIRMENTS.has(raw as FunctionalImpairmentValue)) {
    return {
      ok: false,
      message: `Invalid functionalImpairment value "${raw}". ` +
               `Accepted: ${[...VALID_IMPAIRMENTS].join(', ')}.`,
    };
  }

  return { ok: true, value: raw as FunctionalImpairmentValue };
}
