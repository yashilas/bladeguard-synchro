"""
FastAPI wrapper around the Synchronized Figure Skating Materials Assistant.

Exposes:
  GET  /health        -> liveness check
  POST /chat          -> { "message": "..." }  ->  { "reply": "..." }

Run locally:
  uvicorn main:app --reload --port 8000
"""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents import Agent, Runner, function_tool, trace

# ---------------------------------------------------------------------------
# Environment loading
# ---------------------------------------------------------------------------


def load_env(env_path: str = ".env") -> dict:
    """Read variables from a .env file into os.environ and return them."""
    path = Path(env_path)
    if not path.exists():
        # Not fatal for the API — env vars may already be set on the host
        # (e.g. Render/Railway/Fly environment settings).
        return {}

    load_dotenv(dotenv_path=path)

    loaded = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, _ = line.partition("=")
            key = key.strip()
            loaded[key] = os.environ.get(key)
    return loaded


load_env(".env")

# ---------------------------------------------------------------------------
# Materials DB + agent tool
# ---------------------------------------------------------------------------

materials_db_collection = None


@function_tool
def material_lookup_tool(query: str, max_results: int = 3) -> str:
    """
    Tool function to ask a question about glove materials.

    Args:
        query: The question to ask.
        max_results: The maximum number of results to return.

    Returns:
        A string containing information related to the query.
    """
    if materials_db_collection is None:
        return "Materials database is not initialized."

    results = materials_db_collection.query(query_texts=[query], n_results=max_results)

    if not results["documents"][0]:
        return f"No information found for: {query}"

    return "Related answers to your question:\n" + "\n".join(results["documents"][0])


material_agent = Agent(
    name="Synchronized Figure Skating Materials Assistant",
    instructions="""You are a helpful assistant giving out advice on choosing glove materials for synchronized figure skating.
    You give concise answers.
    If you need to look up material information, use the material_lookup_tool.""",
    tools=[material_lookup_tool],
)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI):
    global materials_db_collection
    script_dir = Path(__file__).parent.parent.parent  
    chroma_client = chromadb.PersistentClient(path=script_dir / "chroma")
    materials_db_collection = chroma_client.get_collection(name="materials_db")
    yield


app = FastAPI(title="Materials Chatbot API", lifespan=lifespan)

# Allow the GitHub Pages frontend (or any origin, during development) to call this API.
# In production, replace "*" with your actual Pages URL, e.g.
# ["https://<your-username>.github.io"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message must not be empty")

    with trace("Synchronized Figure Skating Materials Agent"):
        result = await Runner.run(material_agent, message)

    return ChatResponse(reply=result.final_output)
