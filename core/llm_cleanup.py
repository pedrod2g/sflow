"""LLM post-processing via Groq Llama — removes filler, fixes punctuation.

Adds ~100-300ms latency. This is THE feature that separates SFlow from
commodity dictation apps. System prompt adapts per active app (context-aware).
"""
import os
from groq import Groq
from config import LLM_CLEANUP_MODEL


_BASE_RULES = """Eres un editor que limpia transcripciones de voz. Devuelve SOLO el texto corregido, sin comentarios.

Reglas:
- Elimina muletillas: eh, um, este, o sea, pues, bueno (cuando son relleno)
- Corrige puntuación: puntos, comas, signos de interrogación
- Capitaliza inicio de oraciones y nombres propios
- Preserva el significado exacto — NO parafrasees ni inventes
- Preserva el idioma original (si habla español, responde en español)
- Preserva números como dígitos si así se dictaron
- NO agregues saludos ni despedidas que no estén
- NO agregues markdown salvo que el contexto lo pida"""


TONE_PROFILES = {
    "casual": "Tono: casual, natural. Permite emojis si el contexto sugiere chat.",
    "formal": "Tono: formal, profesional. Sin emojis. Puntuación rigurosa.",
    "code": "Contexto: código. Preserva símbolos, nombres en inglés, camelCase, snake_case. NO corrijas términos técnicos.",
    "email": "Contexto: email. Formal pero amigable. Saluda solo si se dicta. Estructura párrafos.",
    "chat": "Contexto: mensaje corto (Slack/WhatsApp/Discord). Conciso. Emojis permitidos si encajan.",
    "note": "Contexto: nota personal. Mantén el tono del que habla, mínima edición.",
    "default": "Tono: neutral.",
}


class LLMCleanup:
    def __init__(self):
        self._client = None

    def _get_client(self) -> Groq:
        if self._client is None:
            key = os.getenv("GROQ_API_KEY", "")
            if not key:
                raise ValueError("GROQ_API_KEY not configured")
            self._client = Groq(api_key=key, timeout=8.0)
        return self._client

    def clean(self, text: str, tone: str = "default") -> str:
        if not text or len(text.strip()) < 3:
            return text

        tone_rule = TONE_PROFILES.get(tone, TONE_PROFILES["default"])
        system_prompt = f"{_BASE_RULES}\n\n{tone_rule}"

        try:
            completion = self._get_client().chat.completions.create(
                model=LLM_CLEANUP_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text},
                ],
                temperature=0.2,
                max_tokens=1500,
            )
            cleaned = completion.choices[0].message.content.strip()
            # Strip markdown code fences if LLM added them
            if cleaned.startswith("```") and cleaned.endswith("```"):
                cleaned = cleaned.strip("`").strip()
            return cleaned or text
        except Exception:
            return text
