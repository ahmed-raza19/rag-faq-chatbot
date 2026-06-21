"""
Thin wrapper around the Groq API (free tier, Llama 3.3 70B) used as the
generation step in the RAG pipeline. Requires GROQ_API_KEY to be set
(see .env.example). Get a free key at https://console.groq.com
"""

import os

from groq import Groq

GROQ_MODEL = "llama-3.3-70b-versatile"


def get_groq_client() -> Groq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your free key "
            "from https://console.groq.com"
        )
    return Groq(api_key=api_key)


def generate_answer(prompt: str) -> str:
    client = get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
        max_tokens=300,
    )
    return response.choices[0].message.content.strip()
