import io
import os
from groq import Groq
from config import GROQ_MODEL, WHISPER_LANGUAGE


class GroqTranscriber:
    """Cloud transcription via Groq Whisper Large v3 Turbo."""

    def __init__(self):
        self._client = None

    def _get_client(self) -> Groq:
        if self._client is None:
            key = os.getenv("GROQ_API_KEY", "")
            if not key:
                raise ValueError("GROQ_API_KEY not configured")
            self._client = Groq(api_key=key, timeout=10.0)
        return self._client

    def transcribe(self, wav_buffer: io.BytesIO, vocabulary_prompt: str = "") -> str:
        wav_buffer.seek(0)
        data = wav_buffer.read()
        if len(data) < 100:
            return ""
        kwargs = dict(
            file=("recording.wav", data),
            model=GROQ_MODEL,
            language=WHISPER_LANGUAGE,
            response_format="text",
            temperature=0.0,
        )
        if vocabulary_prompt:
            kwargs["prompt"] = vocabulary_prompt
        transcription = self._get_client().audio.transcriptions.create(**kwargs)
        text = transcription.strip() if isinstance(transcription, str) else str(transcription).strip()
        return text

    @property
    def model_id(self) -> str:
        return GROQ_MODEL
