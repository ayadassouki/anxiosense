/**
 * src/mastra/utils/prompt-strategy-loader.ts
 *
 * Loads agent instructions from the prompts/ directory based on the active
 * prompting strategy.  Used at generate() time so strategy can change
 * per workflow invocation without restarting the server.
 *
 * Prompt file location (relative to repo root):
 *   prompts/{agentName}/{strategy}.md
 *
 * Each file contains a ```text … ``` fenced block whose content is the
 * complete system message for that agent and strategy.
 *
 * Strategies:
 *   zero-shot      — task instructions + output schema only; no reasoning procedure, no example
 *   zero-shot-cot  — adds an explicit chain-of-thought reasoning procedure; no example
 *   one-shot-cot   — adds both a reasoning procedure and a worked example (current default)
 *
 * If a prompt file cannot be read (missing, unreadable), the function returns
 * null so the caller can fall back to the agent's hardcoded instructions.
 */

import * as fs   from 'fs';
import * as path from 'path';

// ── Types ─────────────────────────────────────────────────────────────────────

export type PromptStrategy = 'zero-shot' | 'zero-shot-cot' | 'one-shot-cot';
export type AgentName      = 'emotion' | 'symptom' | 'context' | 'referral' | 'report' | 'validation';

const VALID_STRATEGIES: PromptStrategy[] = ['zero-shot', 'zero-shot-cot', 'one-shot-cot'];

// ── Helpers ───────────────────────────────────────────────────────────────────

/**
 * Extracts the text content from the ```text … ``` fenced block in a
 * Markdown prompt file.  Returns null when no such block is found.
 */
function extractFencedText(markdown: string): string | null {
    const match = markdown.match(/```text\n([\s\S]+?)\n```/);
    return match ? match[1].trim() : null;
}

/**
 * Locates the repo-root `prompts/` directory regardless of what directory
 * `mastra dev` sets as process.cwd() at runtime.
 *
 * `mastra dev` bundles the source and runs steps with cwd set to
 * `src/mastra/public/` (inside the source tree), so
 * `path.join(process.cwd(), 'prompts')` resolves to the wrong place.
 *
 * Strategy:
 *   1. PROMPTS_DIR env var — explicit override, highest priority.
 *   2. Walk up from process.cwd() until a directory that contains
 *      `prompts/emotion/` is found (the presence of an agent subdirectory
 *      is the distinguishing marker).  Stops after 8 levels to avoid
 *      infinite loops at the filesystem root.
 *   3. Fall back to path.join(process.cwd(), 'prompts') as a last resort
 *      so the error message still shows a useful path.
 */
function resolvePromptsDir(): string {
    if (process.env.PROMPTS_DIR) return process.env.PROMPTS_DIR;

    let dir = process.cwd();
    for (let i = 0; i < 8; i++) {
        const candidate = path.join(dir, 'prompts');
        // Use 'emotion' as the canary — every AnxioSense deployment has this subdir.
        if (fs.existsSync(path.join(candidate, 'emotion'))) {
            return candidate;
        }
        const parent = path.dirname(dir);
        if (parent === dir) break; // reached filesystem root
        dir = parent;
    }

    // Last resort — caller will get a clear ENOENT message pointing here.
    return path.join(process.cwd(), 'prompts');
}

// ── Public API ────────────────────────────────────────────────────────────────

/**
 * Resolves and returns the active strategy.
 *
 * Priority:
 *   1. Explicit `strategy` argument (when called from workflow step with per-run value)
 *   2. ANXIOSENSE_STRATEGY environment variable
 *   3. 'one-shot-cot' hard default
 */
export function resolveStrategy(strategy?: string): PromptStrategy {
    const raw = (strategy ?? process.env.ANXIOSENSE_STRATEGY ?? 'one-shot-cot').trim();
    if (VALID_STRATEGIES.includes(raw as PromptStrategy)) return raw as PromptStrategy;
    console.warn(`[prompt-loader] Unknown strategy "${raw}" — using one-shot-cot.`);
    return 'one-shot-cot';
}

/**
 * Loads the system-message text for `agentName` under `strategy`.
 *
 * Returns the extracted text string on success, or null if the file cannot
 * be read or does not contain a valid ```text block.  Null signals the caller
 * to fall back to the agent's hardcoded instructions.
 *
 * @param agentName  One of the six AnxioSense agent names.
 * @param strategy   Prompting strategy (or undefined → resolved from env).
 */
export function loadAgentInstructions(
    agentName: AgentName,
    strategy?: string,
): string | null {
    const resolved = resolveStrategy(strategy);

    const promptsDir = resolvePromptsDir();

    const filePath = path.join(promptsDir, agentName, `${resolved}.md`);

    let raw: string;
    try {
        raw = fs.readFileSync(filePath, 'utf-8');
    } catch (err) {
        console.warn(
            `[prompt-loader] Cannot read ${filePath}: ${(err as NodeJS.ErrnoException).message}. ` +
            `Falling back to agent hardcoded instructions.`
        );
        return null;
    }

    const text = extractFencedText(raw);
    if (!text) {
        console.warn(
            `[prompt-loader] No \`\`\`text block found in ${filePath}. ` +
            `Falling back to agent hardcoded instructions.`
        );
        return null;
    }

    console.log(
        `[prompt-loader] ${agentName}/${resolved}.md loaded (${text.length} chars).`
    );
    return text;
}
