"""
Azure AI Speech Telugu Voice Evaluation Script
Ascend Week-1 | CampusVoice | Geethanjali College of Engineering and Technology

Evaluates and compares Microsoft Azure Neural Voices for Telugu (te-IN):
1. te-IN-ShrutiNeural (Female)
2. te-IN-MohanNeural (Male)

Reference:
https://learn.microsoft.com/en-us/azure/ai-services/speech-service/language-support?tabs=tts#text-to-speech
"""
import os
import sys
import time
from pathlib import Path

# Force UTF-8 console output for Telugu unicode characters on Windows
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

# Add backend to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.config import settings

SAMPLE_TELUGU_QUERIES = [
    {
        "id": "query_1_fees",
        "category": "Accounts & Fees",
        "telugu": "గీతాంజలి ఇంజనీరింగ్ కళాశాలలో సెమిస్టర్ ఫీజు చెల్లించడానికి చివరి తేదీ ఎప్పుడు?",
        "english": "When is the last date to pay semester fees at Geethanjali College of Engineering?"
    },
    {
        "id": "query_2_hod",
        "category": "Faculty & Location",
        "telugu": "కంప్యూటర్ సైన్స్ విభాగం హెచ్‌ఓడి గారి కేబిన్ ఎక్కడ ఉంది?",
        "english": "Where is the Computer Science Department HOD's cabin located?"
    },
    {
        "id": "query_3_timetable",
        "category": "Academics & Timetable",
        "telugu": "సిఎస్ఇ బి సెక్షన్ సోమవారం మొదటి పీరియడ్ ఏమిటి?",
        "english": "What is the first period for CSE-B on Monday?"
    },
    {
        "id": "query_4_circular",
        "category": "Official Circular Alert",
        "telugu": "సర్క్యులర్ నంబర్ 12 ప్రకారం, ఆలస్య రుసుము లేకుండా ట్యూషన్ ఫీజు చెల్లింపు గడువు నవంబర్ 10 వరకు పొడిగించబడింది.",
        "english": "As per Circular No. 12, the deadline for tuition fee payment without late fee is extended to November 10."
    }
]

VOICES_TO_TEST = [
    {
        "name": "te-IN-ShrutiNeural",
        "gender": "Female",
        "style": "Conversational, warm, student-friendly, highly natural inflection",
        "best_for": "Main Helpdesk AI Voice, Interactive Q&A, Push-to-Talk Student Assistance"
    },
    {
        "name": "te-IN-MohanNeural",
        "gender": "Male",
        "style": "Authoritative, resonant, formal, broadcast clarity",
        "best_for": "Official Administrative Notices, Exam Alerts, Escalation Ticket Updates"
    }
]

def run_evaluation():
    print("=" * 80)
    print(" AZURE AI SPEECH — TELUGU (te-IN) NEURAL VOICE EVALUATION")
    print(" Geethanjali College of Engineering and Technology | CampusVoice")
    print("=" * 80)
    print(f"Azure Speech Region: {settings.AZURE_SPEECH_REGION}")
    has_key = bool(settings.AZURE_SPEECH_KEY and settings.AZURE_SPEECH_KEY.strip())
    print(f"Azure Speech Key Configured: {'YES' if has_key else 'NO (Set AZURE_SPEECH_KEY in .env)'}")
    print("-" * 80)

    output_dir = backend_dir / "voice_samples"
    output_dir.mkdir(parents=True, exist_ok=True)

    if has_key:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            print("[ERROR] azure-cognitiveservices-speech not installed.")
            return

    for q_idx, q in enumerate(SAMPLE_TELUGU_QUERIES, 1):
        print(f"\n[Test Case {q_idx}] Category: {q['category']}")
        print(f" Telugu Query : {q['telugu']}")
        print(f" English Meaning: {q['english']}")
        print("-" * 60)

        for v in VOICES_TO_TEST:
            voice_name = v["name"]
            print(f"  > Testing Voice: {voice_name} ({v['gender']})")
            print(f"    Style       : {v['style']}")
            print(f"    Best Suited : {v['best_for']}")

            if has_key:
                try:
                    speech_config = speechsdk.SpeechConfig(
                        subscription=settings.AZURE_SPEECH_KEY,
                        region=settings.AZURE_SPEECH_REGION
                    )
                    speech_config.speech_synthesis_voice_name = voice_name
                    
                    wav_file = output_dir / f"{q['id']}_{voice_name}.wav"
                    file_audio_config = speechsdk.audio.AudioOutputConfig(filename=str(wav_file))
                    synthesizer = speechsdk.SpeechSynthesizer(
                        speech_config=speech_config,
                        audio_config=file_audio_config
                    )

                    t0 = time.perf_counter()
                    result = synthesizer.speak_text_async(q["telugu"]).get()
                    latency_ms = (time.perf_counter() - t0) * 1000

                    if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                        print(f"    Synthesis   : SUCCESS | Latency: {latency_ms:.1f}ms")
                        print(f"    Saved Audio : {wav_file}")
                    else:
                        print(f"    Synthesis   : FAILED ({result.cancellation_details.reason})")
                except Exception as e:
                    print(f"    Synthesis   : ERROR ({e})")
            else:
                print(f"    Simulation  : (Live synthesis requires AZURE_SPEECH_KEY)")

    print("\n" + "=" * 80)
    print(" RECOMMENDATION & ARCHITECTURAL VERDICT:")
    print("=" * 80)
    print("1. te-IN-ShrutiNeural:")
    print("   Recommended for: Primary Voice Assistant & Interactive Helpdesk.")
    print("   Why: Shorter syllables sound warmer and friendlier to students and parents asking questions.")
    print("   Set in .env: AZURE_SPEECH_TTS_VOICE_TE=\"te-IN-ShrutiNeural\"")
    print()
    print("2. te-IN-MohanNeural:")
    print("   Recommended for: Formal Public Addresses & Emergency/Notice Broadcasts.")
    print("   Why: Deeper baritone provides strong institutional authority when reading circulars.")
    print("   Set in .env: AZURE_SPEECH_TTS_VOICE_TE=\"te-IN-MohanNeural\"")
    print()
    print("Switch dynamically at any time by updating AZURE_SPEECH_TTS_VOICE_TE in .env")
    print("=" * 80)

if __name__ == "__main__":
    run_evaluation()
