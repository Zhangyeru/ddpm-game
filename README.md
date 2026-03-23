# Noise Archaeologist Prototype

This repository now contains a playable scaffold for the DDPM web game concept from `DDPM_WEB_GAME_MVP.md`.

## Structure

- `frontend/`: React + Vite single-page prototype
- `backend/`: FastAPI mock gameplay service
- `DDPM_WEB_GAME_MVP.md`: product and technical design

## What The Prototype Does

- Starts a denoise session with one hidden target
- Streams locally loaded offline denoise trajectories from the backend
- Lets the player guess from six candidates
- Supports three guidance cards
- Supports one freeze-region action
- Scores a round and reveals the target on win/loss

The backend now reads a local offline trajectory manifest from `backend/assets/trajectories/manifest.json`. The manifest is generated from bundled source photos in `backend/assets/source-images/` and stores precomputed `webp` frame paths for each target, sample, and guidance variant.

If you need to refresh the bundled seed photos from Wikimedia Commons:

```bash
python3 backend/scripts/download_seed_images.py
```

If you need to regenerate the offline trajectories:

```bash
python3 backend/scripts/generate_trajectory_assets.py
```

## Run The Backend

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --reload --app-dir backend
```

The API will be available at `http://localhost:8000`.

## Run The Frontend

```bash
cd frontend
npm install
npm run dev
```

The app expects the API at `http://localhost:8000/api` by default.

To override that:

```bash
VITE_API_BASE_URL=http://localhost:8000/api npm run dev
```

## Next Recommended Steps

1. Curate or replace the bundled source photos with a more consistent art direction.
2. Swap polling for WebSocket pushes if you want smoother pacing.
3. Add a lightweight level config system and persistent progression.
4. Move from candidate-only guessing to optional typed guesses once the base pacing feels right.
