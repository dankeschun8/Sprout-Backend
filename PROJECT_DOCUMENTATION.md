# Sprout Backend Project Documentation

## 1. What This Project Is For

Sprout Backend is the server-side API for a herbal plant identification and remedy exploration application. Its main job is to connect three important parts of the system:

1. A frontend that sends plant images and requests herb data.
2. A trained PyTorch image classification model that predicts which herbal plant appears in an uploaded image.
3. External data services, especially Supabase for remedy records and Trefle for plant metadata and images.

In practical terms, the backend lets a user upload a plant image, receives that image through a Flask API, runs machine learning inference, returns the most likely plant class, and enriches the result with scientific, Indonesian, common-name, and image information where available.

The project is designed for an application called Sprout, although the home route still returns the older text `Herbify backend is running`.

## 2. High-Level System Summary

Sprout Backend provides these core capabilities:

| Capability | What It Does |
|---|---|
| Image prediction | Accepts an uploaded image and classifies it into one of 113 known herbal plant classes. |
| Confidence filtering | Returns `Unknown` when the model's top confidence is below `0.7`. |
| Plant name parsing | Splits class labels into scientific/English names and Indonesian names. |
| Trefle enrichment | Looks up plant metadata from Trefle, including scientific name, common name, and image URL. |
| Remedy browsing | Reads herbal recipe/remedy records from Supabase. |
| Remedy lookup | Retrieves remedies for a specific herb name. |
| Explore pagination | Returns paginated herb/remedy cards for frontend browse pages. |
| Railway deployment | Includes root deployment files so Railway can detect, build, and run the app. |

The backend is not a full user-management system. It does not currently store prediction history, authenticate users, or save uploaded images permanently.

## 3. Project Directory Structure

```text
Sprout-Backend/
|-- .gitattributes
|-- .gitignore
|-- PROJECT_DOCUMENTATION.md
|-- README.md
|-- railway.json
|-- requirements.txt
|-- start.sh
|-- Backend-Test/
    |-- .env
    |-- app.py
    |-- class_names.json
    |-- FLASK_BACKEND_GUIDE.md
    |-- requirements.txt
    |-- supabase-flask-guide.md
    |-- core/
    |   |-- __init__.py
    |   |-- inference.py
    |   |-- model.py
    |   |-- plant_info.py
    |-- routes/
    |   |-- __init__.py
    |   |-- explore.py
    |   |-- predict.py
    |-- uploads/
    |-- weights/
    |-- venv/
```

Some folders are local-only and ignored by Git:

| Path | Purpose | Git Status |
|---|---|---|
| `Backend-Test/.env` | Local API keys and service URLs. | Ignored |
| `Backend-Test/uploads/` | Temporary uploaded image storage. | Ignored |
| `Backend-Test/weights/` | Local PyTorch model weights. | Ignored |
| `Backend-Test/venv/` | Local Python virtual environment. | Ignored |
| `__pycache__/` | Python bytecode cache. | Ignored |

## 4. Current Source Files

### 4.1 `Backend-Test/app.py`

This is the Flask application entry point. It performs the startup sequence for the backend:

1. Loads environment variables with `load_dotenv()`.
2. Checks whether the model weights file exists and looks valid.
3. Downloads the model weights from Google Drive if the local weights file is missing or invalid.
4. Imports and registers route blueprints.
5. Creates the Flask app.
6. Enables CORS.
7. Exposes the home health-check route.
8. Runs Flask in debug mode when started directly.

Important constants:

```python
MODEL_PATH = "weights/internimage.pth"
MODEL_URL = "https://drive.google.com/uc?id=1zcQ6sa-mVxv6y5OWqTtHT5Mn0dyiGrEp"
```

The path is relative to the working directory. This is why local execution and Railway deployment should start from inside `Backend-Test`.

The model validation function checks three conditions:

| Check | Why It Exists |
|---|---|
| File does not exist | The app cannot run inference without weights. |
| File is smaller than 10 MB | Real model weights are much larger; tiny files are probably placeholders. |
| File begins like a Git LFS pointer | Git LFS pointer files are metadata, not usable model weights. |

The app imports route blueprints only after the model file check. That order matters because importing the prediction route imports `core.inference`, and `core.inference` immediately loads the model weights.

### 4.2 `Backend-Test/routes/predict.py`

This file defines the image prediction route.

Main objects:

```python
predict_bp = Blueprint("predict", __name__)
UPLOAD_FOLDER = "uploads"
```

