from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from vagents.core import AgentModule, AgentInput, AgentOutput
from vagents.core.model import LM


def _git_summary(repo_dir: Path) -> Dict[str, Any]:
    try:
        import subprocess

        def run(cmd: List[str]) -> str:
            out = subprocess.run(cmd, cwd=str(repo_dir), capture_output=True, text=True)
            return out.stdout.strip()

        head = run(["git", "rev-parse", "HEAD"])[:12]
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"]) or "(detached)"
        last_commit = run(["git", "log", "-1", "--pretty=%h %an %ad %s", "--date=iso"])

        # Diff summary for working tree
        stat = run(["git", "diff", "--stat"])
        staged_stat = run(["git", "diff", "--cached", "--stat"])

        # Recent commits
        recent = run(["git", "log", "--pretty=oneline", "-n", "10"])[:5000]

        return {
            "head": head,
            "branch": branch,
            "last_commit": last_commit,
            "diff_stat": stat,
            "staged_diff_stat": staged_stat,
            "recent_commits": recent,
        }
    except Exception as e:
        return {"error": f"Failed to read git info: {e}"}


def _git_unified_diff(repo_dir: Path) -> str:
    try:
        import subprocess

        out = subprocess.run(
            ["git", "diff"], cwd=str(repo_dir), capture_output=True, text=True
        )
        staged = subprocess.run(
            ["git", "diff", "--cached"],
            cwd=str(repo_dir),
            capture_output=True,
            text=True,
        )
        return (out.stdout + "\n" + staged.stdout)[:200000]
    except Exception as e:
        return f"[Error] git diff failed: {e}"


class CodeReview(AgentModule):
    async def forward(self, input: AgentInput) -> AgentOutput:
        payload = input.payload or {}
        cwd = Path(payload.get("repo", os.getcwd()))
        model_name = payload.get("model") or os.environ.get(
            "VAGENTS_CODEREVIEW_MODEL", "Qwen/Qwen3-32B"
        )

        summary = _git_summary(cwd)
        diffs = _git_unified_diff(cwd)

        system = (
            "You are a senior software engineer performing a thorough code review. "
            "Identify correctness issues, design flaws, potential bugs, security concerns, "
            "missing tests, and provide actionable suggestions. Be specific and cite code hunks."
        )
        user = (
            "Repository summary:\n"
            + str(summary)
            + "\n\n"
            + "Unified diff (working tree and staged):\n"
            + diffs
        )
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        lm = self.lm or LM(name=model_name)
        try:
            resp = await lm(messages=messages, temperature=0.2, max_tokens=1800)
            content = (
                resp.get("choices", [{}])[0]
                .get("message", {})
                .get("content", str(resp))
            )
            result = {
                "review": content,
                "repo": str(cwd),
                "head": summary.get("head"),
                "branch": summary.get("branch"),
                "used_model": model_name,
            }
        except Exception as e:
            result = {
                "review": f"[Error calling LM] {e}",
                "repo": str(cwd),
                "excerpt": (
                    diffs[:2000] if isinstance(diffs, str) else str(diffs)[:2000]
                ),
                "used_model": model_name,
            }

        return AgentOutput(input_id=input.id, result=result)


async def run(input: AgentInput) -> AgentOutput:
    return await CodeReview().forward(input)
