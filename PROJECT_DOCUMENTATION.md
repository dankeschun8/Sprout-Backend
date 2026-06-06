# Sprout Backend Project Documentation

## 1. Project Overview

Sprout Backend is a Flask-based REST API used by the Sprout frontend to identify herbal plants from images and retrieve related plant and remedy information. The backend receives an uploaded image, preprocesses it, runs a trained image classification model, enriches the prediction with plant details from the Trefle API, and exposes Supabase-powered endpoints for herbal recipe data.

The main backend code is located inside the `Backend-Test` directory. The application is divided into a main Flask entry point, route modules, and core machine learning modules.

## 2. Project Structure

```text
Sprout-Backend/
|-- .gitattributes
|-- .gitignore
|-- PROJECT_DOCUMENTATION.md
|-- Backend-Test/
    |-- app.py
    |-- class_names.json
    |-- requirements.txt
    |-- FLASK_BACKEND_GUIDE.md
    |-- supabase-flask-guide.md
    |-- core/
    |   |-- __init__.py
    |   |-- inference.py
    |   |-- model.py
    |-- routes/
        |-- __init__.py
        |-- predict.py
        |-- explore.py
```

## 3. Main Application File

### `Backend-Test/app.py`

This file is the main entry point of the Flask backend. It creates the Flask application, enables CORS, checks whether the model weights exist, downloads the model if needed, registers route blueprints, and starts the server.

The file begins by loading environment variables with `load_dotenv()`. These environment variables are used by other modules for API keys and service URLs, such as Trefle and Supabase credentials.

```python
load_dotenv()
```

The application defines the model weight path:

```python
MODEL_PATH = "weights/internimage.pth"
MODEL_URL = "https://drive.google.com/uc?id=1zcQ6sa-mVxv6y5OWqTtHT5Mn0dyiGrEp"
```

The function `model_file_is_invalid(path)` checks whether the model file is missing, too small, or only a Git LFS pointer file. This is important because large `.pth` files are often stored using Git LFS. If the actual model file is not present, the application downloads it from Google Drive using `gdown`.

```python
if model_file_is_invalid(MODEL_PATH):
    os.makedirs("weights", exist_ok=True)
    gdown.download(MODEL_URL, MODEL_PATH, quiet=False)
```

After the model file check, the route blueprints are imported and registered:

```python
from routes.predict import predict_bp
from routes.explore import explore_bp

app.register_blueprint(predict_bp)
app.register_blueprint(explore_bp)
```

The home route is a simple health-check endpoint:

```python
@app.route("/")
def home():
    return {"message": "Herbify backend is running"}
```

When run directly, Flask starts in debug mode:

```python
if __name__ == "__main__":
    app.run(debug=True)
```

## 4. Prediction Route

### `Backend-Test/routes/predict.py`

This file defines the `/predict` endpoint. It handles image upload, file validation, temporary storage, model prediction, plant name extraction, Trefle API lookup, and final JSON response.

The route is organized as a Flask blueprint:

```python
predict_bp = Blueprint('predict', __name__)
```

The uploaded image is temporarily saved inside the `uploads` folder:

```python
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
```

### `extract_plant_name(class_label)`

This helper function extracts the scientific or main plant name from a class label. The class labels are stored in the format:

```text
Aloe Vera (Lidah Buaya)
```

For this example, `extract_plant_name()` returns:

```text
Aloe Vera
```

It does this by reading the text before the opening parenthesis.

### `get_indonesian_name(class_label)`

This helper function extracts the Indonesian plant name from the text inside parentheses. For example:

```text
Aloe Vera (Lidah Buaya)
```

returns:

```text
Lidah Buaya
```

The Indonesian name is important because the frontend uses it to request matching remedy data from the Supabase-backed route.

### `get_plant_info(plant_name)`

This function connects to the Trefle API. It receives a plant name, formats it for search by replacing spaces with hyphens, and sends a GET request using the configured Trefle token and API URL.

```python
params = {
    "token": [os.getenv('TREFLE_TOKEN')],
    "q": query_name
}
response = requests.get(os.getenv('TREFLE_API_URL'), params=params, timeout=10)
```

If Trefle returns plant data, the backend keeps the scientific name, common name, and image URL:

```python
return {
    "scientific_name": plant.get("scientific_name"),
    "common_name": plant.get("common_name"),
    "image_url": plant.get("image_url"),
}
```

If the API request fails or no plant is found, the function returns `None`.

### `/predict`

The `/predict` endpoint accepts only POST requests:

```python
@predict_bp.route("/predict", methods=["POST"])
def predict_route():
```

The frontend sends the image using the form key `image`. The route first checks whether the image exists:

```python
if "image" not in request.files:
    return jsonify({"error": "No image uploaded"}), 400
```

It also checks whether the filename is empty:

