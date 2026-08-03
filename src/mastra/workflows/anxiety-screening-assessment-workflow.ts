import { knowledgeEvidenceValidationStep } from './knowledge-evidence-validation-step';
import { assessmentClaimConstructionStep } from './assessment-claim-construction-step';
import { knowledgeEvidenceRetrievalStep } from './knowledge-evidence-retrieval-step';
import { createStep, createWorkflow } from '@mastra/core/workflows';
import { z } from 'zod';
import { loadAgentInstructions, type PromptStrategy } from '../utils/prompt-strategy-loader';
import { ValidationAgentOutputSchema } from '../../kb/types';
import { writeSession, readSession, clearSession, accumulateTokenUsage, type SessionData } from '../utils/anxiety-assessment-session-store';
import { exportWorkflowRun } from '../utils/workflow-evaluation-run-exporter';
import { computeGad7Score, formatGad7ForReport } from '../utils/gad7-assessment-scorer';
import {
    getPatientRecommendation,
    getStandardClinicalRecommendation,
    getFunctionalImpairmentLabel,
    buildRecommendationDirective,
    renderRecommendationPrompt,
    enforceRecommendation,
    type FunctionalImpairment,
    type ConcernPattern,
    type ReferralLevel,
} from '../utils/clinical-support-recommendation-policy';

// ── Input schema ─────────────────────────────────────────────────────────────

const inputSchema = z.object({
    /**
     * Selects the analysis pipeline:
     *   - "journal"       → personal journal entry; GAD-7 supported; full referral.
     *   - "social-media"  → pasted Reddit/social posts; GAD-7 bypassed; extra disclaimer.
     */
    mode: z.enum(['journal', 'social-media']).default('journal'),

    /** The free-text content to analyse. */
    userText: z.string(),

    /**
     * Optional GAD-7 answers — exactly 7 integers, each 0–3.
     * Only used in "journal" mode. Ignored in "social-media" mode.
     */
    gad7Answers: z
        .array(z.number().int().min(0).max(3))
        .length(7)
        .optional(),

    /**
     * When true, the report includes a Clinician Details section with the raw
     * GAD-7 score, clinical severity label, and per-item breakdown.
     * Hidden from standard user-facing output.
     */
    clinicianMode: z.boolean().optional().default(false),

    /**
     * Functional impairment response — the GAD-7 standard follow-up question:
     * "How difficult have these problems made it for you to do your work, take
     * care of things at home, or get along with other people?"
     *
     * Only used in journal mode (alongside GAD-7 answers).
     * Does NOT change the GAD-7 score — only personalises the recommendation.
     * Source: Spitzer et al. (2006); AnxioSense supervisory guidance (July 2026).
     */
    functionalImpairment: z.enum([
        'not_difficult_at_all',
        'somewhat_difficult',
        'very_difficult',
        'extremely_difficult',
    ]).optional(),

    /**
     * Prompting strategy to apply to all agents in this workflow run.
     * Loaded from prompts/{agentName}/{strategy}.md at generate() time.
     *   zero-shot      — task + schema only
     *   zero-shot-cot  — adds chain-of-thought reasoning procedure
     *   one-shot-cot   — adds reasoning procedure + worked example (default)
     */
    strategy: z.enum(['zero-shot', 'zero-shot-cot', 'one-shot-cot']).optional().default('one-shot-cot'),
});

// ── Shared step schemas ───────────────────────────────────────────────────────

/**
 * Which upstream provider OpenRouter actually routed this call to (DeepInfra, Groq,
 * Novita, Google, …). Recorded per agent call so a routing change is visible in the
 * data instead of being an invisible confound.
 *
 * Context: on 2026-08-03 the `Google` upstream was found to return token-dropped
 * output for meta-llama/llama-4-scout — 21/21 corrupted vs 179/179 clean across the
 * other three upstreams. Routing is now pinned in model-provider.ts; this field is
 * how we verify the pin held for every row.
 *
 * Only the OpenAI-compatible Chat Completions shape carries `provider`; returns
 * undefined for providers or endpoints that do not.
 */
function extractUpstreamProvider(response: unknown): string | undefined {
    const body = (response as { response?: { body?: unknown } })?.response?.body;
    if (!body) return undefined;
    try {
        const parsed = typeof body === 'string' ? JSON.parse(body) : body;
        const p = (parsed as { provider?: unknown })?.provider;
        return typeof p === 'string' && p.length > 0 ? p : undefined;
    } catch {
        return undefined;
    }
}

const agentOutputSchema = z.object({
    result: z.string(),
    /** Wall-clock duration of agent.generate() in milliseconds. */
    durationMs: z.number(),
    /** Token usage reported by the provider for this generate() call. */
    inputTokens:  z.number().optional(),
    outputTokens: z.number().optional(),
    /** Upstream provider OpenRouter routed this call to (see extractUpstreamProvider). */
    upstreamProvider: z.string().optional(),
});

const combinedAnalysisSchema = z.object({
    mode: z.enum(['journal', 'social-media']),
    userText: z.string(),
    emotionAnalysis: z.string(),
    symptomAnalysis: z.string(),
    contextAnalysis: z.string(),
    referralAnalysis: z.string(),
    /** Per-agent generate() durations for session timing instrumentation. */
    agentTimingsMs: z.object({
        emotion: z.number(),
        symptom: z.number(),
        context: z.number(),
        referral: z.number(),
    }),
    /** Summed token usage from the four parallel agents (to be added to session in Map 2). */
    parallelTokenUsage: z.object({
        inputTokens:  z.number(),
        outputTokens: z.number(),
    }).optional(),
});

