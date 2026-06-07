# Sprout Backend

Sprout Backend is a Flask API for herbal plant identification and remedy lookup.

It can:

- classify uploaded plant images through a PyTorch model
- return the top three predictions and an `Unknown` result for low confidence
- enrich known predictions with Trefle plant metadata
- fetch herbal remedy data from Supabase
- serve explore-page data for the frontend

## App Root

The actual backend app is inside:

```text
Backend-Test/
```

Run locally from that folder:

```bash
cd Backend-Test
pip install -r requirements.txt
python app.py
```

## Railway

Use:

```text
Root Directory: /Backend-Test
```

Start command:

```bash
gunicorn app:app --bind "0.0.0.0:${PORT:-5000}"
```

Required Railway variables:

```text
SUPABASE_URL
SUPABASE_KEY
TREFLE_TOKEN
TREFLE_API_URL
```
