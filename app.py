import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from llm_client import generate_answer
from rag_engine import RAGEngine

load_dotenv()

app = FastAPI(
    title="Smart FAQ Chatbot (RAG)",
    description="Retrieval-Augmented Generation chatbot over an FAQ knowledge base.",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

KNOWLEDGE_BASE_PATH = os.path.join("knowledge_base", "faq_data.json")
engine = RAGEngine(KNOWLEDGE_BASE_PATH)

USE_LLM_GENERATION = os.getenv("GROQ_API_KEY") is not None


class ChatRequest(BaseModel):
    message: str
    top_k: int = 3


@app.get("/")
def root():
    return FileResponse("templates/index.html")


@app.get("/status")
def status():
    return {
        "status": "ok",
        "knowledge_base_entries": len(engine.faq_entries),
        "llm_generation_enabled": USE_LLM_GENERATION,
    }


@app.post("/chat")
def chat(request: ChatRequest):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    generate_fn = generate_answer if USE_LLM_GENERATION else None

    try:
        return engine.answer(
            request.message, top_k=request.top_k, generate_fn=generate_fn
        )
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
