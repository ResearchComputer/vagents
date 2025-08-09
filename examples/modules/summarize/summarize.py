from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from vagents.core import AgentModule, AgentInput, AgentOutput
from vagents.core.model import LM


def _read_text_file(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _read_pdf_file(path: Path) -> str:
    try:
        try:
            import pypdf  # type: ignore

            reader = pypdf.PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            from PyPDF2 import PdfReader  # type: ignore

            reader = PdfReader(str(path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return f"[Error] Unable to extract text from PDF: {e}. Install 'pypdf' or 'PyPDF2'."


def _load_content(payload: Dict[str, Any]) -> tuple[str, Optional[str]]:
    file_path = payload.get("file") or payload.get("path")
    if file_path:
        p = Path(str(file_path))
        if not p.exists():
            return f"[Error] File not found: {p}", str(p)
        if p.suffix.lower() in {".md", ".txt", ".markdown"}:
            return _read_text_file(p), str(p)
        if p.suffix.lower() in {".pdf"}:
            return _read_pdf_file(p), str(p)
        try:
            return _read_text_file(p), str(p)
        except Exception as e:
            return f"[Error] Unsupported file type or read error: {e}", str(p)
    content = payload.get("input") or payload.get("stdin") or payload.get("content")
    return (content or "", None)


def _truncate(text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 100] + "\n...[truncated]"


class Summarize(AgentModule):
    async def forward(self, input: AgentInput) -> AgentOutput:
        payload = input.payload or {}
        max_chars = int(payload.get("max_chars", 15000))
        query = payload.get("q") or payload.get("query") or "Summarize the document."
        content, source = _load_content(payload)
        truncated = _truncate(content or "", max_chars)

        system_prompt = "You are a helpful assistant. Provide a clear, structured summary of the document."
        user_prompt = (
            f"Instruction: {query}\n\n"
            f"Document Content (truncated to {max_chars} chars):\n" + truncated
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        model_name = payload.get("model") or os.environ.get(
            "VAGENTS_SUMMARIZE_MODEL", "Qwen/Qwen3-32B"
        )
        lm = self.lm or LM(name=model_name)

        try:
            resp = await lm(messages=messages, temperature=0.2, max_tokens=1200)
            summary = (
                resp.get("choices", [{}])[0]
                .get("message", {})
                .get("content", str(resp))
            )
            result = {
                "summary": summary,
                "source": source,
                "input_chars": len(content or ""),
                "used_model": model_name,
            }
        except Exception as e:
            result = {
                "summary": f"[Error calling LM] {e}",
                "source": source,
                "excerpt": truncated[:1000],
                "used_model": model_name,
            }

        return AgentOutput(input_id=input.id, result=result)


async def run(input: AgentInput) -> AgentOutput:
    return await Summarize().forward(input)
