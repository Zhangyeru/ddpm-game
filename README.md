# Noise Archaeologist Prototype

This repository now contains a playable scaffold for the DDPM web game concept from `DDPM_WEB_GAME_MVP.md`.

## Structure

- `frontend/`: React + Vite single-page prototype
- `backend/`: FastAPI mock gameplay service
- `deploy/`: `systemd` / `nginx` / env deployment templates
- `DDPM_WEB_GAME_MVP.md`: product and technical design

## What The Prototype Does

- Starts a denoise session with one hidden target
- Streams locally loaded offline denoise trajectories from the backend
- Lets the player guess from six candidates
- Supports three guidance cards
- Supports one freeze-region action
- Supports differentiated level rules such as family commit, masked candidates, rotating echoes, single-card contracts, corruption thresholds, and evidence debt
- Scores a round and reveals the target on win/loss

The backend now reads a local offline trajectory manifest from `backend/assets/trajectories/manifest.json`. The current checked-in manifest still ships precomputed `webp` frame paths, and the generator has been upgraded to support 100-step real DDIM inversion trajectories from bundled source photos in `backend/assets/source-images/`.

If you need to refresh the bundled seed photos from Wikimedia Commons:

```bash
python3 backend/scripts/download_seed_images.py
```

If you need to regenerate the offline trajectories:

```bash
python3 backend/scripts/generate_trajectory_assets.py
```

Useful generation flags:

```bash
python3 backend/scripts/generate_trajectory_assets.py \
  --device auto \
  --model-id runwayml/stable-diffusion-v1-5 \
  --num-steps 100 \
  --targets cat \
  --sample-ids sample-01 \
  --variant-keys base \
  --output-root /tmp/game-demo-trajectories
```

Notes:

- Full 100-step asset refresh is intended for a CUDA machine.
- CPU generation is supported for small scoped runs, but it is slow.

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

For same-origin deployment behind Nginx, build with:

```bash
VITE_API_BASE_URL=/api npm run build
```

## Deploy For Tens Of Users

This project is fine for a small shared deployment on one Linux server:

- `Nginx` serves the built frontend
- `Nginx` proxies `/api/` to FastAPI
- `systemd` keeps the backend running
- SQLite remains the backing store

The checked-in deployment templates are:

- [deploy/backend.env.example](/home/anfield/project/game-demo/deploy/backend.env.example)
- [deploy/systemd/noise-archaeologist-backend.service](/home/anfield/project/game-demo/deploy/systemd/noise-archaeologist-backend.service)
- [deploy/nginx/noise-archaeologist.conf.example](/home/anfield/project/game-demo/deploy/nginx/noise-archaeologist.conf.example)

### Quick Deploy On This Machine

If you are deploying directly from this host with the current LAN address `10.80.247.62`, the shortest path is:

```bash
cd /home/anfield/project/game-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd frontend
npm install
VITE_API_BASE_URL=/api npm run build

cd /home/anfield/project/game-demo
sudo mkdir -p /etc/noise-archaeologist
sudo cp deploy/backend.env.example /etc/noise-archaeologist/backend.env
sudo editor /etc/noise-archaeologist/backend.env

sudo cp deploy/systemd/noise-archaeologist-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now noise-archaeologist-backend

sudo cp deploy/nginx/noise-archaeologist.conf.example /etc/nginx/sites-available/noise-archaeologist.conf
sudo ln -s /etc/nginx/sites-available/noise-archaeologist.conf /etc/nginx/sites-enabled/noise-archaeologist.conf
sudo nginx -t
sudo systemctl reload nginx
```

After that, the site should be reachable at:

- `http://10.80.247.62/`

### 1. Prepare The Backend

```bash
cd /home/anfield/project/game-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Copy the example env file and replace the secret:

```bash
sudo mkdir -p /etc/noise-archaeologist
sudo cp deploy/backend.env.example /etc/noise-archaeologist/backend.env
sudo editor /etc/noise-archaeologist/backend.env
```

### 2. Build The Frontend

```bash
cd /home/anfield/project/game-demo/frontend
npm install
VITE_API_BASE_URL=/api npm run build
```

### 3. Install The Backend Service

If you are deploying from this machine as-is, you can use [deploy/systemd/noise-archaeologist-backend.service](/home/anfield/project/game-demo/deploy/systemd/noise-archaeologist-backend.service) directly.

If you move the project later, update:

- `User=anfield`
- `/home/anfield/project/game-demo`

Then install it:

```bash
sudo cp deploy/systemd/noise-archaeologist-backend.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now noise-archaeologist-backend
sudo systemctl status noise-archaeologist-backend
```

### 4. Install Nginx

If you are exposing this exact machine on the current local network, you can use [deploy/nginx/noise-archaeologist.conf.example](/home/anfield/project/game-demo/deploy/nginx/noise-archaeologist.conf.example) directly with `10.80.247.62`.

If you later switch to a domain or another server path, update:

- `server_name 10.80.247.62`
- `/home/anfield/project/game-demo`

Then install it:

```bash
sudo cp deploy/nginx/noise-archaeologist.conf.example /etc/nginx/sites-available/noise-archaeologist.conf
sudo ln -s /etc/nginx/sites-available/noise-archaeologist.conf /etc/nginx/sites-enabled/noise-archaeologist.conf
sudo nginx -t
sudo systemctl reload nginx
```

After that:

- frontend: `http://10.80.247.62/`
- backend through nginx: `http://10.80.247.62/api/`

### Notes

- This same-origin layout avoids frontend CORS issues.
- For public traffic, put HTTPS in front of the Nginx server block.
- The backend service binds to `127.0.0.1:8000`, so only Nginx exposes it externally.

## Next Recommended Steps

1. Run the full 100-step diffusion refresh on a GPU box and replace the checked-in 24-frame manifest.
2. Curate or replace the bundled source photos with a more consistent art direction.
3. Swap polling for WebSocket pushes if you want smoother pacing.
4. Add a lightweight level config system and persistent progression.
