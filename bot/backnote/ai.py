"""Lecture summaries via the Gemini API (free tier can read public YouTube videos)."""

import logging

import aiohttp

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

PROMPT = """You are a meticulous teaching assistant. Watch this university {kind} recording
("{title}", subject: "{subject}") and write study notes in {language}.

Output GitHub-flavoured Markdown only (no preamble), using exactly this structure:

## 🧭 Overview
3-5 sentences: what the session covers and why it matters.

## 🔑 Key ideas
Bullet list of the main concepts, each with a one-line explanation. **Bold** the term.

## 📐 Formulas & definitions
Important formulas as LaTeX between $...$ (inline) or $$...$$ (block) with the meaning of each
symbol, and precise definitions. Omit this section if there are none.

## ⏱ Timeline
A Markdown table | Time | Topic | with 5-12 rows using mm:ss or h:mm:ss timestamps.

## ✅ Self-check
4-6 questions. After each question put the answer inside
<details><summary>Answer</summary>...</details>.

## 📌 Takeaways
3 bullet points to remember for the exam.

Keep established technical terms, code, commands and library names in English
(add the translation in parentheses on first use where helpful). Put code in fenced blocks.
Keep it factual and skip small talk and organisational announcements."""


class SummaryError(RuntimeError):
    pass


class GeminiSummarizer:
    def __init__(self, api_key: str, model: str, language: str = "Ukrainian") -> None:
        self._api_key = api_key
        self._model = model
        self._language = language

    async def summarize_video(
        self, video_url: str, *, title: str, subject: str, kind: str = "lecture"
    ) -> str:
        prompt = PROMPT.format(
            kind=kind.lower(), title=title, subject=subject, language=self._language
        )
        payload = {
            "contents": [{"parts": [{"file_data": {"file_uri": video_url}}, {"text": prompt}]}],
        }
        # Hour-long videos can take several minutes to process.
        timeout = aiohttp.ClientTimeout(total=15 * 60)
        async with (
            aiohttp.ClientSession(timeout=timeout) as http,
            http.post(
                API_URL.format(model=self._model),
                json=payload,
                headers={"x-goog-api-key": self._api_key},
            ) as resp,
        ):
            data = await resp.json(content_type=None)
            if resp.status != 200:
                message = (data or {}).get("error", {}).get("message", resp.reason)
                log.warning("Gemini error %s: %s", resp.status, message)
                raise SummaryError(f"Gemini API error {resp.status}: {message}")
        return extract_text(data)


def extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
        raise SummaryError(f"Gemini returned no summary ({reason})")
    parts = (candidates[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought")).strip()
    if not text:
        raise SummaryError("Gemini returned an empty summary")
    return text
