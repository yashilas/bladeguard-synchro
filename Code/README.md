# bladeguard-synchro
bladeguard-synchro — Ultra-thin, high-impact protective wearables for hand and finger safety in synchronized figure skating. This repository documents material research, prototype design, impact/cut testing, and collaboration efforts to address a critical safety gap in a growing sport.

# Glove Materials Chatbot

Turns `glove_agent.py` into a small web app:

- **backend/** — FastAPI wrapper exposing the agent as a `POST /chat` API
- **frontend/** — a static page (deployable to GitHub Pages) that calls the API and shows the reply

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