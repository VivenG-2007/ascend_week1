"""Azure AI Speech speech-to-text via the short-audio REST API.

Language handling: the REST endpoint recognises ONE language per request. For `auto` we send the
audio once per configured language (default en-IN and te-IN) in parallel and keep the result with
the higher confidence. Code-mixed Telugu-English accuracy must be measured on real recordings.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Protocol

import httpx

from app.config import Settings

log = logging.getLogger("campusvoice.stt")


class SpeechError(Exception):
    def __init__(self, message: str, empty: bool = False, unavailable: bool = False) -> None:
        super().__init__(message)
        self.message = message
        self.empty = empty       # True when the audio was understood as silence / no speech
        self.unavailable = unavailable  # True when speech is not configured on this server


@dataclass
class SttResult:
    text: str
    language: str  # "en" | "te"
    locale: str
    confidence: float | None


class SpeechToText(Protocol):
    def transcribe(self, wav: bytes, language: str = "auto") -> SttResult: ...


def _short(locale: str) -> str:
    return "te" if locale.lower().startswith("te") else "en"


class AzureStt:
    def __init__(self, settings: Settings, client: httpx.Client | None = None) -> None:
        if not settings.azure_speech_configured:
            raise SpeechError(
                "Voice input is not set up on this server. Please type your question.",
                unavailable=True,
            )
        self.s = settings
        self.http = client or httpx.Client(timeout=20)
        self.url = (
            f"https://{settings.azure_speech_region}.stt.speech.microsoft.com"
            "/speech/recognition/conversation/cognitiveservices/v1"
        )
        log.info("AzureStt ready: region=%s languages=%s", settings.azure_speech_region, settings.azure_speech_stt_languages)

    def _locale_for(self, language: str) -> list[str]:
        locales = self.s.stt_languages
        if language == "auto":
            return locales
        match = [l for l in locales if _short(l) == language]
        return match or [("te-IN" if language == "te" else "en-IN")]

    def _recognise(self, wav: bytes, locale: str) -> SttResult | str:
        log.debug("AzureStt._recognise: locale=%s audio=%d bytes", locale, len(wav))
        try:
            r = self.http.post(
                self.url,
                params={"language": locale, "format": "detailed", "profanity": "raw"},
                content=wav,
                headers={
                    "Ocp-Apim-Subscription-Key": self.s.azure_speech_key or "",
                    "Content-Type": "audio/wav; codecs=audio/pcm; samplerate=16000",
                    "Accept": "application/json",
                },
            )
        except httpx.HTTPError as exc:
            log.warning("AzureStt network error locale=%s: %s", locale, type(exc).__name__)
            raise SpeechError("Could not reach the speech service. Please type your question instead.") from exc

        log.debug("AzureStt._recognise: HTTP %d locale=%s", r.status_code, locale)

        if r.status_code in (401, 403):
            raise SpeechError("The speech service rejected our credentials. Please type your question instead.")
        if r.status_code >= 400:
            log.warning("AzureStt HTTP %s locale=%s", r.status_code, locale)
            raise SpeechError("The speech service had a problem. Please type your question instead.")

        body = r.json()
        status = body.get("RecognitionStatus")
        if status == "Success":
            best = (body.get("NBest") or [{}])[0]
            text = (best.get("Display") or body.get("DisplayText") or "").strip()
            conf = best.get("Confidence")
            log.debug("AzureStt: recognised locale=%s confidence=%.3f text=%r", locale, conf or 0, text[:80])
            return SttResult(text, _short(locale), locale, conf)
        log.debug("AzureStt: non-success status=%r locale=%s", status, locale)
        return status or "Error"

    def transcribe(self, wav: bytes, language: str = "auto") -> SttResult:
        locales = self._locale_for(language)
        log.info("AzureStt.transcribe: language=%s locales=%s audio=%d bytes", language, locales, len(wav))
        with ThreadPoolExecutor(max_workers=len(locales)) as pool:
            outcomes = list(pool.map(lambda loc: self._recognise(wav, loc), locales))
        good = [o for o in outcomes if isinstance(o, SttResult) and o.text]
        if good:
            best = max(good, key=lambda o: o.confidence or 0.0)
            log.info("AzureStt.transcribe: best locale=%s confidence=%.3f", best.locale, best.confidence or 0)
            return best
        statuses = {o for o in outcomes if isinstance(o, str)}
        if statuses & {"NoMatch", "InitialSilenceTimeout"} or not statuses:
            raise SpeechError(
                "I could not hear any speech. Please try again or type your question.",
                empty=True,
            )
        raise SpeechError("The speech service could not understand that audio. Please try again or type.")


def get_stt(settings: Settings) -> SpeechToText:
    return AzureStt(settings)