The route accepts image uploads at:

```text
POST /predict
```

The uploaded file must be sent as multipart form data with the field name:

```text
image
```

The route flow is:

1. Check that `image` exists in `request.files`.
2. Reject empty filenames.
3. Sanitize the filename with `secure_filename()`.
4. Save the uploaded file temporarily in `uploads/`.
5. Call `predict(image_path)` from `core.inference`.
6. If the model result is known, extract the main plant name and Indonesian plant name.
7. Fetch plant details from Trefle through `core.plant_info.get_plant_info()`.
8. Return the final JSON response.
9. Delete the temporary uploaded image in the `finally` block.

The route has two helper functions:

| Function | Input Example | Output Example |
|---|---|---|
| `extract_plant_name()` | `Aloe Vera (Lidah Buaya)` | `Aloe Vera` |
| `get_indonesian_name()` | `Aloe Vera (Lidah Buaya)` | `Lidah Buaya` |

These helpers rely on the class-label format stored in `class_names.json`.

### 4.3 `Backend-Test/routes/explore.py`

This file defines endpoints for remedy and explore data. It connects to Supabase using:

```python
supabase_client.create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
```

The route module expects two Supabase tables:

| Table | Expected Purpose |
|---|---|
| `herbs` | Stores herb IDs, herb names, and scientific names. |
| `herbal_recipes` | Stores remedy instructions, uses, dosage, warnings, and relationships to herbs. |

The module defines two Supabase select strings:

| Constant | Purpose |
|---|---|
| `REMEDY_SELECT` | Selects remedy fields and joined herb name. |
| `EXPLORE_SELECT` | Selects recipe fields plus joined herb ID, herb name, and scientific name. |

The helper `format_remedy(item)` flattens Supabase's nested join response into a simpler JSON shape.

### 4.4 `Backend-Test/core/inference.py`

This file loads the trained model and exposes the `predict(image_path)` function used by the `/predict` route.

Important constants:

```python
WEIGHTS_PATH = "weights/internimage.pth"
CLASS_NAMES_PATH = "class_names.json"
IMAGE_SIZE = 128
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
```

The file does model setup at import time:

1. Disables gradient calculation globally with `torch.set_grad_enabled(False)`.
2. Loads class labels from `class_names.json`.
3. Creates an `InternImageClassifier` with the correct number of output classes.
4. Moves the model to GPU if CUDA is available, otherwise CPU.
5. Loads the checkpoint from `weights/internimage.pth`.
6. Loads `checkpoint["model_state_dict"]` into the model.
7. Sets the model to evaluation mode.
8. Defines the image preprocessing transform.

The preprocessing pipeline:

```python
transforms.Resize((128, 128))
transforms.ToTensor()
transforms.Normalize(
    mean=[0.485, 0.456, 0.406],
    std=[0.229, 0.224, 0.225]
)
```

The `predict()` function:

1. Opens the uploaded image with PIL.
2. Converts it to RGB.
3. Applies the transform.
4. Adds a batch dimension.
5. Moves the tensor to the selected device.
6. Runs the model inside `torch.inference_mode()`.
7. Applies softmax to produce probabilities.
8. Extracts the top three predictions.
9. Returns `Unknown` when the top confidence is below `0.7`.

### 4.5 `Backend-Test/core/model.py`

This file defines the neural network class:

```python
class InternImageClassifier(nn.Module)
```

Although the class is named `InternImageClassifier`, the current implementation uses a ConvNeXt Tiny backbone from the `timm` library:

```python
timm.create_model(
    "convnext_tiny",
    pretrained=pretrained,
    num_classes=0,
    drop_path_rate=drop_path_rate,
)
```

The model consists of three conceptual parts:

| Part | Purpose |
|---|---|
| ConvNeXt Tiny backbone | Extracts visual features from the image. |
| Global context block | Learns channel-wise weighting for extracted features. |
| Classification head | Converts pooled features into class logits. |

The global context block uses adaptive average pooling, two 1x1 convolutions, GELU activation, and sigmoid activation. It creates a feature weighting mask and multiplies that mask with the backbone feature map.

The classification head uses:

1. `LayerNorm`
2. `Dropout`
3. `Linear`

The forward pass is:

```text
input image tensor
-> ConvNeXt feature extraction
-> global context weighting
-> spatial mean pooling
-> classification head
-> logits for 113 plant classes
```

### 4.6 `Backend-Test/core/plant_info.py`

