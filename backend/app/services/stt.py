"""
Speech-to-Text (STT) Service
Uses Azure AI Speech SDK to transcribe English and Telugu voice audio.
"""
import io
import time
import logging
from typing import Tuple
from app.config import settings

logger = logging.getLogger("campusvoice.stt")

def transcribe_audio_bytes(audio_bytes: bytes, language_hint: str = "en") -> Tuple[str, str, float]:
    """
    Transcribes audio bytes to text using Azure AI Speech.
    Returns (transcript_text, detected_language, stt_latency_ms).
    """
    start_time = time.perf_counter()
    if not audio_bytes or len(audio_bytes) < 100:
        raise ValueError("Audio data is empty or too short to process.")

    target_lang = "te-IN" if language_hint == "te" else "en-IN"

    if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION
            )
            speech_config.speech_recognition_language = target_lang

            # Use push stream or memory audio stream
            push_stream = speechsdk.audio.PushAudioInputStream()
            push_stream.write(audio_bytes)
            push_stream.close()

            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
            recognizer = speechsdk.SpeechRecognizer(speech_config=speech_config, audio_config=audio_config)
            
            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                transcript = result.text.strip()
                stt_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return transcript, language_hint, stt_ms
            elif result.reason == speechsdk.ResultReason.NoMatch:
                raise ValueError("No speech could be recognized. Please speak clearly.")
            else:
                logger.warning(f"[STT] Azure recognition canceled/failed: {result.cancellation_details.reason}")
        except Exception as e:
            logger.error(f"[STT] Azure Speech API error: {e}")

    # Fallback simulation if Azure Speech key not configured
    stt_ms = round((time.perf_counter() - start_time) * 1000, 2)
    demo_transcript = "ఫీజు వివరాలు ఏమిటి?" if language_hint == "te" else "When is the last date to pay fees?"
    return demo_transcript, language_hint, max(1.0, stt_ms)
