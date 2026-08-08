# <a href="https://yashilas.github.io/bladeguard-synchro" style="text-decoration: none; color: inherit;"><img src="GlideRiseGlove.png" alt="bladeguard-synchro" width="100" height="100" align="center"> bladeguard-synchro</a>

<div class="text-box">
    <strong>bladeguard-synchro</strong> — Ultra-thin, high-impact protective wearables for hand and finger safety in synchronized figure skating. This repository documents material research, prototype design, impact/cut testing, and collaboration efforts to address a critical safety gap in a growing sport.
</div>

## Purpose
bladeguard-synchro is a research and prototype project focused on developing ultra-thin protective wearables for hand and finger safety in synchronized figure skating. The main goal is to protect skaters from blade run-over injuries while preserving dexterity and grip.

## Project Overview

`bladeguard-synchro` combines materials research and a lightweight assistant interface to help design protective glove solutions for synchronized skating. The repository includes:

-  **FastAPI backend** that wraps glove material reasoning and exposes a `POST /chat` API.
-  **static frontend** chat widget that calls the API and displays structured material recommendations.
-  **Chroma knowledge collection** used for material lookup, retrieval, and response generation.
-  deployment-focused workflow that supports local testing and static hosting while keeping the actual API on a real backend host.

The project’s goal is to protect skaters from blade run-over injuries while preserving grip, flexibility, and comfort in performance footwear.

What it includes
-  Materials research: Evaluates materials for cut resistance, impact absorption, flexibility, and thermal comfort.
-  Prototype design: Targets a low-profile protective system that can fit inside skating gloves and still allow full finger movement.
-  Testing focus: Aims to reduce impact injuries and improve blade cut protection without bulky padding.

Application components
- **backend/** — FastAPI wrapper exposing the agent as a `POST /chat` API
    - FastAPI server providing a POST /chat endpoint.
    - Uses a materials_db Chroma collection for retrieval or RAG-style response generation.
    - Wraps glove_agent.py logic into an API, so the assistant can answer questions like “best material for grip in cold rinks”.
    - Supports local development on http://localhost:8000.
- **frontend/** — a static page (deployable to GitHub Pages) that calls the API and shows the reply (frontend or root index.html):
    -  Static web UI with a chat widget for asking material and glove design questions.
    -  Built as a single-page interface, designed for easy deployment to GitHub Pages.
    -  Includes a configurable API URL setting that can be stored in browser localStorage.

Key features
- Chatbot interface: A bottom-right popup assistant that accepts user questions and displays structured replies.
- Configurable API endpoint: Frontend reads the backend URL from a config file or saved settings, avoiding hardcoded endpoints.
- Chroma collection lifecycle: Backend initializes or reuses a persistent Chroma collection for material knowledge.
- Single-file frontend: No build step needed for the frontend, making deployment simple.

Deployment notes
- The backend must run on a real host since GitHub Pages only serves static files.
- The frontend can be served from GitHub Pages or any static site host.
- Backend depends on environment variables like OPENAI_API_KEY and optionally OPENAI_DEFAULT_MODEL.

Structure
-  index.html — main public-facing landing page and chat UI
-  main.py — FastAPI backend entrypoint
-  glove_agent.py — agent logic and material reasoning
-  glove_screener.py — material screening utilities
-  rag_setup.py / rank_materials.py — data retrieval and ranking helpers
-  create_materials_db.py — build or prepare the Chroma collection
-  frontend — standalone frontend assets
-  data — datasets and material database files
-  chroma — Chroma database storage

Value proposition  
  This project combines materials science research with a lightweight interactive assistant to help users choose glove materials for synchronized skating. It is both a documentation/research repo and a small web app prototype for material recommendation.

# bladeguard-synchro Chatbot Deployment

## 1. Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt
cp .env.example .env   # then fill in OPENAI_API_KEY and OPENAI_DEFAULT_MODEL
```

You also need a Chroma collection named `materials_db` at `./chroma` (same as the
original script expected) — the API loads it once at startup.

Run it locally:

```bash
uvicorn main:app --reload --port 8000
```

Check it's alive: `curl http://localhost:8000/health`

Test a chat call:

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Best material for grip in cold rinks?"}'
```

### Deploying the backend
`uvicorn`/FastAPI needs a real host (GitHub Pages only serves static files, so the
API can't live there). Any small host works — Render, Railway, Fly.io, a VM, etc.
Whichever you use:
- set `OPENAI_API_KEY` / `OPENAI_DEFAULT_MODEL` as environment variables on the host
- make sure your `chroma` folder (or however you build the collection) ships with the deploy
- note the public URL, e.g. `https://materials-api.onrender.com` — you'll paste this into the frontend

For production, also tighten CORS in `main.py`:
```python
allow_origins=["https://<your-username>.github.io"]
```

## 2. Frontend (GitHub Pages)

`frontend/index.html` is a single self-contained file — no build step.

1. Push this repo to GitHub.
2. In the repo settings → **Pages**, set the source to the `frontend/` folder (or `main` branch root, if you move `index.html` there).
3. Open the published page, expand **API settings**, and paste your deployed backend URL (e.g. `https://materials-api.onrender.com`). It's saved in the browser via `localStorage` so you only enter it once.
4. Ask a question — the page calls `POST {api-url}/chat` and renders the reply.

While developing, you can leave the API URL as `http://localhost:8000` and run the backend locally with CORS wide open (already the default in `main.py`).

## Notes on the original script

- `load_env`, the `material_lookup_tool`, and the `material_agent` definition are unchanged in spirit — just wrapped by FastAPI instead of a `if __name__ == "__main__"` block.
- The commented-out manual query/demo code from the original script was left out of the API since it's not needed for serving requests.
- `openai-agents` is the assumed PyPI package name for the `agents` import — adjust `requirements.txt` if your environment uses a different source/install method.

## Go to frontend floder in the terminal

python -m http.server 5500
http://localhost:5500/index.html