const validatedAnalysisSchema = combinedAnalysisSchema.extend({
    validationAnalysis: z.string(),
});

const finalReportSchema = z.object({
    finalReport: z.string(),
    /**
     * Aggregate token usage across all agent.generate() calls in this run.
     * Parallel-step usage is summed in Map 1 and written to the session store.
     * Report-step usage is added here.  Values come from LanguageModelV2Usage
     * (inputTokens / outputTokens); undefined if the provider did not return them.
     */
    tokenUsage: z.object({
        inputTokens:  z.number(),
        outputTokens: z.number(),
    }).optional(),
    /**
     * Observable internal quality flags accumulated during this run.
     * Included in the workflow output so the evaluation runner can record them
     * without re-running.  All flags default to false on the normal path.
     */
    qualityFlags: z.object({
        agent_json_parse_failed:     z.boolean(),
        fallback_claim_injected:     z.boolean(),
        referral_risk_fallback_used: z.boolean(),
        recommendation_rejected:     z.boolean(),
    }).optional(),
});

// ── Mode context helpers ──────────────────────────────────────────────────────

function modePrefix(mode: 'journal' | 'social-media'): string {
    if (mode === 'social-media') {
        return (
            'CONTEXT: The following text was sourced from social media (e.g. Reddit). ' +
            'Treat it as self-reported content from an unknown author describing their ' +
            'own experiences. Do NOT assume clinical intent or structured disclosure. ' +
            'Be appropriately cautious about any inferences.\n\n'
        );
    }
    return (
        'CONTEXT: The following text is a personal journal entry written by the user ' +
        'to describe how they have been feeling recently.\n\n'
    );
}

// ── Parallel extraction steps ─────────────────────────────────────────────────

const emotionStep = createStep({
    id: 'emotion-analysis-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('emotionAgent');
        if (!agent) throw new Error('Emotion agent not found');
        const strategy = (inputData.strategy ?? 'one-shot-cot') as PromptStrategy;
        const instructions = loadAgentInstructions('emotion', strategy) ?? undefined;
        const t0 = Date.now();
        const response = await agent.generate(
            modePrefix(inputData.mode) + inputData.userText,
            { instructions },
        );
        const usage = response.usage;
        console.log(`[usage] emotion: input=${usage?.inputTokens ?? '?'} output=${usage?.outputTokens ?? '?'}`);
        return { result: response.text, durationMs: Date.now() - t0, inputTokens: usage?.inputTokens, outputTokens: usage?.outputTokens, upstreamProvider: extractUpstreamProvider(response) };
    },
});

const symptomStep = createStep({
    id: 'symptom-extraction-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('symptomAgent');
        if (!agent) throw new Error('Symptom agent not found');
        const strategy = (inputData.strategy ?? 'one-shot-cot') as PromptStrategy;
        const instructions = loadAgentInstructions('symptom', strategy) ?? undefined;
        const t0 = Date.now();
        const response = await agent.generate(
            modePrefix(inputData.mode) + inputData.userText,
            { instructions },
        );
        const usage = response.usage;
        console.log(`[usage] symptom: input=${usage?.inputTokens ?? '?'} output=${usage?.outputTokens ?? '?'}`);
        return { result: response.text, durationMs: Date.now() - t0, inputTokens: usage?.inputTokens, outputTokens: usage?.outputTokens, upstreamProvider: extractUpstreamProvider(response) };
    },
});

const contextStep = createStep({
    id: 'context-reasoning-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('contextAgent');
        if (!agent) throw new Error('Context agent not found');
        const strategy = (inputData.strategy ?? 'one-shot-cot') as PromptStrategy;
        const instructions = loadAgentInstructions('context', strategy) ?? undefined;
        const t0 = Date.now();
        const response = await agent.generate(
            modePrefix(inputData.mode) + inputData.userText,
            { instructions },
        );
        const usage = response.usage;
        console.log(`[usage] context: input=${usage?.inputTokens ?? '?'} output=${usage?.outputTokens ?? '?'}`);
        return { result: response.text, durationMs: Date.now() - t0, inputTokens: usage?.inputTokens, outputTokens: usage?.outputTokens, upstreamProvider: extractUpstreamProvider(response) };
    },
});

const referralStep = createStep({
    id: 'referral-safety-step',
    inputSchema,
    outputSchema: agentOutputSchema,
    execute: async ({ inputData, mastra }) => {
        const agent = mastra?.getAgent('referralAgent');
        if (!agent) throw new Error('Referral agent not found');

        // Social-media mode: prepend extra conservatism instruction to the referral agent.
        const socialMediaNote =
            inputData.mode === 'social-media'
                ? 'IMPORTANT: This text is from social media, not a direct clinical disclosure. ' +
                  'Be conservative — default to "low" or "moderate" unless there are very explicit ' +
                  'safety signals in the text itself.\n\n'
                : '';

        const strategy = (inputData.strategy ?? 'one-shot-cot') as PromptStrategy;
        const instructions = loadAgentInstructions('referral', strategy) ?? undefined;
        const t0 = Date.now();
        const response = await agent.generate(
            socialMediaNote + modePrefix(inputData.mode) + inputData.userText,
            { instructions },
        );
        const usage = response.usage;
        console.log(`[usage] referral: input=${usage?.inputTokens ?? '?'} output=${usage?.outputTokens ?? '?'}`);
        return { result: response.text, durationMs: Date.now() - t0, inputTokens: usage?.inputTokens, outputTokens: usage?.outputTokens, upstreamProvider: extractUpstreamProvider(response) };
    },
});