```python
if file.filename == "":
    return jsonify({"error": "Empty filename"}), 400
```

The filename is sanitized with `secure_filename()` to prevent unsafe file paths:

```python
filename = secure_filename(file.filename)
```

The image is then saved temporarily:

```python
image_path = os.path.join(UPLOAD_FOLDER, filename)
file.save(image_path)
```

After saving the image, the backend calls the `predict()` function from `core/inference.py`:

```python
result = predict(image_path)
```

If the model returns a known class, the route extracts the scientific name and Indonesian name, adds them to the response, and fetches plant details from Trefle.

Finally, the endpoint returns the result as JSON. The uploaded file is deleted in the `finally` block to avoid storing unnecessary user images on the server:

```python
finally:
    if os.path.exists(image_path):
        os.remove(image_path)
```

## 5. Explore and Remedy Routes

### `Backend-Test/routes/explore.py`

This file defines routes that retrieve herbal remedy data from Supabase and plant image information from Trefle.

The file creates a Supabase client using environment variables:

```python
supabase = supabase_client.create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
```

It also contains a `get_plant_info(plant_name)` function similar to the one in `predict.py`. This function is used by the explore endpoint to enrich Supabase recipe data with plant images from Trefle.

### `/api/remedies`

This GET endpoint returns all herbal recipe records from the `herbal_recipes` table and joins herb names from the related `herbs` table.

```python
@explore_bp.route('/api/remedies', methods=['GET'])
def get_remedies():
```

The Supabase query selects fields such as:

- `instructions`
- `used_for`
- `dosage`
- `side_effects`
- `contraindications`
- `warnings`
- `interactions`
- `part_used`
- `herbs(herb_name)`

The response is flattened before being returned to the frontend. This means nested Supabase data is converted into a simpler JSON structure.

### `/api/remedies/by/<herb_name>`

This GET endpoint returns remedy data for a specific herb name:

```python
@explore_bp.route('/api/remedies/by/<herb_name>', methods=['GET'])
def get_remedies_by_herb(herb_name):
```

The function first searches the `herbs` table for matching rows:

```python
herb_res = supabase.table('herbs') \
    .select('herb_id, herb_name') \
    .eq('herb_name', herb_name) \
    .execute()
```

If no herb is found, it returns an empty list. If a herb is found, it collects the `herb_id` values and uses them to query the `herbal_recipes` table:

```python
res = supabase.table('herbal_recipes').select(...).in_('herb_id', herb_ids).execute()
```

This route is used after prediction. The frontend receives the predicted Indonesian herb name, then calls this endpoint to retrieve related remedy data.

### `/api/explore`

This GET endpoint supports paginated browsing of herbal plants and remedies:

```python
@explore_bp.route('/api/explore', methods=['GET'])
def get_explore():
```

It accepts optional query parameters:

- `page`
- `per_page`

The route calculates the Supabase range from the requested page:

```python
start = (page - 1) * per_page
end = page * per_page - 1
```

It then queries `herbal_recipes`, joins related herb information, retrieves total count, and returns:

- `herbs`
- `total_pages`
- `total`
- `page`

For each herb, the route also attempts to fetch plant image data from the Trefle API.

## 6. Machine Learning Inference

### `Backend-Test/core/inference.py`

This file loads the trained model and defines the image prediction process.

The main configuration values are:

```python
WEIGHTS_PATH = "weights/internimage.pth"
CLASS_NAMES_PATH = "class_names.json"
IMAGE_SIZE = 224
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
```

`WEIGHTS_PATH` points to the trained PyTorch model checkpoint. `CLASS_NAMES_PATH` points to the list of class labels. `IMAGE_SIZE` defines the size used for inference preprocessing. `DEVICE` automatically uses CUDA if a compatible GPU is available, otherwise it uses CPU.

Gradient calculation is disabled because inference does not need training updates:

```python
torch.set_grad_enabled(False)
```

The file loads the class names from `class_names.json`:

```python
with open(CLASS_NAMES_PATH, "r") as f:
    class_names = json.load(f)
```

The number of classes is calculated from the class list:

```python
num_classes = len(class_names)
```

The model is created using `InternImageClassifier`:

```python
model = InternImageClassifier(
    num_classes=num_classes,
    pretrained=False
)
```

The checkpoint is loaded from disk:

```python
checkpoint = torch.load(
    WEIGHTS_PATH,
    map_location=DEVICE,
    weights_only=True
)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()
```

The model is placed in evaluation mode with `model.eval()`. This disables training behavior such as dropout randomness and makes predictions more stable.

### Image Preprocessing

The preprocessing pipeline uses `torchvision.transforms`:

```python
transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])
```

The uploaded image is:

1. Resized to `224 x 224`.
2. Converted into a PyTorch tensor.
3. Normalized using ImageNet mean and standard deviation.