This file centralizes Trefle API access so prediction and explore routes do not duplicate the same lookup logic.

The function:

```python
get_plant_info(plant_name)
```

does this:

1. Replaces spaces in the plant name with hyphens.
2. Sends a GET request to `TREFLE_API_URL`.
3. Includes `TREFLE_TOKEN` as a query parameter.
4. Reads the first item from the returned `data` array.
5. Returns only the fields the frontend needs.

Returned object:

```json
{
  "scientific_name": "Aloe vera",
  "common_name": "Aloe",
  "image_url": "https://example.com/image.jpg"
}
```

If Trefle fails, returns no data, or raises an exception, the function returns `None`.

### 4.7 `Backend-Test/class_names.json`

This file contains the class labels used by the model. The project currently has 113 classes.

Each model output index maps directly to a class label in this file. The order must stay synchronized with the model training output order.

Example labels:

```text
Abelmoschus Esculentus (Okra)
Acorus Calamus (Dlingo)
Aloe Vera (Lidah Buaya)
Alstonia Scholaris (Pulai)
Amaranthus Spinosus (Bayam Duri)
```

The label convention is:

```text
Scientific or English Name (Indonesian Name)
```

The prediction route depends on this convention to extract Indonesian names for remedy lookups.

### 4.8 `Backend-Test/requirements.txt`

This file contains Python dependencies needed by the backend.

| Package | Purpose |
|---|---|
| `flask` | Web API framework. |
| `flask-cors` | Allows cross-origin frontend requests. |
| `python-dotenv` | Loads local environment variables from `.env`. |
| `requests` | Calls the Trefle API. |
| `supabase` | Connects to Supabase tables. |
| `gdown` | Downloads model weights from Google Drive. |
| `torch` | Runs the PyTorch model. |
| `torchvision` | Provides image transforms. |
| `timm` | Provides the ConvNeXt Tiny model backbone. |
| `pillow` | Opens and converts uploaded images. |
| `gunicorn` | Production WSGI server used by Railway. |

### 4.9 Root `requirements.txt`

Railway analyzes the repository root. Because the real app is inside `Backend-Test`, the root `requirements.txt` delegates dependency installation to the nested file:

```text
-r Backend-Test/requirements.txt
```

Without this file, Railway may fail to detect the project as a Python app.

### 4.10 `start.sh`

This is the production start script used by Railway:

```bash
cd Backend-Test
gunicorn app:app --bind "0.0.0.0:${PORT:-5000}"
```

It moves into `Backend-Test` first so relative paths like `weights/internimage.pth` and `class_names.json` resolve correctly.

### 4.11 `railway.json`

This file tells Railway exactly how to start the app:

```json
{
  "deploy": {
    "startCommand": "bash start.sh",
    "restartPolicyType": "on_failure",
    "restartPolicyMaxRetries": 10
  }
}
```

It removes ambiguity from Railpack's build/start detection.

## 5. Environment Variables

The backend expects these variables:

| Variable | Required | Used By | Purpose |
|---|---:|---|---|
| `TREFLE_TOKEN` | Yes | `core/plant_info.py` | API token for Trefle plant search. |
| `TREFLE_API_URL` | Yes | `core/plant_info.py` | Trefle plant search endpoint. |
| `SUPABASE_URL` | Yes | `routes/explore.py` | Supabase project URL. |
| `SUPABASE_KEY` | Yes | `routes/explore.py` | Supabase anon/service key used by the Python client. |
| `PORT` | Railway provides this | `start.sh` | Port used by Gunicorn in production. |

Local `.env` example:

