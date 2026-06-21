# Smart FAQ Chatbot (RAG-Based System)

A Retrieval-Augmented Generation chatbot: FAQ entries are embedded and stored
in a FAISS vector index, the most relevant entries are retrieved per query,
and a free-tier LLM (Groq / Llama 3.3 70B) generates a natural-language
answer grounded strictly in that retrieved context.

## Architecture

```
FAQ knowledge base (JSON)
        │
        ▼
sentence-transformers embeddings (all-MiniLM-L6-v2)
        │
        ▼
FAISS vector index (cosine similarity via normalized inner product)
        │
        ▼
User query ──► embed ──► FAISS search ──► top-k relevant FAQ entries
        │
        ▼
   score < threshold?
    ├── Yes ──► fallback message (no hallucination)
    └── No  ──► build grounded prompt ──► Groq LLM ──► generated answer
```

## Project Structure

```
04-rag-faq-chatbot/
├── knowledge_base/
│   └── faq_data.json     # FAQ knowledge base
├── rag_engine.py          # embeddings, FAISS index, retrieval + answer logic
├── llm_client.py           # Groq API wrapper (generation step)
├── app.py                  # FastAPI application
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Get a **free** Groq API key at [console.groq.com](https://console.groq.com) and
add it to `.env`:

```
GROQ_API_KEY=your_key_here
```

> The first run will download the `all-MiniLM-L6-v2` embedding model (~80MB)
> from Hugging Face — this requires an internet connection once, then it's
> cached locally.

## Usage

### 1. Run the API

```bash
uvicorn app:app --reload
```

Visit `http://127.0.0.1:8000/docs` for interactive Swagger documentation.

### 2. Chat with the bot

```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I get my money back for a return?"}'
```

Response:

```json
{
  "query": "How do I get my money back for a return?",
  "answer": "You can get a full refund within 14 days of purchase as long as the item is unused and in its original packaging. Refunds are processed within 5-7 business days.",
  "source": "rag_generated",
  "retrieved_context": [
    { "question": "What is your refund policy?", "answer": "...", "score": 0.81 }
  ]
}
```

## Behavior Notes

- **No `GROQ_API_KEY` set?** The app still works — it falls back to returning
  the top-matched FAQ answer directly (`"source": "retrieval_only"`) instead
  of failing. This makes the project runnable and demoable with zero API
  cost or setup.
- **Fallback handling**: if no FAQ entry crosses the similarity threshold
  (default `0.35`), the bot returns a clear "I don't have information on
  that" message rather than letting the LLM guess.
- **Extending the knowledge base**: add more `{ "question": ..., "answer": ... }`
  objects to `knowledge_base/faq_data.json` — the index rebuilds automatically
  on app startup.