### `predict(image_path)`

The `predict()` function receives the path of the uploaded image.

```python
def predict(image_path: str):
```

It opens the image with PIL and converts it to RGB:

```python
image = Image.open(image_path).convert("RGB")
```

The image is transformed, given a batch dimension, and moved to the selected device:

```python
tensor = transform(image).unsqueeze(0).to(DEVICE)
```

The model produces output logits:

```python
outputs = model(tensor)
```

The logits are converted into probabilities using softmax:

```python
probs = torch.softmax(outputs, dim=1)
```

The top three predictions are selected:

```python
topk_conf, topk_idx = torch.topk(probs, k=3)
```

The function returns each predicted class and its confidence score. If the highest confidence score is below `0.7`, the final result is set to `Unknown`:

```python
if results[0]["confidence"] < 0.7:
    return {
        "predictions": results,
        "final": "Unknown"
    }
```

Otherwise, the final result is the class with the highest confidence.

## 7. Model Architecture

### `Backend-Test/core/model.py`

This file defines the model class used for plant classification.

```python
class InternImageClassifier(nn.Module):
```

Although the class is named `InternImageClassifier`, the current implementation uses a `convnext_tiny` backbone from the `timm` library:

```python
self.backbone = timm.create_model(
    'convnext_tiny',
    pretrained=pretrained,
    num_classes=0,
    drop_path_rate=drop_path_rate,
)
```

The `num_classes=0` setting removes the default classification head, allowing the project to define its own custom classification layers.

The model stores the number of output features from the backbone:

```python
self.feature_dim = self.backbone.num_features
```

### Global Context Block

The model includes a global context module:

```python
self.global_context = nn.Sequential(
    nn.AdaptiveAvgPool2d(1),
    nn.Conv2d(self.feature_dim, self.feature_dim // 4, 1),
    nn.GELU(),
    nn.Conv2d(self.feature_dim // 4, self.feature_dim, 1),
    nn.Sigmoid()
)
```

This block learns channel-wise attention weights. It helps the model emphasize useful feature channels and reduce less useful ones.

### Classification Head

The classification head contains:

- `LayerNorm`
- `Dropout`
- `Linear`

```python
self.head = nn.Sequential(
    nn.LayerNorm(self.feature_dim),
    nn.Dropout(max(drop_rate, 0.1)),
    nn.Linear(self.feature_dim, num_classes)
)
```

The final linear layer outputs one score for each plant class.

### Forward Pass

The `forward()` method defines how input images move through the model:

```python
features = self.backbone.forward_features(x)
context = self.global_context(features)
features = features * context
x = features.mean(dim=[-2, -1])
return self.head(x)
```

The image first passes through the ConvNeXt backbone. The extracted feature map is multiplied by the global context weights, pooled into a vector, and passed through the classification head.

## 8. Class Names

### `Backend-Test/class_names.json`

This JSON file contains the plant class labels used by the model. The project currently has 113 classes. Each label follows this general format:

```text
Scientific or English Name (Indonesian Name)
```

Example:

```text
Aloe Vera (Lidah Buaya)
```

The order of class names is important because the model output index is mapped directly to this list. For example, if the model predicts index `2`, the backend uses the class at position `2` in `class_names.json`.

## 9. Package Files

### `Backend-Test/requirements.txt`

This file lists the Python dependencies required to run the backend:

```text
flask
flask-cors
python-dotenv
requests
supabase
gdown
torch
torchvision
timm
pillow
gunicorn
```

Important packages include:

- `flask`: Creates the REST API.
- `flask-cors`: Allows the frontend to call the backend from a different origin.
- `python-dotenv`: Loads environment variables from `.env`.
- `requests`: Calls the Trefle API.
- `supabase`: Connects to Supabase.
- `gdown`: Downloads model weights from Google Drive.
- `torch`: Runs the PyTorch model.
- `torchvision`: Provides image transforms.
- `timm`: Provides the ConvNeXt model backbone.
- `pillow`: Opens and converts uploaded images.
- `gunicorn`: Runs the app in production environments.

## 10. Empty Package Initializers

### `Backend-Test/core/__init__.py`

This file is empty. Its purpose is to mark the `core` directory as a Python package so that modules such as `core.inference` and `core.model` can be imported.

### `Backend-Test/routes/__init__.py`

This file is empty. Its purpose is to mark the `routes` directory as a Python package so that route modules can be imported into the Flask app.

## 11. Repository Configuration Files

### `.gitignore`

The `.gitignore` file prevents sensitive, generated, or large local files from being committed. It ignores:

- `.env`
- Python cache files
- `uploads/`
- virtual environments
- system files
- model weight files

This is important because `.env` may contain API keys, and model weight files are usually too large for normal Git storage.

### `.gitattributes`

This file configures Git LFS behavior for `.pth` files:

