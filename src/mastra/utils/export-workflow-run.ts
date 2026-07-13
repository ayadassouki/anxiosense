/**
 * Evaluation export utility.
 *
 * Saves a full workflow run snapshot as a Markdown file under
 * evaluation/prompt-experiments/runs/<timestamp>-<promptVersion>-<testCase>.md
 *
 * Call after the final report is generated (see anxiosense-workflow.ts reportStep).
 * Errors are intentionally not re-thrown — a failed export must never crash a run.
 */

import fs from 'fs';
import path from 'path';

export interface WorkflowRunExportParams {
    testCaseName: string;
    promptVersion: string;
    userText: string;
    /** Formatted GAD-7 block produced by gad7-scorer.ts, or null if not provided. */
    gad7Block: string | null;
    emotionAnalysis: string;
    symptomAnalysis: string;
    contextAnalysis: string;
    referralAnalysis: string;
    buildClaimsOutput: unknown;
    retrievalOutput: unknown;
    validationOutput: unknown;
    finalReport: string;
    /**
     * Pipeline timing data.  Optional — absent when the timing block failed or on the
     * urgent-safety path (which short-circuits before timing is assembled).
     * Included here for research analysis; intentionally excluded from user-facing report.
     */
    timings?: {
        parallelMs:  number;
        emotionMs:   number;
        symptomMs:   number;
        contextMs:   number;
        referralMs:  number;
        retrievalMs: number;
        validationMs: number;
        reportMs:    number;
        totalMs:     number;
    };
}

/** Format a duration in milliseconds for human reading. */
function fmtMs(ms: number): string {
    return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}

/** Try to pretty-print a JSON string; fall back to the raw string on parse error. */
function safeJsonBlock(raw: string): string {
    try {
        return JSON.stringify(JSON.parse(raw.trim()), null, 2);
    } catch {
        return raw.trim();
    }
}

/**
 * Writes the workflow run to a timestamped Markdown file.
 * Returns the absolute path of the file written.
 */
export function exportWorkflowRun(params: WorkflowRunExportParams): string {
    const {
        testCaseName,
        promptVersion,
        userText,
        gad7Block,
        emotionAnalysis,
        symptomAnalysis,
        contextAnalysis,
        referralAnalysis,
        buildClaimsOutput,
        retrievalOutput,
        validationOutput,
        finalReport,
        timings,
    } = params;

    // Build a filename-safe timestamp: 2026-06-28T14-05-30
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    const slug = testCaseName.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    const version = promptVersion.toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
    const filename = `${timestamp}-${version}-${slug}.md`;

    const outputDir = path.resolve(process.cwd(), 'evaluation/prompt-experiments/runs');
    fs.mkdirSync(outputDir, { recursive: true });
    const filePath = path.join(outputDir, filename);

    const gad7Section = gad7Block
        ? [`## GAD-7 Score`, gad7Block, ``]
        : [`## GAD-7 Score`, '_Not provided for this run._', ``];

    const md = [
        `# AnxioSense Workflow Run`,
        ``,
        `## Test Case`,
        testCaseName,
        ``,
        `## Prompt Version`,
        promptVersion,
        ``,
        `## User Input`,
        userText,
        ``,
        ...gad7Section,
        `## Emotion Agent Output`,
        '```json',
        safeJsonBlock(emotionAnalysis),
        '```',
        ``,
        `## Symptom Agent Output`,
        '```json',
        safeJsonBlock(symptomAnalysis),
        '```',
        ``,
        `## Context Agent Output`,
        '```json',
        safeJsonBlock(contextAnalysis),
        '```',
        ``,
        `## Referral Agent Output`,
        '```json',
        safeJsonBlock(referralAnalysis),
        '```',
        ``,
        `## Build Claims Step`,
        '```json',
        JSON.stringify(buildClaimsOutput, null, 2),
        '```',
        ``,
        `## Retrieval Step`,
        '```json',
        JSON.stringify(retrievalOutput, null, 2),
        '```',
        ``,
        `## Evidence Validation Step`,
        '```json',
        JSON.stringify(validationOutput, null, 2),
        '```',
        ``,
        `## Final Report`,
        '```md',
        finalReport,
        '```',
        ``,
        ...(timings
            ? [
                `## Pipeline Performance (research metadata — not shown to users)`,
                ``,
                `| Stage | Duration |`,
                `|---|---|`,
                `| Parallel agents (4 agents, concurrent) | ${fmtMs(timings.parallelMs)} |`,
                `|   ↳ Emotion analysis | ${fmtMs(timings.emotionMs)} |`,
                `|   ↳ Symptom identification | ${fmtMs(timings.symptomMs)} |`,
                `|   ↳ Context assessment | ${fmtMs(timings.contextMs)} |`,
                `|   ↳ Referral & safety | ${fmtMs(timings.referralMs)} |`,
                `| Knowledge base retrieval | ${fmtMs(timings.retrievalMs)} |`,
                `| Evidence validation | ${fmtMs(timings.validationMs)} |`,
                `| Report generation | ${fmtMs(timings.reportMs)} |`,
                `| **Total** | **${fmtMs(timings.totalMs)}** |`,
                ``,
            ]
            : [`## Pipeline Performance`, `_Timing data not available for this run._`, ``]),
    ].join('\n');

    fs.writeFileSync(filePath, md, 'utf-8');
    return filePath;
}
