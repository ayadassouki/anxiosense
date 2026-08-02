"""
src/prompt_loader.py

Load AnxioSense prompt templates from the repository's prompts/ directory.
Each prompt file is a Markdown document with a fenced code block under
the "## Prompt" section.

Supported strategies:
    zero-shot       → prompts/{agent}/zero-shot.md
    zero-shot-cot   → prompts/{agent}/zero-shot-cot.md
    one-shot-cot    → prompts/{agent}/one-shot-cot.md

Usage:
    from src.prompt_loader import PromptLoader
    loader = PromptLoader(repo_root="/path/to/anxiosense")
    system_prompt = loader.load("emotion", "zero-shot")
    user_message  = loader.format_user_message(text)
"""

from __future__ import annotations

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# PromptLoader
# ---------------------------------------------------------------------------

class PromptLoaderError(ValueError):
    """Raised when a prompt file cannot be found or parsed."""


# Regex to extract content from the first fenced code block in the ## Prompt section
_PROMPT_SECTION_RE = re.compile(
    r"##\s+Prompt\s*\n+```(?:text)?\n(.*?)```",
    re.DOTALL,
)


class PromptLoader:
    """
    Load prompt templates from the repository's prompts/ directory.

    Parameters
    ----------
    repo_root:
        Absolute path to the repository root (contains the prompts/ directory).
    prompts_dir:
        Name of the prompts subdirectory relative to repo_root.
        Defaults to "prompts".
    """

    VALID_STRATEGIES = {"zero-shot", "zero-shot-cot", "one-shot-cot"}

    def __init__(
        self,
        repo_root: str | Path,
        prompts_dir: str = "prompts",
    ) -> None:
        self._root = Path(repo_root) / prompts_dir
        if not self._root.is_dir():
            raise PromptLoaderError(
                f"Prompts directory not found: {self._root}"
            )

    def load(self, agent: str, strategy: str) -> str:
        """
        Return the raw system-prompt text for a given agent and strategy.

        Parameters
        ----------
        agent:
            One of: emotion, symptom, context, referral, report, validation.
        strategy:
            One of: zero-shot, zero-shot-cot, one-shot-cot.

        Returns
        -------
        str: the extracted prompt text (used as the system message).
        """
        if strategy not in self.VALID_STRATEGIES:
            raise PromptLoaderError(
                f"Unknown strategy: {strategy!r}. "
                f"Valid options: {sorted(self.VALID_STRATEGIES)}"
            )

        md_path = self._root / agent / f"{strategy}.md"
        if not md_path.exists():
            raise PromptLoaderError(
                f"Prompt file not found: {md_path}"
            )

        return self._extract_prompt(md_path)

    def _extract_prompt(self, path: Path) -> str:
        """Parse the Markdown file and extract the prompt from the fenced block."""
        text = path.read_text(encoding="utf-8")
        match = _PROMPT_SECTION_RE.search(text)
        if not match:
            raise PromptLoaderError(
                f"Could not find '## Prompt' section with a fenced code block in {path}. "
                "Expected format: '## Prompt\\n\\n```text\\n<prompt>\\n```'"
            )
        return match.group(1).rstrip("\n")

    def list_agents(self) -> list[str]:
        """Return the list of agents for which prompt directories exist."""
        return sorted(
            d.name for d in self._root.iterdir() if d.is_dir()
        )

    def list_strategies(self, agent: str) -> list[str]:
        """Return the list of strategy files available for a given agent."""
        agent_dir = self._root / agent
        if not agent_dir.is_dir():
            raise PromptLoaderError(f"Agent directory not found: {agent_dir}")
        return sorted(
            f.stem for f in agent_dir.glob("*.md")
        )

    @staticmethod
    def format_user_message(text: str) -> str:
        """
        Wrap the raw dataset text as the user message content.

        The AnxioSense prompts are pure system prompts — the user text is passed
        directly as the user turn content.
        """
        return text.strip()