```text
*.pth filter=lfs diff=lfs merge=lfs -text
Backend-Test/weights/internimage.pth filter=lfs diff=lfs merge=lfs -text
```

It tells Git to treat PyTorch model files as large binary files managed by Git LFS.

## 12. Existing Guide Files

### `Backend-Test/FLASK_BACKEND_GUIDE.md`

This file is a general guide explaining Flask backend concepts, image upload, prediction endpoints, Trefle usage, and possible future backend features. Some examples in the guide describe an expanded or older version of the backend, so the current source code should be treated as the authoritative implementation.

### `Backend-Test/supabase-flask-guide.md`

This file is a guide for connecting Flask to Supabase. It includes examples using PostgreSQL drivers and common database query patterns. The current project code uses the `supabase` Python client rather than raw `psycopg2` queries.

## 13. Environment Variables

The backend expects the following environment variables to be available:

```text
TREFLE_TOKEN
TREFLE_API_URL
SUPABASE_URL
SUPABASE_KEY
```

These values should be placed in a local `.env` file inside the backend runtime directory. The `.env` file is ignored by Git for security.

## 14. API Endpoints Summary

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Health check route showing that the backend is running. |
| POST | `/predict` | Receives an image, runs model prediction, and returns plant details. |
| GET | `/api/remedies` | Returns all herbal recipe data from Supabase. |
| GET | `/api/remedies/by/<herb_name>` | Returns recipe data for a specific herb name. |
| GET | `/api/explore?page=1&per_page=6` | Returns paginated herb and remedy data for the Explore page. |

## 15. Complete Prediction Flow

The prediction flow connects the frontend, Flask backend, model, Trefle API, and Supabase data.

```text
User uploads or captures an image in the frontend
-> Frontend sends the image to Flask /predict as FormData
-> Flask validates the uploaded file
-> Flask temporarily saves the file in uploads/
-> Backend preprocesses the image using PIL and torchvision transforms
-> PyTorch model predicts the top plant classes
-> Backend checks confidence threshold
-> Backend extracts scientific name and Indonesian name
-> Backend fetches plant details and image URL from Trefle
-> Backend returns prediction JSON to frontend
-> Frontend uses Indonesian name to call /api/remedies/by/<herb_name>
-> Flask retrieves recipe data from Supabase
-> Frontend displays plant name, confidence, image, and herbal uses
```

## 16. Response Data Example

A successful `/predict` response has this general structure:

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

If the confidence is below the threshold, the response uses:

```json
{
  "final": "Unknown",
  "predictions": []
}
```

The actual low-confidence response still includes the top three predictions, but the `final` field is set to `Unknown`.

## 17. Important Implementation Notes

The current inference image size is set to `224 x 224` in `core/inference.py`. If the model was trained using a different image size, such as `128 x 128`, the inference size should usually match the training size to keep preprocessing consistent.

The class is named `InternImageClassifier`, but the current implementation uses the `convnext_tiny` backbone from `timm`. If the thesis or report describes the model architecture, it should mention the actual implementation or rename the class to avoid confusion.

The `/predict` route only retrieves Trefle plant details. Supabase remedy data is retrieved through separate endpoints, especially `/api/remedies/by/<herb_name>`, which the frontend calls after receiving the prediction result.

Uploaded images are deleted after prediction. This improves privacy and prevents storage growth, but it also means the backend does not keep user-uploaded images for history or auditing.

## 18. Running the Backend

Install dependencies:

```bash
pip install -r requirements.txt
```

Create a `.env` file with the required credentials:

```text
TREFLE_TOKEN=your_trefle_token
TREFLE_API_URL=https://trefle.io/api/v1/plants/search
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

Run the backend from the `Backend-Test` directory:

```bash
python app.py
```

The backend should start on:

```text
http://127.0.0.1:5000
```

## 19. Testing the API

Test the home route:

```bash
curl http://127.0.0.1:5000/
```

Test prediction with an image:

```bash
curl -X POST http://127.0.0.1:5000/predict -F "image=@test.jpg"
```

Test all remedies:

```bash
curl http://127.0.0.1:5000/api/remedies
```

Test remedies by herb name:

```bash
curl http://127.0.0.1:5000/api/remedies/by/Lidah%20Buaya
```

Test explore pagination:

```bash
curl "http://127.0.0.1:5000/api/explore?page=1&per_page=6"
```

## 20. Summary

This backend acts as the main processing layer for the Sprout herbal plant identification system. It receives images from the frontend, uses a trained PyTorch model for classification, enriches the result with Trefle plant data, and provides Supabase recipe endpoints for herbal use information. The code is separated into clear modules: `app.py` for application setup, `routes/predict.py` for image prediction, `routes/explore.py` for remedy and explore data, `core/inference.py` for model loading and prediction, and `core/model.py` for the neural network architecture.
