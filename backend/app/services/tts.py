"""Azure AI Speech neural text-to-speech via REST. Voice is chosen from the answer language."""
from __future__ import annotations

import logging
import re
from typing import Protocol
from xml.sax.saxutils import escape

import httpx

from app.config import Settings
from app.services.stt import SpeechError

log = logging.getLogger("campusvoice.tts")
OUTPUT_FORMAT = "audio-16khz-32kbitrate-mono-mp3"


class TextToSpeech(Protocol):
    def synthesize(self, text: str, language: str) -> bytes: ...


def make_spoken(answer: str, max_words: int = 40) -> str:
    """Plain, short text for audio: strip markdown and cut at a sentence end near `max_words`."""
    t = re.sub(r"[*_`#>|]+", " ", answer)
    t = re.sub(r"\s+", " ", t).strip()
    words = t.split()
    if len(words) <= max_words:
        return t
    cut = " ".join(words[:max_words])
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "), cut.rfind("। "))
    return (cut[: end + 1] if end > 20 else cut.rstrip(",;:")) + ("" if end > 20 else ".")


class AzureTts:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        if not settings.azure_speech_configured:
            raise SpeechError("Text-to-speech is not configured.")
        self.s = settings
        self.http = client or httpx.Client(timeout=20)
        self.url = (
            f"https://{settings.azure_speech_region}.tts.speech.microsoft.com"
            "/cognitiveservices/v1"
        )
        log.info(
            "AzureTts ready: region=%s voice_en=%s voice_te=%s",
            settings.azure_speech_region,
            settings.azure_speech_tts_voice_en,
            settings.azure_speech_tts_voice_te,
        )

    def voice_for(self, language: str) -> tuple[str, str]:
        return (
            (self.s.azure_speech_tts_voice_te, "te-IN")
            if language == "te"
            else (self.s.azure_speech_tts_voice_en, "en-IN")
        )

    def synthesize(self, text: str, language: str) -> bytes:
        voice, locale = self.voice_for(language)
        ssml = (
            f"<speak version='1.0' xml:lang='{locale}'>"
            f"<voice name='{voice}'>{escape(text)}</voice></speak>"
        )
        log.debug(
            "AzureTts.synthesize: language=%s voice=%s text=%d chars",
            language,
            voice,
            len(text),
        )
        try:
            r = self.http.post(
                self.url,
                content=ssml.encode("utf-8"),
                headers={
                    "Ocp-Apim-Subscription-Key": self.s.azure_speech_key or "",
                    "Content-Type": "application/ssml+xml",
                    "X-Microsoft-OutputFormat": OUTPUT_FORMAT,
                    "User-Agent": "CampusVoice",
                },
            )
        except httpx.HTTPError as exc:
            log.warning("AzureTts network error: %s", type(exc).__name__)
            raise SpeechError("Could not reach the speech service.") from exc

        if r.status_code >= 400 or not r.content:
            log.warning("AzureTts HTTP %s language=%s voice=%s", r.status_code, language, voice)
            raise SpeechError("Text-to-speech failed.")

        log.debug(
            "AzureTts.synthesize: success language=%s audio=%d bytes",
            language,
            len(r.content),
        )
        return r.content


def get_tts(settings: Settings) -> TextToSpeech:
    return AzureTts(settings)
