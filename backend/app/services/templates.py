"""Fixed, backend-authored message templates (English and Telugu). These never contain model output."""
TEXT = {
    "off_topic": {
        "en": "I can only help with questions about {college}, such as fees, exams, timetables, faculty, hostel, transport and events.",
        "te": "నేను {college} గురించిన ప్రశ్నలకు మాత్రమే సహాయం చేయగలను, ఉదాహరణకు ఫీజులు, పరీక్షలు, టైమ్ టేబుల్, ఫ్యాకల్టీ, హాస్టల్, రవాణా, కార్యక్రమాలు.",
    },
    "refused": {
        "en": "I can't help with that request. I don't have access to personal student records, and I can't share private or internal information.",
        "te": "ఆ అభ్యర్థనకు నేను సహాయం చేయలేను. నా దగ్గర విద్యార్థుల వ్యక్తిగత రికార్డులు లేవు, ప్రైవేట్ లేదా అంతర్గత సమాచారం పంచుకోలేను.",
    },
    "escalated": {
        "en": "I'm not sure about this, so I have raised a ticket with {department}. Your ticket ID is {ticket_id}. They will follow up.",
        "te": "దీనిపై నాకు ఖచ్చితమైన సమాచారం లేదు, కాబట్టి {department} విభాగానికి టికెట్ నమోదు చేశాను. మీ టికెట్ ID {ticket_id}. వారు మిమ్మల్ని సంప్రదిస్తారు.",
    },
    "clarify": {
        "en": "I need a little more detail to answer that. {detail}",
        "te": "దానికి సమాధానం ఇవ్వడానికి మరికొంత సమాచారం కావాలి. {detail}",
    },
    "error": {
        "en": "I had a technical problem looking that up. Please try again in a moment.",
        "te": "ఆ సమాచారం వెతకడంలో సాంకేతిక సమస్య వచ్చింది. దయచేసి కాసేపటి తర్వాత మళ్లీ ప్రయత్నించండి.",
    },
    "unknown_topic": {
        "en": "I can only help with questions about {college}. If your question is about the college, please mention the topic, for example fees, exams, hostel, bus, library or timetable.",
        "te": "నేను {college} గురించిన ప్రశ్నలకు మాత్రమే సహాయం చేయగలను. మీ ప్రశ్న కళాశాల గురించి అయితే, ఫీజులు, పరీక్షలు, హాస్టల్, బస్సు, లైబ్రరీ లేదా టైమ్ టేబుల్ వంటి అంశాన్ని పేర్కొనండి.",
    },
}


def t(key: str, lang: str, **kw: str) -> str:
    return TEXT[key]["te" if lang == "te" else "en"].format(**kw)