// ── Report step ───────────────────────────────────────────────────────────────

const reportStep = createStep({
    id: 'assessment-report-step',
    inputSchema: ValidationAgentOutputSchema,
    outputSchema: finalReportSchema,
    execute: async ({ inputData, mastra }) => {
        let finalReport: string;

        if (inputData.riskLevel === 'urgent') {
            finalReport = `# AnxioSense Screening Support Report

## Important — Urgent Safety Notice

Based on what you shared, there may be an immediate safety concern that requires urgent attention.

**This screening tool is not able to provide crisis support.** Please reach out for help right now:

- Contact a crisis line in your country or region
- Go to your nearest emergency department, or call emergency services (911 / 999 / 112)
- Reach out immediately to a trusted person who can be with you

---

*This report has not been generated. When an immediate safety concern is present, your wellbeing takes priority over a screening summary. Please seek support now.*

*This tool is intended for screening support only and is not a clinical service.*`;

            // Clear session data — urgent path short-circuits before the export block.
            // Timing data is unavailable on this path; just clean up memory.
            try { clearSession(inputData.sessionId); } catch { /* non-fatal */ }

        } else {
            const agent = mastra?.getAgent('reportAgent');
            if (!agent) throw new Error('Report agent not found');

            // Read session data — includes mode, clinicianMode, gad7 fields, retrieval output
            const session = readSession(inputData.sessionId);
            const mode                 = session?.mode                 ?? 'journal';
            const clinicianMode        = session?.clinicianMode        ?? false;
            const gad7Block            = session?.gad7Block            ?? null;
            const gad7ConcernPattern   = session?.gad7ConcernPattern   ?? null;
            const discordanceNote      = session?.discordanceNote      ?? null;
            const functionalImpairment = session?.functionalImpairment ?? null;

            // ── Mode label ────────────────────────────────────────────────────
            const modeLabel =
                mode === 'social-media' ? 'Social Media Analysis' : 'Journal / Self-Report';

            // ── Group validated claims by agent for structured LLM input ──────
            // Claims are passed as semantic labels, not raw user sentences,
            // so the LLM can rewrite them as clinical findings.
            const emotionClaims  = inputData.claimValidations
                .filter(v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'emotion')
                .map(v => v.claimText);
            const symptomClaims  = inputData.claimValidations
                .filter(v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'symptom')
                .map(v => v.claimText);
            const contextClaims  = inputData.claimValidations
                .filter(v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'context')
                .map(v => v.claimText);

            const claimsForPrompt = [
                `Emotional signals: ${emotionClaims.length  > 0 ? emotionClaims.join('; ')  : 'none identified'}`,
                `Anxiety indicators: ${symptomClaims.length > 0 ? symptomClaims.join('; ')  : 'none identified'}`,
                `Contextual factors: ${contextClaims.length > 0 ? contextClaims.join('; ')  : 'none identified'}`,
            ].join('\n');

            // ── Evidence Agreement — based on concern-level comparison ─────────
            // Compares validated text signal strength (symptom claim count) against
            // the GAD-7 concern band, or falls back to KB support ratio for social-media.
            const validatedSymptomClaims = inputData.claimValidations.filter(
                v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'symptom'
            );

            let evidenceAgreement: 'High' | 'Moderate' | 'Low';
            let agreementText: string;

            if (discordanceNote === 'high_gad7_low_text') {
                evidenceAgreement = 'Low';
                agreementText     = 'The questionnaire responses indicated more concern than the written text alone suggested.';
            } else if (discordanceNote === 'low_gad7_high_text') {
                evidenceAgreement = 'Low';
                agreementText     = 'The written text reflected more concern indicators than the questionnaire responses.';
            } else if (gad7ConcernPattern) {
                // Journal mode with GAD-7: compare concern bands numerically
                const levelToNum: Record<string, number> = {
                    'Minimal Concern Pattern':  0,
                    'Mild Concern Pattern':     1,
                    'Elevated Concern Pattern': 2,
                    'High Concern Pattern':     3,
                };
                const gad7Num = levelToNum[gad7ConcernPattern] ?? 1;
                // Text level: derived from validated symptom claim count
                const textNum = validatedSymptomClaims.length === 0 ? 0
                    : validatedSymptomClaims.length <= 2              ? 1
                    : validatedSymptomClaims.length <= 4              ? 2
                    :                                                    3;
                const diff = Math.abs(gad7Num - textNum);
                if (diff === 0) {
                    evidenceAgreement = 'High';
                    agreementText     = 'The questionnaire responses and written text were generally consistent.';
                } else if (diff === 1) {
                    evidenceAgreement = 'Moderate';
                    agreementText     = 'Some indicators were present, but the available text provided limited detail.';
                } else {
                    evidenceAgreement = 'Low';
                    agreementText     = 'The questionnaire responses and written text did not fully align.';
                }
            } else {
                // Social media or journal without GAD-7: compare text against KB
                const totalClaims    = inputData.claimValidations.length;
                const supportedCount = inputData.claimValidations.filter(v => v.supportStatus === 'supported').length;
                const partialCount   = inputData.claimValidations.filter(v => v.supportStatus === 'partially_supported').length;
                if (totalClaims === 0) {
                    evidenceAgreement = 'Low';
                    agreementText     = 'Insufficient information was available to assess agreement across sources.';
                } else {
                    const supportRatio = (supportedCount + partialCount * 0.5) / totalClaims;
                    evidenceAgreement  = supportRatio >= 0.6 ? 'High' : 'Moderate';
                    agreementText      = supportRatio >= 0.6
                        ? 'The identified indicators were broadly consistent with the clinical guidance used.'
                        : 'Some indicators were present, but the available text provided limited detail.';
                }
            }

            // ── Recommendation instruction (from PDF lookup table) ────────────
            // When GAD-7 + functional impairment are both available, use the
            // exact patient-facing text from the specification lookup table.
            // Otherwise fall back to concern-pattern-based instructions.
            const concernPatternForReport = gad7ConcernPattern
                ?? (inputData.riskLevel === 'urgent'   ? 'High Concern Pattern'
                  : inputData.riskLevel === 'moderate' ? 'Elevated Concern Pattern'
                  :                                      'Minimal Concern Pattern');

            const gad7Severity = session?.gad7Severity ?? null;

            // ── Recommendation directive ──────────────────────────────────────
            // The anchor is selected exactly as before: the severity × impairment
            // lookup when journal mode supplied both, otherwise the concern-pattern
            // anchor. Severity, concern pattern and referral level are already
            // decided here — the LLM never chooses any of them, it only writes
            // context around a fixed sentence, and enforceRecommendation() below
            // restores the anchor if it strays.
            const recommendationDirective = buildRecommendationDirective({
                mode,
                severity:       gad7Severity as Parameters<typeof getPatientRecommendation>[0] | null,
                impairment:     functionalImpairment as FunctionalImpairment | null,
                referralLevel:  inputData.riskLevel as ReferralLevel,
                concernPattern: concernPatternForReport as ConcernPattern,
                // Labels only — toSafeLabels() drops the GEN-1 fallback claim and
                // anything sentence-shaped, so no user sentence reaches the prompt.
                symptomClaims: inputData.claimValidations.filter(
                    v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'symptom'
                ),
                stressorClaims: inputData.claimValidations.filter(
                    v => v.supportStatus !== 'unsupported' && v.sourceAgent === 'context'
                ),
            });

            const recommendationInstruction = renderRecommendationPrompt(recommendationDirective);

            // ── LLM generates Supporting Findings + Recommendation + Limitations ─
            // Supporting Findings are generated by the LLM (not TypeScript) so it can
            // rewrite the raw claim text into concise clinical language without copying
            // user sentences. Assessment Overview and Evidence Agreement remain TypeScript.
            const prompt = `
Input Mode: ${modeLabel}
Concern Pattern: ${concernPatternForReport}

VALIDATED FINDINGS (summarise as clinical plain-language findings — do NOT reproduce user text):
${claimsForPrompt}

Generate THREE sections. Do NOT include a document title. Do NOT include Assessment Overview — it is generated automatically.
Start your response directly with "## Supporting Findings".

## Supporting Findings
Rewrite the validated findings above as concise clinical plain-language bullet points.
Rules:
- NEVER copy the user's original words or sentences
- Use clinical terminology: "persistent worry", "sleep disruption", "positive emotional tone", "stable functioning", "social withdrawal"
- Keep each bullet 2–5 words (a label, not a sentence)
- If anxiety indicators are "none identified" AND emotional signals are positive/neutral: write only "No significant anxiety-related indicators were identified in the provided text."
- If anxiety indicators are present: write "The report identified the following experiences in the provided text:" then 3–6 bullets, then end with "These findings were checked against the clinical guidance and screening knowledge base used by AnxioSense."
- Include any contextual factors at the end of the bullets (e.g., "Academic stress", "Social pressures")

## Recommendation
${recommendationInstruction}

## Limitations
Write exactly TWO sentences, and do not repeat an idea that the other sentence already covers.
Sentence 1: state that the report is based only on the information provided and that missing context may affect interpretation.${mode === 'social-media' ? ' In this sentence also note that social media text adds further uncertainty.' : ''}
Sentence 2: end with exactly this wording — "This report is intended for screening support only, is not a clinical diagnosis, and cannot replace a comprehensive assessment by a qualified healthcare professional."

CRITICAL RULES — any violation makes the report unusable:
- Do NOT include a document title, Assessment Overview, or Evidence Agreement
- Do NOT reproduce user text in Supporting Findings — summarise clinically
- Do NOT include chunk IDs, claim IDs, file names, similarity scores
- Do NOT diagnose the user or name any clinical condition
- Do NOT suggest coping strategies, breathing exercises, mindfulness, or therapy techniques
- Do NOT mention hotlines, apps, websites, specific clinic types, or named resources
- Keep tone supportive, cautious, and non-judgmental
`;

            // Strategy is written to the session store in Map 2 (which has getInitData).
            // We read it back here so the report step doesn't need getInitData.
            const reportSession = readSession(inputData.sessionId);
            const reportStrategy = (reportSession?.promptStrategy ?? 'one-shot-cot') as PromptStrategy;
            const reportInstructions = loadAgentInstructions('report', reportStrategy) ?? undefined;
            const response = await agent.generate(
                prompt,
                { instructions: reportInstructions },
            );
            const reportUsage = response.usage;
            console.log(`[usage] report: input=${reportUsage?.inputTokens ?? '?'} output=${reportUsage?.outputTokens ?? '?'}`);
            const reportUpstreamProvider = extractUpstreamProvider(response);
            console.log(`[provider] report served by ${reportUpstreamProvider ?? 'unknown'}`);
            // Add report-step usage to the running total in the session store.
            accumulateTokenUsage(inputData.sessionId, reportUsage?.inputTokens, reportUsage?.outputTokens);

            // ── Post-process LLM output ───────────────────────────────────────
            let llmBody = response.text.trim()
                .replace(/^#+\s*AnxioSense\b[^\n]*\n\n?/im, '')
                .trim();

            // Ensure output starts at Supporting Findings; strip any LLM preamble
            const sfIdx = llmBody.search(/^#{1,3}\s*Supporting\s+Findings\b/im);
            if (sfIdx > 10) {
                llmBody = llmBody.slice(sfIdx).trim();
            } else if (sfIdx === -1) {
                // LLM skipped the section — inject fallback
                const recIdx = llmBody.search(/^#{1,3}\s*Recommendation\b/im);
                const fallback = symptomClaims.length === 0
                    ? '## Supporting Findings\n\nNo significant anxiety-related indicators were identified in the provided text.'
                    : '## Supporting Findings\n\nThe report identified the following experiences in the provided text:\n\n' +
                      symptomClaims.map(c => `- ${c}`).join('\n') +
                      '\n\nThese findings were checked against the clinical guidance and screening knowledge base used by AnxioSense.';
                llmBody = recIdx !== -1
                    ? fallback + '\n\n' + llmBody.slice(recIdx)
                    : fallback + '\n\n' + llmBody;
            }

            // ── Enforce the recommendation (deterministic) ────────────────────
            // Rejects a Recommendation section that dropped or altered the anchor,
            // or that changed the level of concern, added a diagnosis, or
            // introduced techniques/resources. On rejection the anchor is restored
            // verbatim and the model's addition is discarded — so the clinical
            // classification cannot be moved by generation.
            const enforcement = enforceRecommendation(llmBody, recommendationDirective);
            llmBody = enforcement.body;
            if (enforcement.enforced) {
                console.warn(
                    `[AnxioSense] Recommendation rejected and reset to the deterministic anchor ` +
                    `(${recommendationDirective.anchorSource}); violations: ${enforcement.violations.join(', ')}`
                );
                // Update quality flag in session store.
                const _qfSession = readSession(inputData.sessionId);
                if (_qfSession?.qualityFlags) {
                    writeSession(inputData.sessionId, {
                        qualityFlags: { ..._qfSession.qualityFlags, recommendation_rejected: true },
                    });
                }
            }

            // ── Build Assessment Overview (deterministic TypeScript) ──────────
            const overviewParts: string[] = [];
            if (mode === 'social-media') {
                overviewParts.push(
                    '**Analysis Type:** Social Media Analysis\n\n' +
                    'No structured questionnaire was available because this analysis was performed using secondary ' +
                    'social media text. Results therefore rely only on linguistic, emotional, symptomatic, and ' +
                    'contextual indicators identified in the written text.'
                );
            } else {
                overviewParts.push('**Analysis Type:** Journal / Self-Report');
                if (gad7Block) {
                    overviewParts.push('\n' + gad7Block);
                    // Append functional impairment if provided
                    if (functionalImpairment) {
                        const impairmentLabel = getFunctionalImpairmentLabel(
                            functionalImpairment as FunctionalImpairment
                        );
                        overviewParts.push(
                            `\n**Functional Impairment:** ${impairmentLabel}\n\n` +
                            `*"If you checked off any problems, how difficult have these problems made it for you ` +
                            `to do your work, take care of things at home, or get along with other people?"*`
                        );
                    }
                } else {
                    overviewParts.push(
                        '\nNo structured questionnaire was completed for this assessment. ' +
                        'The analysis relies on linguistic and contextual indicators identified in the written text.'
                    );
                }
                if (discordanceNote === 'high_gad7_low_text') {
                    overviewParts.push(
                        '\n**Note on Evidence Sources:** The structured questionnaire indicates a higher level of ' +
                        'concern than was reflected in the written text. Written expression may not fully capture ' +
                        'all of an individual\'s internal experiences. Both sources were considered in generating this report.'
                    );
                } else if (discordanceNote === 'low_gad7_high_text') {
                    overviewParts.push(
                        '\n**Note on Evidence Sources:** The written text reflects more indicators of concern than ' +
                        'the structured questionnaire score alone suggests. Both sources were considered in generating this report.'
                    );
                }
            }
            const assessmentOverview = `## Assessment Overview\n\n${overviewParts.join('\n')}`;

            // ── Evidence Agreement section ────────────────────────────────────
            const evidenceAgreementSection =
                `## Evidence Agreement\n\n**${evidenceAgreement}** — ${agreementText}`;

            // Insert Evidence Agreement before Limitations
            const limitIdx = llmBody.search(/^#{1,3}\s*Limitations?\b/im);
            let mainBody: string;
            if (limitIdx !== -1) {
                mainBody =
                    llmBody.slice(0, limitIdx).trimEnd() +
                    '\n\n' + evidenceAgreementSection +
                    '\n\n' + llmBody.slice(limitIdx);
            } else {
                mainBody = llmBody + '\n\n' + evidenceAgreementSection;
            }

            finalReport =
                `# AnxioSense Screening Support Report\n\n` +
                `${assessmentOverview}\n\n` +
                mainBody;

            // ── Clinician Summary block ───────────────────────────────────────
            // Clinically meaningful details only — no chunk IDs, no cosine thresholds.
            if (clinicianMode) {
                const severityLabel: Record<string, string> = {
                    minimal:  'Minimal — 0–4',
                    mild:     'Mild — 5–9',
                    moderate: 'Moderate — 10–14',
                    severe:   'Severe — 15–21',
                };
                const itemLabels = ['Not at all', 'Several days', 'More than half the days', 'Nearly every day'];
                const questions  = [
                    'Feeling nervous, anxious, or on edge',
                    'Not being able to stop or control worrying',
                    'Worrying too much about different things',
                    'Trouble relaxing',
                    'Being so restless that it is hard to sit still',
                    'Becoming easily annoyed or irritable',
                    'Feeling afraid, as if something awful might happen',
                ];

                // GAD-7 section
                let gad7ClinicianSection = '';
                if (session?.gad7Score !== null && session?.gad7Score !== undefined) {
                    const itemBreakdown = (session.gad7ItemScores ?? [])
                        .map((score, i) => `  ${i + 1}. ${questions[i]}\n     → ${itemLabels[score]}`)
                        .join('\n');
                    gad7ClinicianSection =
                        `**GAD-7:** ${session.gad7Score}/21 ` +
                        `(${severityLabel[session.gad7Severity ?? ''] ?? session.gad7Severity ?? 'Unknown'})\n\n` +
                        `**Per-Item Responses:**\n${itemBreakdown}\n\n`;
                }

                // Validated indicators — clinician-friendly labels, no raw user text
                const allValidated = inputData.claimValidations.filter(v => v.supportStatus !== 'unsupported');
                const indicatorLines = allValidated.length > 0
                    ? allValidated
                        .map(v => {
                            const supportLabel = v.supportStatus === 'supported' ? 'Supported' : 'Partially Supported';
                            return `  - ${v.claimText} (${supportLabel})`;
                        })
                        .join('\n')
                    : '  No anxiety-related indicators validated.';

                // Differential considerations — always natural clinical language
                const diffLean = inputData.differentiationAssessment.primaryLean;
                const differentialText = (!diffLean || diffLean === 'unclear')
                    ? 'Available information was insufficient to confidently distinguish anxiety-related symptoms from ' +
                      'other possible conditions such as depression. Further clinical assessment would be required.'
                    : `Assessment leans toward ${diffLean}. ${inputData.differentiationAssessment.reasoning}`;

                // Assessment notes — only if discordance was detected
                const assessmentNotes = discordanceNote === 'high_gad7_low_text'
                    ? 'The questionnaire responses indicated greater concern than was reflected in the written text. ' +
                      'This may suggest that written expression did not fully capture the respondent\'s internal experience.'
                    : discordanceNote === 'low_gad7_high_text'
                    ? 'The written text reflected more indicators of concern than the questionnaire responses alone suggested. ' +
                      'Clinical attention to both sources would be warranted.'
                    : '';

                const clinicianBlock = `

---

## Clinician Summary *(restricted — do not share with patient)*

${gad7ClinicianSection}**Validated Indicators:**
${indicatorLines}

**Evidence Confidence:** ${evidenceAgreement}

**Differential Considerations:**
${differentialText}
${assessmentNotes ? `\n**Assessment Notes:**\n${assessmentNotes}\n` : ''}
**Instrument provenance:** GAD-7 — Spitzer RL, Kroenke K, Williams JBW, Löwe B (2006), *Archives of Internal Medicine* 166(10):1092–1097. Items reproduced for educational and research use.

*This section is intended for qualified clinicians only and must not be shared with the patient as part of the screening output.*`;

                finalReport += clinicianBlock;
            }
        }

        // ── Pipeline Performance timing ────────────────────────────────────────
        // Timing is written to session store and logged to console ONLY.
        // It is NOT appended to finalReport (kept out of user-facing content).
        // It IS passed to the evaluation export for research analysis.
        let assembledTimings: SessionData['timings'] | undefined;
        try {
            const timingSession = readSession(inputData.sessionId);
            const agentMs       = timingSession?.agentTimingsMs;
            const retrievalMs   = timingSession?.retrievalElapsedMs  ?? 0;
            const validationMs  = timingSession?.validationElapsedMs ?? 0;
            const reportMs      = timingSession?.reportStartMs != null
                ? Date.now() - timingSession.reportStartMs
                : 0;

            if (agentMs) {
                const parallelMs = Math.max(agentMs.emotion, agentMs.symptom, agentMs.context, agentMs.referral);
                const totalMs    = parallelMs + retrievalMs + validationMs + reportMs;
                const fmt = (ms: number) => ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;

                assembledTimings = {
                    parallelMs,
                    emotionMs:   agentMs.emotion,
                    symptomMs:   agentMs.symptom,
                    contextMs:   agentMs.context,
                    referralMs:  agentMs.referral,
                    retrievalMs,
                    validationMs,
                    reportMs,
                    totalMs,
                };

                writeSession(inputData.sessionId, { timings: assembledTimings });

                // Console-only timing summary (not written to user report)
                console.log(
                    `[AnxioSense] Timing — ` +
                    `parallel: ${fmt(parallelMs)} ` +
                    `(emotion: ${fmt(agentMs.emotion)}, symptom: ${fmt(agentMs.symptom)}, ` +
                    `context: ${fmt(agentMs.context)}, referral: ${fmt(agentMs.referral)}), ` +
                    `retrieval: ${fmt(retrievalMs)}, validation: ${fmt(validationMs)}, ` +
                    `report: ${fmt(reportMs)}, total: ${fmt(totalMs)}`
                );
            }
        } catch (timingErr) {
            console.warn('[AnxioSense] Timing block failed (non-fatal):', timingErr);
        }

        // ── Evaluation export (opt-in) ────────────────────────────────────────
        // Disabled by default so normal users do not generate evaluation files.
        // Set EXPORT_EVALUATIONS=true in the Mastra process environment to enable.
        // clearSession always runs to free in-memory state regardless of export setting.
        const exportSession = readSession(inputData.sessionId);
        clearSession(inputData.sessionId);

        if (process.env.EXPORT_EVALUATIONS === 'true') {
            try {
                const filePath = exportWorkflowRun({
                    testCaseName:      process.env.ANXIOSENSE_TEST_CASE     ?? 'manual-run',
                    promptVersion:     process.env.ANXIOSENSE_PROMPT_VERSION ?? 'one-shot-cot-v1',
                    userText:          exportSession?.userText          ?? '',
                    gad7Block:         exportSession?.gad7Block         ?? null,
                    emotionAnalysis:   exportSession?.emotionAnalysis   ?? '{}',
                    symptomAnalysis:   exportSession?.symptomAnalysis   ?? '{}',
                    contextAnalysis:   exportSession?.contextAnalysis   ?? '{}',
                    referralAnalysis:  exportSession?.referralAnalysis  ?? '{}',
                    buildClaimsOutput: exportSession?.buildClaimsOutput ?? {},
                    retrievalOutput:   exportSession?.retrievalOutput   ?? {},
                    validationOutput:  inputData,
                    finalReport,
                    timings:           assembledTimings,
                });
                console.log(`[AnxioSense] Evaluation run saved → ${filePath}`);
            } catch (e) {
                console.warn('[AnxioSense] Export failed (non-fatal):', e);
            }
        }

        // ── Total token usage summary ─────────────────────────────────────────
        // exportSession was captured before clearSession() above — use it directly.
        // Re-reading after clearSession always returns undefined.
        const tokenUsage = exportSession?.tokenUsage;
        console.log(
            `[usage] total: input=${tokenUsage?.inputTokens ?? '?'} output=${tokenUsage?.outputTokens ?? '?'}`
        );

        // Quality flags are accumulated across workflow steps via the session store.
        // Default all to false so the field is always present in the output.
        const qualityFlags = exportSession?.qualityFlags ?? {
            agent_json_parse_failed:     false,
            fallback_claim_injected:     false,
            referral_risk_fallback_used: false,
            recommendation_rejected:     false,
        };

        return { finalReport, tokenUsage, qualityFlags };
    },
});

// ── Workflow definition ───────────────────────────────────────────────────────

export const anxietyScreeningAssessmentWorkflow = createWorkflow({
    id: 'anxiosense-workflow',
    inputSchema,
    outputSchema: finalReportSchema,
})
    .parallel([emotionStep, symptomStep, contextStep, referralStep])

    // ── Map 1: merge parallel outputs → combinedAnalysisSchema ───────────────
    .map(async ({ inputData, getInitData }) => {
        const originalInput = getInitData() as z.infer<typeof inputSchema>;
        const e = inputData['emotion-analysis-step'];
        const s = inputData['symptom-extraction-step'];
        const c = inputData['context-reasoning-step'];
        const r = inputData['referral-safety-step'];
        const parallelInput  = (e.inputTokens  ?? 0) + (s.inputTokens  ?? 0) + (c.inputTokens  ?? 0) + (r.inputTokens  ?? 0);
        const parallelOutput = (e.outputTokens ?? 0) + (s.outputTokens ?? 0) + (c.outputTokens ?? 0) + (r.outputTokens ?? 0);
        return {
            mode:             originalInput.mode ?? 'journal',
            userText:         originalInput.userText,
            emotionAnalysis:  e.result,
            symptomAnalysis:  s.result,
            contextAnalysis:  c.result,
            referralAnalysis: r.result,
            agentTimingsMs: {
                emotion:  e.durationMs,
                symptom:  s.durationMs,
                context:  c.durationMs,
                referral: r.durationMs,
            },
            parallelTokenUsage: { inputTokens: parallelInput, outputTokens: parallelOutput },
        };
    })
    .then(assessmentClaimConstructionStep)

    // ── Map 2: risk level + GAD-7 computation + session write ────────────────
    .map(async ({ inputData, getInitData }) => {
        // ── Risk level ────────────────────────────────────────────────────────
        const VALID_RISK_LEVELS = ['low', 'moderate', 'urgent'] as const;
        type RiskLevel = typeof VALID_RISK_LEVELS[number];
        let riskLevel: RiskLevel = 'moderate';
        let referral_risk_fallback_used = false;
        try {
            const referral = JSON.parse(inputData.referralAnalysis);
            const raw = referral.risk_level;
            if (typeof raw === 'string' && (VALID_RISK_LEVELS as readonly string[]).includes(raw)) {
                riskLevel = raw as RiskLevel;
            } else if (typeof raw === 'string') {
                console.warn(
                    `[AnxioSense] Invalid risk_level "${raw}" from referral agent — defaulting to "moderate".`
                );
                referral_risk_fallback_used = true;
            }
        } catch {
            console.warn('[AnxioSense] Referral JSON parse failed — defaulting risk_level to "moderate".');
            referral_risk_fallback_used = true;
        }

        // ── GAD-7 (journal mode only) ─────────────────────────────────────────
        const originalInput = getInitData() as z.infer<typeof inputSchema>;
        const mode                = originalInput.mode                ?? 'journal';
        const clinicianMode       = originalInput.clinicianMode       ?? false;
        const functionalImpairment = originalInput.functionalImpairment ?? null;
        const promptStrategy      = (originalInput.strategy ?? 'one-shot-cot') as PromptStrategy;

        let gad7Block:      string | null   = null;
        let gad7Score:      number | null   = null;
        let gad7Severity:   string | null   = null;
        let gad7ItemScores: number[] | null = null;

        if (mode === 'journal' && Array.isArray(originalInput.gad7Answers) && originalInput.gad7Answers.length === 7) {
            try {
                const gad7Result = computeGad7Score(originalInput.gad7Answers);
                gad7Block      = formatGad7ForReport(gad7Result);
                gad7Score      = gad7Result.score;
                gad7Severity   = gad7Result.severity;
                gad7ItemScores = [...gad7Result.itemScores];
                console.log(`[AnxioSense] GAD-7 scored: ${gad7Score}/21 (${gad7Severity})`);
            } catch (e) {
                console.warn('[AnxioSense] GAD-7 scoring failed (non-fatal):', e);
            }
        } else if (mode === 'social-media') {
            console.log('[AnxioSense] Social-media mode — GAD-7 bypassed.');
        }

        // ── Concern pattern label (from GAD-7 score) ──────────────────────────
        let gad7ConcernPattern: string | null = null;
        if (mode === 'journal' && gad7Score !== null) {
            if      (gad7Score <= 4)  gad7ConcernPattern = 'Minimal Concern Pattern';
            else if (gad7Score <= 9)  gad7ConcernPattern = 'Mild Concern Pattern';
            else if (gad7Score <= 14) gad7ConcernPattern = 'Elevated Concern Pattern';
            else                      gad7ConcernPattern = 'High Concern Pattern';
        }

        // ── Discordance detection ─────────────────────────────────────────────
        // Flags when GAD-7 and text-based signal disagree markedly.
        // GEN-1 is the fallback claim injected when agents return nothing —
        // treat it as "no real text signal" for discordance purposes.
        let discordanceNote: 'high_gad7_low_text' | 'low_gad7_high_text' | null = null;
        if (mode === 'journal' && gad7Score !== null) {
            const isFallbackOnly =
                inputData.claims.length === 1 && inputData.claims[0].claimId === 'GEN-1';
            const realClaimCount = isFallbackOnly ? 0 : inputData.claims.length;

            if (gad7Score >= 15 && realClaimCount <= 1) {
                // High questionnaire score but minimal text signal
                discordanceNote = 'high_gad7_low_text';
                console.log('[AnxioSense] Discordance detected: high_gad7_low_text');
            } else if (gad7Score <= 4 && realClaimCount >= 4) {
                // Minimal questionnaire score but rich text signal
                discordanceNote = 'low_gad7_high_text';
                console.log('[AnxioSense] Discordance detected: low_gad7_high_text');
            }
        }

        // ── Session write ─────────────────────────────────────────────────────
        writeSession(inputData.sessionId, {
            mode,
            clinicianMode,
            functionalImpairment,
            promptStrategy,
            userText:          inputData.userText,
            emotionAnalysis:   inputData.emotionAnalysis,
            symptomAnalysis:   inputData.symptomAnalysis,
            contextAnalysis:   inputData.contextAnalysis,
            referralAnalysis:  inputData.referralAnalysis,
            buildClaimsOutput: { sessionId: inputData.sessionId, claims: inputData.claims },
            gad7Block,
            gad7Score,
            gad7Severity,
            gad7ItemScores,
            gad7ConcernPattern,
            discordanceNote,
            // Timing: parallel agent durations + start mark for retrieval
            agentTimingsMs:    inputData.agentTimingsMs,
            retrievalStartMs:  Date.now(),
            // Seed token usage with the parallel agents' counts; report step will add its own.
            tokenUsage: inputData.parallelTokenUsage ?? { inputTokens: 0, outputTokens: 0 },
            // Update quality flags with referral_risk_fallback_used (agent_json_parse_failed
            // and fallback_claim_injected were seeded by the claim construction step).
            qualityFlags: {
                agent_json_parse_failed:     inputData.agent_json_parse_failed,
                fallback_claim_injected:     inputData.fallback_claim_injected,
                referral_risk_fallback_used,
                recommendation_rejected:     false,  // updated by report step
            },
        });

        return {
            sessionId:    inputData.sessionId,
            originalText: inputData.userText,
            claims:       inputData.claims,
            riskLevel,
        };
    })
    .then(knowledgeEvidenceRetrievalStep)

    // ── Pass-through: write retrieval output + timing to session ─────────────
    .map(async ({ inputData }) => {
        const session = readSession(inputData.sessionId);
        const retrievalElapsedMs = session?.retrievalStartMs != null
            ? Date.now() - session.retrievalStartMs
            : 0;
        writeSession(inputData.sessionId, {
            retrievalOutput:    inputData,
            retrievalElapsedMs,
            validationStartMs:  Date.now(),
        });
        return inputData;
    })
    .then(knowledgeEvidenceValidationStep)

    // ── Map 4: record evidence validation elapsed time ────────────────────────
    .map(async ({ inputData }) => {
        const session = readSession(inputData.sessionId);
        const validationElapsedMs = session?.validationStartMs != null
            ? Date.now() - session.validationStartMs
            : 0;
        writeSession(inputData.sessionId, {
            validationElapsedMs,
            reportStartMs: Date.now(),
        });
        return inputData;
    })
    .then(reportStep);

anxietyScreeningAssessmentWorkflow.commit();
