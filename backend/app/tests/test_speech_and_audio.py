import json
import logging

import httpx
import pytest

from app.config import Settings
from app.services.audio import SILENCE_RMS, AudioError, validate_audio
from app.services.stt import AzureStt, SpeechError
from app.services.tts import AzureTts, make_spoken
from app.tests.conftest import make_wav

CFG = dict(azure_speech_key="SPEECH-SECRET-KEY", azure_speech_region="centralindia", _env_file=None)


def stt_with(handler, **extra):
    return AzureStt(Settings(**CFG, **extra), httpx.Client(transport=httpx.MockTransport(handler)))


def ok(text, conf=0.9):
    return httpx.Response(200, json={"RecognitionStatus": "Success", "DisplayText": text, "NBest": [{"Display": text, "Confidence": conf}]})


def test_stt_success_uses_expected_endpoint_and_headers():
    seen = []

    def h(req):
        seen.append(req)
        return ok("When is the fee deadline?")

    r = stt_with(h).transcribe(make_wav(), "en")
    req = seen[0]
    assert r.text == "When is the fee deadline?" and r.language == "en"
    assert req.url.host == "centralindia.stt.speech.microsoft.com" and req.url.params["language"] == "en-IN"
    assert req.headers["ocp-apim-subscription-key"] == "SPEECH-SECRET-KEY" and "audio/wav" in req.headers["content-type"]


def test_stt_auto_tries_both_languages_and_keeps_the_more_confident():
    def h(req):
        return ok("ఫీజు చివరి తేదీ ఎప్పుడు", 0.93) if req.url.params["language"] == "te-IN" else ok("fees", 0.41)

    r = stt_with(h).transcribe(make_wav(), "auto")
    assert r.language == "te" and r.confidence == 0.93


@pytest.mark.parametrize("status", ["NoMatch", "InitialSilenceTimeout"])
def test_stt_silence_is_reported_as_empty(status):
    with pytest.raises(SpeechError) as e:
        stt_with(lambda r: httpx.Response(200, json={"RecognitionStatus": status})).transcribe(make_wav(), "en")
    assert e.value.empty


def test_stt_errors_are_friendly_and_never_leak_the_key():
    for resp in (httpx.Response(401), httpx.Response(500), httpx.Response(200, json={"RecognitionStatus": "Error"})):
        with pytest.raises(SpeechError) as e:
            stt_with(lambda r, resp=resp: resp).transcribe(make_wav(), "en")
        assert "SPEECH-SECRET-KEY" not in e.value.message and "type" in e.value.message.lower()


def test_stt_network_failure_is_a_speech_error():
    def boom(req):
        raise httpx.ConnectError("down")

    with pytest.raises(SpeechError):
        stt_with(boom).transcribe(make_wav(), "en")


def test_stt_requires_configuration():
    with pytest.raises(SpeechError):
        AzureStt(Settings(_env_file=None))


def tts_with(handler, **extra):
    return AzureTts(Settings(**CFG, **extra), httpx.Client(transport=httpx.MockTransport(handler)))


def test_tts_picks_voice_by_language_and_escapes_ssml():
    seen = []

    def h(req):
        seen.append(req)
        return httpx.Response(200, content=b"mp3bytes")

    t = tts_with(h)
    assert t.synthesize("Fees <due> & more", "en") == b"mp3bytes"
    t.synthesize("ఫీజు", "te")
    en_body, te_body = seen[0].content.decode(), seen[1].content.decode()
    assert "en-IN-NeerjaNeural" in en_body and "&lt;due&gt; &amp; more" in en_body
    assert "te-IN-ShrutiNeural" in te_body and "te-IN" in te_body
    assert seen[0].headers["x-microsoft-outputformat"].endswith("mp3") and seen[0].url.host == "centralindia.tts.speech.microsoft.com"


def test_tts_voices_are_configurable():
    seen = []
    t = tts_with(lambda r: (seen.append(r), httpx.Response(200, content=b"x"))[1], azure_speech_tts_voice_te="te-IN-MohanNeural")
    t.synthesize("నమస్తే", "te")
    assert "te-IN-MohanNeural" in seen[0].content.decode()


def test_tts_failure_is_a_speech_error():
    with pytest.raises(SpeechError):
        tts_with(lambda r: httpx.Response(500)).synthesize("hello", "en")


def test_make_spoken_strips_markdown_and_limits_words():
    long = "**Fees** are due. " + "This is a filler sentence with several words. " * 20
    spoken = make_spoken(long)
    assert "*" not in spoken and len(spoken.split()) <= 40 and spoken.endswith(".")
    assert make_spoken("Short answer.") == "Short answer."


# ------------------------------------------------------------------------------ audio
def test_valid_wav_is_accepted():
    info = validate_audio(make_wav(2.0), 30)
    assert abs(info.duration_s - 2.0) < 0.01 and info.sample_rate == 16000 and info.rms > SILENCE_RMS


def test_silent_audio_has_low_rms():
    assert validate_audio(make_wav(1.0, amplitude=0), 30).rms < SILENCE_RMS


@pytest.mark.parametrize("data,codes", [(b"", {422}), (b"not audio at all", {415, 422}), (make_wav(0.1), {422}), (make_wav(35), {422}),
                                        (make_wav(1.0, channels=2), {415}), (make_wav(1.0, rate=4000), {415})])
def test_invalid_audio_is_rejected_with_a_user_message(data, codes):
    with pytest.raises(AudioError) as e:
        validate_audio(data, 30)
    assert e.value.status_code in codes and e.value.message


def test_oversize_audio_rejected():
    with pytest.raises(AudioError) as e:
        validate_audio(b"RIFF" + b"0" * 100, 30, max_bytes=50)
    assert e.value.status_code == 413
