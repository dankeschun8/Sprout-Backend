# Sprout Backend

Sprout Backend is a Flask REST API for herbal plant identification and remedy exploration. It accepts uploaded plant images, runs a trained PyTorch classifier, enriches known predictions with Trefle plant metadata, and returns Supabase-backed herbal remedy data for the frontend.

The complete project documentation is in [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md).

## What It Does

- `POST /predict`: receives an image, predicts the plant class, returns top 3 predictions, and marks low-confidence results as `Unknown`.
- `GET /api/remedies`: returns herbal remedy records from Supabase.
- `GET /api/remedies/by/<herb_name>`: returns remedies for one herb name.
- `GET /api/explore`: returns paginated herb/remedy data for browse pages.
- `GET /`: health check route.

## Project Layout

```text
Sprout-Backend/
|-- Backend-Test/
|   |-- app.py
|   |-- class_names.json
|   |-- requirements.txt
|   |-- core/
|   |-- routes/
|-- PROJECT_DOCUMENTATION.md
|-- README.md
|-- railway.json
|-- requirements.txt
|-- start.sh
```

The live Flask app is inside `Backend-Test`. The root `requirements.txt`, `start.sh`, and `railway.json` files are included so Railway can detect and run the nested Python app.

## Environment Variables

Set these locally in `Backend-Test/.env` and in Railway:

```text
TREFLE_TOKEN=your_trefle_token
TREFLE_API_URL=https://trefle.io/api/v1/plants/search
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

## Local Setup

```bash
cd Backend-Test
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

On Windows PowerShell:

```powershell
cd Backend-Test
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Railway Deployment

Railway runs:

```bash
bash start.sh
```

`start.sh` starts the app with:

```bash
cd Backend-Test
gunicorn app:app --bind "0.0.0.0:${PORT:-5000}"
```

The model weights are not committed. On startup, the app downloads `weights/internimage.pth` from the configured Google Drive URL if the file is missing or invalid.

## Documentation

Read [PROJECT_DOCUMENTATION.md](PROJECT_DOCUMENTATION.md) for the detailed explanation of:

- project purpose
- backend architecture
- file-by-file source walkthrough
- model inference flow
- API request and response formats
- Supabase and Trefle integration
- local setup
- Railway deployment
- troubleshooting
- limitations and future improvements
