import os
from groq import Groq
from core.settings import app_settings

class TextRefiner:
    def __init__(self):
        self.client = None

    def _init_client(self):
        if self.client is None:
            api_key = os.environ.get("GROQ_API_KEY")
            if api_key:
                self.client = Groq(api_key=api_key)

    def refine(self, text: str) -> str:
        if not app_settings.refinement_enabled:
            return text

        self._init_client()
        if not self.client:
            return text

        prompt_instructions = f"Por favor, toma el siguiente texto desordenado (transcripción de voz) y reestructura su contenido utilizando un formato de: '{app_settings.refinement_format}'."
        if app_settings.refinement_context:
            prompt_instructions += f"\nContexto adicional: '{app_settings.refinement_context}'."
            
        prompt_instructions += "\nDevuelve UNICAMENTE el texto procesado sin preámbulos, delimitadores ni comentarios adicionales."

        try:
            chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": prompt_instructions
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ],
                model="llama3-70b-8192", # Default groq fast and capable model
                temperature=0.3,
            )
            return chat_completion.choices[0].message.content.strip()
        except Exception as e:
            print(f"Refinement error: {e}")
            return text
