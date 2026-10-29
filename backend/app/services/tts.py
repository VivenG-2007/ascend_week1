"""
Text-to-Speech (TTS) Service
Uses Azure AI Speech Neural voices (te-IN-ShrutiNeural / en-IN-NeerjaNeural).
"""
import time
import base64
import logging
from typing import Tuple, Optional
from app.config import settings

logger = logging.getLogger("campusvoice.tts")

def synthesize_speech(
    text: str,
    language: str = "en",
    voice_name: Optional[str] = None
) -> Tuple[Optional[str], float]:
    """
    Synthesizes text into natural spoken speech using Azure AI Speech Neural voices.
    Supports te-IN-ShrutiNeural and te-IN-MohanNeural for Telugu.
    Returns (audio_base64, tts_latency_ms).
    """
    start_time = time.perf_counter()
    if not text.strip():
        return None, 0.0

    selected_voice = voice_name
    if not selected_voice:
        selected_voice = settings.AZURE_SPEECH_TTS_VOICE_TE if language == "te" else settings.AZURE_SPEECH_TTS_VOICE_EN

    if settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_REGION:
        try:
            import azure.cognitiveservices.speech as speechsdk
            speech_config = speechsdk.SpeechConfig(
                subscription=settings.AZURE_SPEECH_KEY,
                region=settings.AZURE_SPEECH_REGION
            )
            speech_config.speech_synthesis_voice_name = selected_voice
            
            # Synthesize to memory stream
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, audio_config=None)
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio_data = result.audio_data
                b64_audio = base64.b64encode(audio_data).decode("utf-8")
                tts_ms = round((time.perf_counter() - start_time) * 1000, 2)
                return b64_audio, tts_ms
            else:
                logger.warning(f"[TTS] Azure TTS failed with voice {selected_voice}: {result.cancellation_details.reason}")
        except Exception as e:
            logger.error(f"[TTS] Azure TTS API error with voice {selected_voice}: {e}")

    tts_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return None, tts_ms

TELUGU_NEURAL_VOICES = {
    "te-IN-ShrutiNeural": {
        "gender": "Female",
        "style": "Warm, natural, clear, conversational (ideal for student helpdesk & interactive guidance)",
        "doc_url": "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts#text-to-speech"
    },
    "te-IN-MohanNeural": {
        "gender": "Male",
        "style": "Authoritative, resonant, formal, professional (ideal for official announcements & circular alerts)",
        "doc_url": "https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts#text-to-speech"
    }
}
