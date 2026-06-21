"""
RAG FAQ chatbot engine.

Pipeline:
  1. Knowledge base FAQs are embedded with sentence-transformers.
  2. Embeddings are stored in a FAISS index for fast similarity search.
  3. On a user query, the top-k most relevant FAQ entries are retrieved.
  4. Retrieved context is passed to an LLM (Groq / Llama 3.3) which
     generates a natural-language answer grounded in that context.
  5. If retrieval confidence is too low, a fallback response is returned
     instead of letting the LLM hallucinate an answer.
"""

import json
import os

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
FALLBACK_MESSAGE = (
    "I don't have information on that in my knowledge base. "
    "Please contact our support team for further assistance."
)


class RAGEngine:
    def __init__(self, knowledge_base_path: str, embedding_model=None):
        self.knowledge_base_path = knowledge_base_path
        self.embedding_model = embedding_model or SentenceTransformer(
            EMBEDDING_MODEL_NAME
        )
        self.faq_entries = []
        self.index = None
        self._build_index()

    def _build_index(self):
        with open(self.knowledge_base_path, "r", encoding="utf-8") as file:
            self.faq_entries = json.load(file)

        questions = [entry["question"] for entry in self.faq_entries]
        embeddings = self.embedding_model.encode(questions, convert_to_numpy=True)
        embeddings = embeddings.astype("float32")
        faiss.normalize_L2(embeddings)

        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)
        self.index.add(embeddings)

    def retrieve(self, query: str, top_k: int = 3, min_score: float = 0.35) -> list:
        query_embedding = self.embedding_model.encode(
            [query], convert_to_numpy=True
        ).astype("float32")
        faiss.normalize_L2(query_embedding)

        scores, indices = self.index.search(query_embedding, top_k)

        # Adaptive thresholding: if top score is high, lower threshold slightly for context diversity
        top_score = scores[0][0] if len(scores[0]) > 0 else 0
        adaptive_threshold = (
            max(min_score, top_score * 0.7) if top_score > 0.5 else min_score
        )

        results = []
        for score, index in zip(scores[0], indices[0]):
            if index == -1 or score < adaptive_threshold:
                continue
            entry = self.faq_entries[index]
            results.append(
                {
                    "question": entry["question"],
                    "answer": entry["answer"],
                    "score": float(score),
                }
            )

        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results

    def build_prompt(self, query: str, context_entries: list) -> str:
        # Build context with confidence scores
        context_lines = []
        for i, entry in enumerate(context_entries, 1):
            confidence = (
                "high"
                if entry["score"] > 0.7
                else "medium" if entry["score"] > 0.5 else "low"
            )
            context_lines.append(
                f"FAQ #{i} (confidence: {confidence}):\n"
                f"Q: {entry['question']}\n"
                f"A: {entry['answer']}"
            )

        context_block = "\n\n".join(context_lines)

        return (
            "You are a helpful and friendly customer support assistant. "
            "Answer the user's question based ONLY on the FAQ context provided below. "
            "Be concise, natural, and conversational. "
            "If the context doesn't fully address the question, acknowledge what you know and suggest contacting support.\n\n"
            f"FAQ Context:\n{context_block}\n\n"
            f"User Question: {query}\n\n"
            "Provide a helpful, direct answer:"
        )

    def answer(self, query: str, top_k: int = 3, generate_fn=None) -> dict:
        context_entries = self.retrieve(query, top_k=top_k)

        if not context_entries:
            return {
                "query": query,
                "answer": FALLBACK_MESSAGE,
                "source": "fallback",
                "retrieved_context": [],
            }

        if generate_fn is None:
            top_match = context_entries[0]
            return {
                "query": query,
                "answer": top_match["answer"],
                "source": "retrieval_only",
                "retrieved_context": context_entries,
            }

        prompt = self.build_prompt(query, context_entries)
        try:
            generated_answer = generate_fn(prompt)
        except Exception:
            top_match = context_entries[0]
            return {
                "query": query,
                "answer": top_match["answer"],
                "source": "retrieval_only",
                "retrieved_context": context_entries,
            }

        return {
            "query": query,
            "answer": generated_answer,
            "source": "rag_generated",
            "retrieved_context": context_entries,
        }