```text
TREFLE_TOKEN=your_trefle_token
TREFLE_API_URL=https://trefle.io/api/v1/plants/search
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

The `.env` file is ignored by Git and should not be committed.

## 6. API Reference

### 6.1 `GET /`

Health-check route.

Response:

```json
{
  "message": "Herbify backend is running"
}
```

Use this endpoint to confirm the app is reachable.

### 6.2 `POST /predict`

Uploads a plant image and returns prediction results.

Request type:

```text
multipart/form-data
```

Required field:

| Field | Type | Description |
|---|---|---|
| `image` | File | Image to classify. |

Example cURL:

```bash
curl -X POST http://127.0.0.1:5000/predict -F "image=@test.jpg"
```

Successful known-plant response:

```json
{
  "final": "Aloe Vera (Lidah Buaya)",
  "predictions": [
    {
      "class": "Aloe Vera (Lidah Buaya)",
      "confidence": 0.9542
    },
    {
      "class": "Sansevieria Trifasciata (Lidah Mertua)",
      "confidence": 0.0231
    },
    {
      "class": "Kalanchoe Pinnata (Cocor Bebek)",
      "confidence": 0.0107
    }
  ],
  "scientific_name": "Aloe Vera",
  "indonesian_name": "Lidah Buaya",
  "plant_details": {
    "scientific_name": "Aloe vera",
    "common_name": "Aloe",
    "image_url": "https://example.com/plant-image.jpg"
  }
}
```

Low-confidence response:

```json
{
  "predictions": [
    {
      "class": "Some Class",
      "confidence": 0.4123
    },
    {
      "class": "Another Class",
      "confidence": 0.2531
    },
    {
      "class": "Third Class",
      "confidence": 0.1107
    }
  ],
  "final": "Unknown"
}
```

Error responses:

| Status | Body | Meaning |
|---:|---|---|
| `400` | `{"error": "No image uploaded"}` | No `image` field was included. |
| `400` | `{"error": "Empty filename"}` | Uploaded file has no filename. |
| `500` | `{"error": "..."}` | Prediction, model, filesystem, or API error. |

### 6.3 `GET /api/remedies`

Returns all remedy records from Supabase, flattened for frontend use.

Example:

```bash
curl http://127.0.0.1:5000/api/remedies
```

Response shape:

```json
[
  {
    "herb_name": "Lidah Buaya",
    "instructions": "Apply gel to affected area.",
    "used_for": "Skin irritation",
    "dosage": "As needed",
    "side_effects": "Possible irritation",
    "contraindications": "Avoid if allergic",
    "warnings": "External use only",
    "interactions": null,
    "part_used": "Leaf gel"
  }
]
```

### 6.4 `GET /api/remedies/by/<herb_name>`

Returns remedies for a specific herb name.

Example:

```bash
curl "http://127.0.0.1:5000/api/remedies/by/Lidah%20Buaya"
```

Flow:

1. Search `herbs` where `herb_name` equals the provided path value.
2. If no matching herb exists, return `[]`.
3. Collect matching `herb_id` values.
4. Query `herbal_recipes` where `herb_id` is in that list.
5. Return flattened remedy objects.

Response:

```json
[
  {
    "herb_name": "Lidah Buaya",
    "instructions": "Apply gel to affected area.",
    "used_for": "Skin irritation",
    "dosage": "As needed",
    "side_effects": "Possible irritation",
    "contraindications": "Avoid if allergic",
    "warnings": "External use only",
    "interactions": null,
    "part_used": "Leaf gel"
  }
]
```

### 6.5 `GET /api/explore`

Returns paginated explore-page data.

Query parameters:

| Parameter | Default | Description |
|---|---:|---|
| `page` | `1` | Page number. |
| `per_page` | `6` | Number of records per page. |

Example:

```bash
curl "http://127.0.0.1:5000/api/explore?page=1&per_page=6"
```

Response shape:

```json
{
  "herbs": [
    {
      "id": 1,
      "recipe_id": 1,
      "herb_id": 2,
      "herb_name": "Lidah Buaya",
      "scientific_name": "Aloe vera",
      "common_name": "Aloe",
      "image_url": "https://example.com/image.jpg",
      "remedies": [
        {
          "recipe_id": 1,
          "used_for": "Skin irritation",
          "part_used": "Leaf gel",
          "dosage": "As needed",
          "instructions": "Apply gel to affected area.",
          "side_effects": "Possible irritation",
          "contraindications": "Avoid if allergic",
          "warnings": "External use only",
          "interactions": null
        }
      ]
    }
  ],
  "total_pages": 10,
  "total": 60,
  "page": 1
}
```

## 7. Complete Prediction Flow

```text
Frontend user selects or captures an image
-> Frontend sends POST /predict with multipart form field "image"
-> Flask validates the request
-> Flask saves the image temporarily in Backend-Test/uploads/
-> core.inference opens the image with PIL
-> torchvision transforms resize and normalize the image
-> PyTorch model predicts class logits
-> softmax converts logits to probabilities
-> top 3 predictions are selected
-> confidence threshold decides known plant vs Unknown
-> route extracts scientific/English name and Indonesian name
-> backend asks Trefle for plant metadata
-> backend returns JSON result to the frontend
-> temporary upload is deleted
-> frontend can call /api/remedies/by/<indonesian_name>
-> backend retrieves related remedy data from Supabase
```

## 8. Explore and Remedy Data Flow

```text
Frontend opens Explore page
-> Frontend calls GET /api/explore?page=1&per_page=6
-> Flask calculates Supabase range
-> Supabase returns herbal_recipes joined with herbs
-> backend asks Trefle for image/common-name metadata per item
-> backend formats each record as a frontend card
-> frontend renders plant/remedy cards
```

For a prediction result:

```text
Model predicts "Aloe Vera (Lidah Buaya)"
-> predict route adds "indonesian_name": "Lidah Buaya"
-> frontend calls /api/remedies/by/Lidah%20Buaya
-> backend finds herbs.herb_name == "Lidah Buaya"
-> backend uses herb_id to fetch herbal_recipes
-> frontend displays remedy information
```

## 9. Model Behavior

The model is a 113-class plant classifier. It produces probabilities for all known classes and returns the top three.

The backend uses a fixed confidence threshold:

```text
top confidence < 0.7 -> final = Unknown
top confidence >= 0.7 -> final = top predicted class
```

This threshold is a product decision. A higher threshold means fewer false positives but more `Unknown` results. A lower threshold means more confident-looking predictions but a higher risk of incorrect plant labels.

## 10. Local Development Setup

### 10.1 Create and Activate a Virtual Environment

From the repo root:

```bash
cd Backend-Test
python -m venv venv
```

Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 10.2 Install Dependencies

From inside `Backend-Test`:

```bash
pip install -r requirements.txt
```

Or from the repo root:

```bash
pip install -r requirements.txt
```

The root `requirements.txt` points to the nested requirements file.

### 10.3 Configure Environment Variables

Create `Backend-Test/.env`:

```text
TREFLE_TOKEN=your_trefle_token
TREFLE_API_URL=https://trefle.io/api/v1/plants/search
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_key
```

### 10.4 Run the App

From inside `Backend-Test`:

```bash
python app.py
```

The development server should run at:

```text
http://127.0.0.1:5000
```

### 10.5 Test Basic Routes

Health check:

```bash
curl http://127.0.0.1:5000/
```

Prediction:

```bash
curl -X POST http://127.0.0.1:5000/predict -F "image=@test.jpg"
```

Explore:

```bash
curl "http://127.0.0.1:5000/api/explore?page=1&per_page=6"
```

Remedy lookup:

```bash
curl "http://127.0.0.1:5000/api/remedies/by/Lidah%20Buaya"
```

## 11. Railway Deployment

Railway initially failed because Railpack analyzed the repository root and did not see a root-level Python app or root-level `requirements.txt`. The live Flask app is nested inside `Backend-Test`, so deployment needs explicit root files.

The project now includes:

| File | Purpose |
|---|---|
| `requirements.txt` | Makes Railway detect Python dependencies from the root. |
| `start.sh` | Starts Gunicorn from inside `Backend-Test`. |
| `railway.json` | Sets Railway's start command to `bash start.sh`. |

Railway start command:

```bash
bash start.sh
```

Gunicorn command:

```bash
gunicorn app:app --bind "0.0.0.0:${PORT:-5000}"
```

Railway environment variables required:

```text
TREFLE_TOKEN
TREFLE_API_URL
SUPABASE_URL
SUPABASE_KEY
```

Deployment note: the model weights are not committed to Git. On startup, the backend checks for `weights/internimage.pth` and downloads it through `gdown` if needed. This can make first startup slower and can fail if Google Drive blocks, rate-limits, or changes access to the file.

## 12. Git and Repository Configuration

### 12.1 `.gitignore`

Ignored files:

```text
.env
*.pyc
__pycache__/
uploads/
.venv/
venv/
.DS_Store
weights/
.pth
```

Important effects:

1. API keys are not committed.
2. Uploaded images are not committed.
3. Virtual environments are not committed.
4. Model weights are not committed.

### 12.2 `.gitattributes`

The repository contains Git LFS rules for `.pth` files:

```text
*.pth filter=lfs diff=lfs merge=lfs -text
Backend-Test/weights/internimage.pth filter=lfs diff=lfs merge=lfs -text
```

However, the current `.gitignore` excludes `.pth` and `weights/`, so model weights are not currently pushed. The app downloads weights at runtime instead.

## 13. Security and Privacy Notes

### 13.1 API Keys

Never commit `.env`. Supabase and Trefle credentials should be set through environment variables locally and through Railway environment variables in production.

### 13.2 Uploaded Images

Uploaded images are saved only temporarily. The prediction route deletes them after the response is generated. This helps reduce storage usage and avoids keeping user images unnecessarily.

### 13.3 Filename Safety

The upload route uses `secure_filename()` to sanitize user-provided filenames before writing them to disk.

### 13.4 Medical Disclaimer

The backend returns herbal remedy information from Supabase. This information should be treated as educational content, not medical advice. Any frontend using this backend should communicate that users should consult qualified professionals before using herbal remedies, especially if pregnant, taking medication, allergic, or managing medical conditions.

## 14. Known Limitations

| Limitation | Details |
|---|---|
| No authentication | Any client that can reach the backend can call the endpoints. |
| No rate limiting | Heavy traffic can overload model inference or external APIs. |
| Runtime model download | Cold starts depend on Google Drive availability. |
| Trefle dependency | Plant images/common names may be missing if Trefle fails. |
| Supabase dependency | Remedy endpoints require valid Supabase credentials and table structure. |
| No persistent prediction history | Uploaded images and prediction results are not stored by this backend. |
| Confidence threshold is fixed | The `0.7` threshold is hardcoded. |
| Class-label format dependency | Name extraction expects labels like `Name (Indonesian Name)`. |

## 15. Common Troubleshooting

### Railway says Railpack cannot determine how to build the app

Cause: Railway analyzed the root and did not find Python build markers.

Fix: keep these root files:

```text
requirements.txt
start.sh
railway.json
```

### App crashes because `class_names.json` is missing

Cause: app was started from the wrong working directory.

Fix: start from `Backend-Test`, or use `start.sh`.

### App crashes because `weights/internimage.pth` is missing

Cause: the weights file is ignored by Git and needs to be downloaded at startup.

Fix:

1. Confirm the Google Drive model URL is accessible.
2. Confirm `gdown` is installed.
3. Confirm Railway has enough disk space and startup time.

### Supabase routes return errors

Possible causes:

1. `SUPABASE_URL` missing.
2. `SUPABASE_KEY` missing.
3. Tables are named differently.
4. Columns are missing.
5. Row Level Security blocks the query.

### Trefle enrichment is missing

Possible causes:

1. `TREFLE_TOKEN` missing.
2. `TREFLE_API_URL` missing.
3. Trefle returned no matching plant.
4. Trefle request timed out or failed.

The prediction can still return model results even when Trefle enrichment is unavailable.

## 16. Recommended Future Improvements

| Improvement | Benefit |
|---|---|
| Move model weights to a more stable storage provider | More reliable deployment startup than Google Drive. |
| Add file type validation | Prevent non-image uploads from reaching PIL/model inference. |
| Add request size limits | Protect server memory and disk usage. |
| Add rate limiting | Protect model inference and Trefle/Supabase quotas. |
| Add structured logging | Easier debugging in Railway logs. |
| Add health endpoint that checks dependencies | Separate simple app health from model/Supabase/Trefle readiness. |
| Add tests | Catch route and response-shape regressions. |
| Cache Trefle results | Reduce repeated external API calls on explore pages. |
| Add async/background model download | Improve startup visibility and failure handling. |
| Consider renaming `Backend-Test` | A production directory name like `backend` would be clearer. |
| Consider renaming `InternImageClassifier` | The implementation uses ConvNeXt Tiny, so the current class name may confuse readers. |

## 17. Existing Supporting Guides

The repository also includes:

| File | Notes |
|---|---|
| `Backend-Test/FLASK_BACKEND_GUIDE.md` | Older/general Flask guide. Some parts describe prediction history endpoints that are not in the current live code. |
| `Backend-Test/supabase-flask-guide.md` | General Supabase/PostgreSQL guide. The current project uses the Supabase Python client, not raw `psycopg2`. |

Use this `PROJECT_DOCUMENTATION.md` file as the authoritative documentation for the current implementation.

## 18. Summary

Sprout Backend is a Flask API that supports an herbal plant identification app. It receives plant images, classifies them with a PyTorch model, enriches results with Trefle plant metadata, and serves Supabase-backed remedy data for frontend pages.

The core application lives in `Backend-Test`. The root-level files exist mostly to support deployment and repository documentation. The most important runtime dependencies are the model weights, class-name mapping, Supabase credentials, and Trefle credentials.

The current backend is functional and deployable, but it should be treated as an application backend with external dependencies. Production hardening should focus on reliable model storage, request validation, rate limiting, logging, and tests.
