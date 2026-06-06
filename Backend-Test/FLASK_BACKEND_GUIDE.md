# 🌿 Flask Plant Prediction Backend - Complete Guide

A comprehensive guide to understanding and using your Flask backend for plant image classification.

---

## 📚 Table of Contents

1. [Project Overview](#project-overview)
2. [Project Structure](#project-structure)
3. [Installation & Setup](#installation--setup)
4. [Understanding the Code](#understanding-the-code)
5. [API Endpoints Explained](#api-endpoints-explained)
6. [How to Use Each Feature](#how-to-use-each-feature)
7. [Frontend Integration](#frontend-integration)
8. [Testing Your API](#testing-your-api)
9. [Troubleshooting](#troubleshooting)
10. [Advanced Features](#advanced-features)

---

## 🎯 Project Overview

### What Does This Backend Do?

Your Flask backend is a **REST API** that:

1. **Accepts plant images** from users
2. **Predicts the plant species** using a machine learning model
3. **Fetches additional information** about the plant from Trefle API
4. **Stores prediction history** in a JSON database
5. **Provides query endpoints** to search and filter past predictions

Think of it like this:
- **Frontend (Website/App)** = The face customers see
- **Backend (This Flask app)** = The brain that does the work
- **Model (inference.py)** = The expert that identifies plants
- **Database (JSON file)** = The memory that remembers past predictions

---

## 📁 Project Structure

```
your-project/
├── app_enhanced.py          # Main Flask application (THE BRAIN)
├── inference.py             # ML model prediction logic
├── requirements.txt         # Python dependencies
├── uploads/                 # Temporary folder for uploaded images
├── prediction_history/      # Stores all prediction data
│   └── predictions.json     # JSON "database"
└── models/                  # Your trained ML model files
    └── plant_model.pth
```

### What Each File Does

- **app_enhanced.py**: Your main server that handles HTTP requests
- **inference.py**: Contains the `predict()` function that uses your trained model
- **predictions.json**: Stores every prediction made (like a database)
- **uploads/**: Temporarily holds uploaded images (deleted after processing)

---

## 🚀 Installation & Setup

### Step 1: Install Python Dependencies

```bash
pip install flask flask-cors requests pillow torch torchvision
```

Or use a requirements.txt file:

```bash
# Create requirements.txt
cat > requirements.txt << EOF
flask==3.0.0
flask-cors==4.0.0
requests==2.31.0
Pillow==10.1.0
torch==2.1.0
torchvision==0.16.0
EOF

# Install
pip install -r requirements.txt
```

### Step 2: Configure API Keys

Open `app_enhanced.py` and replace the placeholders:

```python
# Find these lines (around line 58-62)
params = {
    "token": ['TREFLE_TOKEN'],  # ← Replace with your actual token
    "q": query_name
}
response = requests.get('TREFLE_API_URL', params=params, timeout=10)
                        # ↑ Replace with actual URL
```

**How to get Trefle API credentials:**
1. Go to https://trefle.io/
2. Sign up for a free account
3. Get your API token
4. Replace in code:
   ```python
   "token": "your-actual-token-here"
   response = requests.get('https://trefle.io/api/v1/plants/search', ...)
   ```

### Step 3: Prepare Your Model

Make sure `inference.py` has a `predict()` function:

```python
# inference.py should look like this:
def predict(image_path):
    """
    Takes an image path and returns prediction result
    """
    # Your model prediction code here
    
    return {
        "final": "Aloe Vera (Lidah Buaya)",  # Full class name
        "confidence": 0.95,                   # Confidence score
        # ... other prediction data
    }
```

### Step 4: Run the Server

```bash
python app_enhanced.py
```

You should see:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

🎉 **Your server is now running!**

---

## 🧠 Understanding the Code

### The Big Picture: How a Request Works

```
User uploads image
       ↓
Frontend sends POST to /predict
       ↓
Flask receives the image
       ↓
Saves image to uploads/ folder
       ↓
Calls predict(image_path) from inference.py
       ↓
Model returns prediction
       ↓
Extracts scientific name & Indonesian name
       ↓
Calls Trefle API for more plant info
       ↓
Saves everything to predictions.json
       ↓
Returns JSON response to frontend
       ↓
User sees the result
```

### Breaking Down the Code

#### 1. **Import Section** (Lines 1-11)

```python
from flask import Flask, request, jsonify  # Flask basics
from flask_cors import CORS                # Allows frontend to call backend
import os                                  # File operations
from werkzeug.utils import secure_filename # Security for file uploads
import requests                            # Call external APIs
import re                                  # Parse text patterns
import json                                # Work with JSON data
from datetime import datetime              # Timestamps
```

**What is CORS?**
- CORS = Cross-Origin Resource Sharing
- Without it, browsers block requests from your frontend to backend
- `CORS(app)` allows your React/Vue/Angular app to communicate with Flask

#### 2. **App Configuration** (Lines 13-27)

```python
app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"              # Where images temporarily live
HISTORY_FOLDER = "prediction_history"  # Where data is stored
HISTORY_FILE = os.path.join(HISTORY_FOLDER, "predictions.json")

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(HISTORY_FOLDER, exist_ok=True)

# Create empty predictions.json if it doesn't exist
if not os.path.exists(HISTORY_FILE):
    with open(HISTORY_FILE, 'w') as f:
        json.dump([], f)  # Start with empty array
```

#### 3. **Utility Functions** (Lines 30-100)

These are helper functions that do specific tasks:

**a) Extract Scientific Name:**
```python
def extract_plant_name(class_label):
    """
    Input:  "Aloe Vera (Lidah Buaya)"
    Output: "Aloe Vera"
    
    How it works:
    - Looks for text before the opening parenthesis "("
    - Strips whitespace
    """
    match = re.match(r'^(.+?)\s*\(', class_label)
    if match:
        return match.group(1).strip()
    return class_label.strip()
```

**b) Extract Indonesian Name:**
```python
def get_indonesian_name(class_label):
    """
    Input:  "Aloe Vera (Lidah Buaya)"
    Output: "Lidah Buaya"
    
    How it works:
    - Looks for text inside parentheses "()"
    """
    match = re.search(r'\((.+?)\)', class_label)
    if match:
        return match.group(1).strip()
    return None
```

**c) Get Plant Info from Trefle API:**
```python
def get_plant_info(plant_name):
    """
    Calls Trefle API to get more info about the plant
    
    Input:  "Aloe Vera"
    Output: {
        "scientific_name": "Aloe vera",
        "common_name": "Aloe",
        "family": "Asphodelaceae",
        "genus": "Aloe",
        "image_url": "https://...",
        ...
    }
    """
    # Replace spaces with hyphens for URL
    query_name = plant_name.replace(' ', '-')
    
    # Call API
    response = requests.get('TREFLE_API_URL', params={...})
    
    # Parse response
    if response.status_code == 200:
        data = response.json()
        if data.get("data"):
            return plant_data
    
    return None  # If API fails or no data
```

#### 4. **Database Functions** (Lines 103-180)

These functions work with the JSON "database":

**a) Save Prediction:**
```python
def save_prediction_to_history(prediction_data):
    """
    Saves a prediction to predictions.json
    
    Like adding a new row to a database table
    """
    # 1. Read existing predictions
    with open(HISTORY_FILE, 'r') as f:
        history = json.load(f)
    
    # 2. Generate new ID
    prediction_id = str(len(history) + 1)
    
    # 3. Add metadata
    prediction_data['id'] = prediction_id
    prediction_data['timestamp'] = datetime.now().isoformat()
    
    # 4. Add to list
    history.append(prediction_data)
    
    # 5. Save back to file
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)
    
    return prediction_id
```

**b) Load All Predictions:**
```python
def load_all_predictions():
    """
    Reads all predictions from JSON file
    
    Returns: List of prediction dictionaries
    """
    with open(HISTORY_FILE, 'r') as f:
        return json.load(f)
```

#### 5. **Query Functions (JPA-Style)** (Lines 183-290)

These are like database queries:

**a) Find All with Pagination:**
```python
def find_all(limit=None, offset=0):
    """
    Like SQL: SELECT * FROM predictions LIMIT 10 OFFSET 0
    
    Example:
        find_all(limit=10, offset=0)  # First 10 results
        find_all(limit=10, offset=10) # Next 10 results
    """
    predictions = load_all_predictions()
    
    if limit:
        return predictions[offset:offset + limit]
    return predictions[offset:]
```

**b) Find by ID:**
```python
def find_by_id(prediction_id):
    """
    Like SQL: SELECT * FROM predictions WHERE id = '123'
    
    Example:
        find_by_id("123")  # Get prediction with ID 123
    """
    predictions = load_all_predictions()
    for pred in predictions:
        if pred.get('id') == prediction_id:
            return pred
    return None
```

**c) Find by Scientific Name:**
```python
def find_by_scientific_name(scientific_name):
    """
    Like SQL: SELECT * FROM predictions 
              WHERE LOWER(scientific_name) = LOWER('aloe vera')
    
    Example:
        find_by_scientific_name("Aloe Vera")
        # Returns all predictions for Aloe Vera
    """
    predictions = load_all_predictions()
    return [p for p in predictions 
            if p.get('scientific_name', '').lower() == scientific_name.lower()]
```

**d) Search with Partial Match:**
```python
def find_by_scientific_name_containing(keyword):
    """
    Like SQL: SELECT * FROM predictions 
              WHERE LOWER(scientific_name) LIKE '%aloe%'
    
    Example:
        find_by_scientific_name_containing("aloe")
        # Returns: Aloe Vera, Aloe arborescens, etc.
    """
    predictions = load_all_predictions()
    keyword_lower = keyword.lower()
    return [p for p in predictions 
            if keyword_lower in p.get('scientific_name', '').lower()]
```

**e) Find by Confidence:**
```python
def find_by_confidence_greater_than(threshold):
    """
    Like SQL: SELECT * FROM predictions WHERE confidence > 0.8
    
    Example:
        find_by_confidence_greater_than(0.9)
        # Returns only high-confidence predictions
    """
    predictions = load_all_predictions()
    return [p for p in predictions if p.get('confidence', 0) > threshold]
```

**f) Find by Date Range:**
```python
def find_by_date_range(start_date, end_date):
    """
    Like SQL: SELECT * FROM predictions 
              WHERE timestamp BETWEEN '2024-01-01' AND '2024-12-31'
    
    Example:
        find_by_date_range("2024-01-01", "2024-01-31")
        # Returns predictions from January 2024
    """
    predictions = load_all_predictions()
    return [p for p in predictions 
            if start_date <= p.get('timestamp', '') <= end_date]
```

---

## 🔌 API Endpoints Explained

### Endpoint 1: POST /predict

**Purpose:** Upload an image and get plant prediction

**What Happens Step-by-Step:**

```python
@app.route("/predict", methods=["POST"])
def predict_route():
    # STEP 1: Check if image was uploaded
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    # STEP 2: Get the file
    file = request.files["image"]
    
    # STEP 3: Check if filename is empty
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400
    
    # STEP 4: Secure the filename (remove dangerous characters)
    filename = secure_filename(file.filename)
    # "../../etc/passwd.jpg" becomes "etc_passwd.jpg"
    
    # STEP 5: Save file temporarily
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(image_path)
    # Now image is in: uploads/plant.jpg
    
    try:
        # STEP 6: Call ML model
        result = predict(image_path)
        # result = {
        #     "final": "Aloe Vera (Lidah Buaya)",
        #     "confidence": 0.95
        # }
        
        # STEP 7: Extract names
        class_label = result.get("final")
        scientific_name = extract_plant_name(class_label)
        # "Aloe Vera"
        
        indonesian_name = get_indonesian_name(class_label)
        # "Lidah Buaya"
        
        # STEP 8: Add names to result
        result["scientific_name"] = scientific_name
        if indonesian_name:
            result["indonesian_name"] = indonesian_name
        
        # STEP 9: Get more info from Trefle API
        plant_info = get_plant_info(scientific_name)
        if plant_info:
            result["plant_details"] = plant_info
        
        # STEP 10: Save to history
        result["filename"] = filename
        prediction_id = save_prediction_to_history(result)
        result["id"] = prediction_id
        
        # STEP 11: Return response
        return jsonify(result)
        
    except Exception as e:
        # If anything goes wrong
        return jsonify({"error": str(e)}), 500
        
    finally:
        # STEP 12: Clean up - delete uploaded image
        if os.path.exists(image_path):
            os.remove(image_path)
```

**How to Use:**

```bash
# Using cURL
curl -X POST http://localhost:5000/predict \
  -F "image=@/path/to/plant.jpg"

# Using Python
import requests

with open('plant.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post('http://localhost:5000/predict', files=files)
    print(response.json())

# Using JavaScript (Frontend)
const formData = new FormData();
formData.append('image', fileInput.files[0]);

fetch('http://localhost:5000/predict', {
  method: 'POST',
  body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

**Response Example:**

```json
{
  "id": "42",
  "final": "Aloe Vera (Lidah Buaya)",
  "scientific_name": "Aloe Vera",
  "indonesian_name": "Lidah Buaya",
  "confidence": 0.95,
  "timestamp": "2024-04-20T15:30:00.123456",
  "filename": "plant.jpg",
  "plant_details": {
    "scientific_name": "Aloe vera",
    "common_name": "Aloe",
    "family": "Asphodelaceae",
    "genus": "Aloe",
    "image_url": "https://bs.plantnet.org/image/...",
    "slug": "aloe-vera"
  }
}
```

---

### Endpoint 2: GET /api/predictions

**Purpose:** Get all predictions with pagination

**How it Works:**

```python
@app.route("/api/predictions", methods=["GET"])
def get_all_predictions():
    # Get query parameters
    limit = request.args.get('limit', type=int)   # ?limit=10
    offset = request.args.get('offset', default=0, type=int)  # &offset=0
    
    # Query the data
    predictions = find_all(limit=limit, offset=offset)
    
    # Return with metadata
    return jsonify({
        "total": count_all(),      # Total number of predictions
        "limit": limit,             # How many returned
        "offset": offset,           # Starting position
        "data": predictions         # The actual predictions
    })
```

**Use Cases:**

```bash
# Get ALL predictions
curl http://localhost:5000/api/predictions

# Get first 10 predictions (Page 1)
curl "http://localhost:5000/api/predictions?limit=10&offset=0"

# Get next 10 predictions (Page 2)
curl "http://localhost:5000/api/predictions?limit=10&offset=10"

# Get predictions 20-30 (Page 3)
curl "http://localhost:5000/api/predictions?limit=10&offset=20"
```

**Response:**

```json
{
  "total": 150,
  "limit": 10,
  "offset": 0,
  "data": [
    {
      "id": "1",
      "scientific_name": "Aloe Vera",
      "confidence": 0.95,
      ...
    },
    {
      "id": "2",
      "scientific_name": "Rosa chinensis",
      "confidence": 0.88,
      ...
    },
    ... 8 more ...
  ]
}
```

---

### Endpoint 3: GET /api/predictions/{id}

**Purpose:** Get a specific prediction by ID

```python
@app.route("/api/predictions/<prediction_id>", methods=["GET"])
def get_prediction_by_id(prediction_id):
    # Find the prediction
    prediction = find_by_id(prediction_id)
    
    # Return it or 404
    if prediction:
        return jsonify(prediction)
    else:
        return jsonify({"error": "Prediction not found"}), 404
```

**Usage:**

```bash
# Get prediction with ID 42
curl http://localhost:5000/api/predictions/42
```

---

### Endpoint 4: GET /api/predictions/search/scientific-name/{name}

**Purpose:** Find all predictions for a specific plant species (exact match)

```python
@app.route("/api/predictions/search/scientific-name/<scientific_name>", methods=["GET"])
def get_by_scientific_name(scientific_name):
    predictions = find_by_scientific_name(scientific_name)
    
    return jsonify({
        "count": len(predictions),
        "data": predictions
    })
```

**Usage:**

```bash
# Find all Aloe Vera predictions
curl http://localhost:5000/api/predictions/search/scientific-name/Aloe%20Vera

# Note: %20 is URL encoding for space
# In browser: http://localhost:5000/api/predictions/search/scientific-name/Aloe Vera
```

---

### Endpoint 5: GET /api/predictions/search/scientific-name-contains

**Purpose:** Search for plants with partial name match

```python
@app.route("/api/predictions/search/scientific-name-contains", methods=["GET"])
def search_scientific_name_containing():
    # Get keyword from query parameter
    keyword = request.args.get('keyword', '')
    
    if not keyword:
        return jsonify({"error": "Keyword parameter required"}), 400
    
    predictions = find_by_scientific_name_containing(keyword)
    
    return jsonify({
        "keyword": keyword,
        "count": len(predictions),
        "data": predictions
    })
```

**Usage:**

```bash
# Find all plants with "aloe" in the name
curl "http://localhost:5000/api/predictions/search/scientific-name-contains?keyword=aloe"

# Results: Aloe Vera, Aloe arborescens, Aloe brevifolia, etc.

# Find all roses
curl "http://localhost:5000/api/predictions/search/scientific-name-contains?keyword=rosa"

# Results: Rosa chinensis, Rosa multiflora, Rosa rugosa, etc.
```

---

### Endpoint 6: GET /api/predictions/search/confidence

**Purpose:** Get predictions above a confidence threshold

```python
@app.route("/api/predictions/search/confidence", methods=["GET"])
def get_by_confidence():
    threshold = request.args.get('threshold', default=0.0, type=float)
    
    predictions = find_by_confidence_greater_than(threshold)
    
    return jsonify({
        "threshold": threshold,
        "count": len(predictions),
        "data": predictions
    })
```

**Usage:**

```bash
# Get very confident predictions (>90%)
curl "http://localhost:5000/api/predictions/search/confidence?threshold=0.9"

# Get decent predictions (>70%)
curl "http://localhost:5000/api/predictions/search/confidence?threshold=0.7"

# Get all predictions with any confidence (>0%)
curl "http://localhost:5000/api/predictions/search/confidence?threshold=0"
```

**Why This is Useful:**
- Filter out low-quality predictions
- Show only reliable results to users
- Identify which predictions might need manual review

---

### Endpoint 7: GET /api/predictions/search/date-range

**Purpose:** Get predictions within a date range

```python
@app.route("/api/predictions/search/date-range", methods=["GET"])
def get_by_date_range():
    start_date = request.args.get('start', '')
    end_date = request.args.get('end', '')
    
    if not start_date or not end_date:
        return jsonify({"error": "Both start and end date required"}), 400
    
    predictions = find_by_date_range(start_date, end_date)
    
    return jsonify({
        "start_date": start_date,
        "end_date": end_date,
        "count": len(predictions),
        "data": predictions
    })
```

**Usage:**

```bash
# Get predictions from January 2024
curl "http://localhost:5000/api/predictions/search/date-range?start=2024-01-01&end=2024-01-31"

# Get predictions from today
curl "http://localhost:5000/api/predictions/search/date-range?start=2024-04-20&end=2024-04-20"

# Get predictions from last week
curl "http://localhost:5000/api/predictions/search/date-range?start=2024-04-13&end=2024-04-20"
```

**Date Format:** Always use ISO format: `YYYY-MM-DD`

---

### Endpoint 8: GET /api/predictions/stats

**Purpose:** Get analytics and statistics

```python
@app.route("/api/predictions/stats", methods=["GET"])
def get_statistics():
    predictions = load_all_predictions()
    
    # Calculate various statistics
    scientific_names = {}
    families = {}
    confidences = []
    
    for pred in predictions:
        # Count by species
        sci_name = pred.get('scientific_name', 'Unknown')
        scientific_names[sci_name] = scientific_names.get(sci_name, 0) + 1
        
        # Count by family
        family = pred.get('plant_details', {}).get('family', 'Unknown')
        families[family] = families.get(family, 0) + 1
        
        # Collect confidences
        if 'confidence' in pred:
            confidences.append(pred['confidence'])
    
    stats = {
        "total_predictions": len(predictions),
        "unique_species": len(scientific_names),
        "unique_families": len(families),
        "top_5_species": sorted(scientific_names.items(), 
                                key=lambda x: x[1], 
                                reverse=True)[:5],
        "top_5_families": sorted(families.items(), 
                                 key=lambda x: x[1], 
                                 reverse=True)[:5],
        "confidence_stats": {
            "average": sum(confidences) / len(confidences) if confidences else 0,
            "min": min(confidences) if confidences else 0,
            "max": max(confidences) if confidences else 0
        }
    }
    
    return jsonify(stats)
```

**Usage:**

```bash
curl http://localhost:5000/api/predictions/stats
```

**Response:**

```json
{
  "total_predictions": 150,
  "unique_species": 45,
  "unique_families": 12,
  "top_5_species": [
    ["Aloe Vera", 25],
    ["Rosa chinensis", 18],
    ["Mentha spicata", 12],
    ["Lavandula angustifolia", 10],
    ["Thymus vulgaris", 8]
  ],
  "top_5_families": [
    ["Asphodelaceae", 30],
    ["Rosaceae", 25],
    ["Lamiaceae", 20],
    ["Apiaceae", 15],
    ["Solanaceae", 12]
  ],
  "confidence_stats": {
    "average": 0.87,
    "min": 0.45,
    "max": 0.99
  }
}
```

**Use Cases:**
- Dashboard analytics
- Show most popular plants
- Monitor prediction quality
- Generate reports

---

### Endpoint 9: DELETE /api/predictions/{id}

**Purpose:** Delete a prediction

```python
@app.route("/api/predictions/<prediction_id>", methods=["DELETE"])
def delete_prediction(prediction_id):
    success = delete_by_id(prediction_id)
    
    if success:
        return jsonify({"message": f"Prediction {prediction_id} deleted"})
    else:
        return jsonify({"error": "Failed to delete"}), 500
```

**Usage:**

```bash
# Delete prediction with ID 42
curl -X DELETE http://localhost:5000/api/predictions/42
```

---

## 💻 Frontend Integration

### React Example

```jsx
import React, { useState } from 'react';

function PlantPredictor() {
  const [image, setImage] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleImageChange = (e) => {
    setImage(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    const formData = new FormData();
    formData.append('image', image);

    try {
      const response = await fetch('http://localhost:5000/predict', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h1>Plant Identifier</h1>
      
      <form onSubmit={handleSubmit}>
        <input 
          type="file" 
          accept="image/*" 
          onChange={handleImageChange}
          required
        />
        <button type="submit" disabled={!image || loading}>
          {loading ? 'Identifying...' : 'Identify Plant'}
        </button>
      </form>

      {result && (
        <div className="result">
          <h2>{result.scientific_name}</h2>
          {result.indonesian_name && (
            <p>Indonesian: {result.indonesian_name}</p>
          )}
          <p>Confidence: {(result.confidence * 100).toFixed(2)}%</p>
          
          {result.plant_details && (
            <div>
              <p>Family: {result.plant_details.family}</p>
              <p>Genus: {result.plant_details.genus}</p>
              {result.plant_details.image_url && (
                <img src={result.plant_details.image_url} alt={result.scientific_name} />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default PlantPredictor;
```

### Fetching Prediction History

```jsx
function PredictionHistory() {
  const [predictions, setPredictions] = useState([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const limit = 10;

  useEffect(() => {
    fetchPredictions();
  }, [page]);

  const fetchPredictions = async () => {
    const offset = (page - 1) * limit;
    const response = await fetch(
      `http://localhost:5000/api/predictions?limit=${limit}&offset=${offset}`
    );
    const data = await response.json();
    
    setPredictions(data.data);
    setTotal(data.total);
  };

  return (
    <div>
      <h2>Prediction History</h2>
      
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Plant Name</th>
            <th>Confidence</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {predictions.map(pred => (
            <tr key={pred.id}>
              <td>{pred.id}</td>
              <td>{pred.scientific_name}</td>
              <td>{(pred.confidence * 100).toFixed(2)}%</td>
              <td>{new Date(pred.timestamp).toLocaleDateString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button 
          onClick={() => setPage(p => Math.max(1, p - 1))}
          disabled={page === 1}
        >
          Previous
        </button>
        
        <span>Page {page} of {Math.ceil(total / limit)}</span>
        
        <button 
          onClick={() => setPage(p => p + 1)}
          disabled={page >= Math.ceil(total / limit)}
        >
          Next
        </button>
      </div>
    </div>
  );
}
```

### Search Functionality

```jsx
function PlantSearch() {
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState([]);

  const handleSearch = async (e) => {
    e.preventDefault();
    
    const response = await fetch(
      `http://localhost:5000/api/predictions/search/scientific-name-contains?keyword=${keyword}`
    );
    const data = await response.json();
    
    setResults(data.data);
  };

  return (
    <div>
      <h2>Search Plants</h2>
      
      <form onSubmit={handleSearch}>
        <input
          type="text"
          value={keyword}
          onChange={(e) => setKeyword(e.target.value)}
          placeholder="Enter plant name..."
        />
        <button type="submit">Search</button>
      </form>

      <div className="results">
        <p>Found {results.length} results</p>
        {results.map(result => (
          <div key={result.id} className="result-card">
            <h3>{result.scientific_name}</h3>
            <p>Confidence: {(result.confidence * 100).toFixed(2)}%</p>
            <p>Date: {new Date(result.timestamp).toLocaleString()}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Statistics Dashboard

```jsx
function Dashboard() {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetch('http://localhost:5000/api/predictions/stats')
      .then(res => res.json())
      .then(data => setStats(data));
  }, []);

  if (!stats) return <div>Loading...</div>;

  return (
    <div className="dashboard">
      <h1>Analytics Dashboard</h1>
      
      <div className="stats-grid">
        <div className="stat-card">
          <h3>Total Predictions</h3>
          <p className="big-number">{stats.total_predictions}</p>
        </div>
        
        <div className="stat-card">
          <h3>Unique Species</h3>
          <p className="big-number">{stats.unique_species}</p>
        </div>
        
        <div className="stat-card">
          <h3>Avg Confidence</h3>
          <p className="big-number">
            {(stats.confidence_stats.average * 100).toFixed(1)}%
          </p>
        </div>
      </div>

      <div className="top-plants">
        <h2>Top 5 Plants</h2>
        <ul>
          {stats.top_5_species.map(([name, count]) => (
            <li key={name}>
              <strong>{name}</strong>: {count} predictions
            </li>
          ))}
        </ul>
      </div>

      <div className="top-families">
        <h2>Top 5 Families</h2>
        <ul>
          {stats.top_5_families.map(([family, count]) => (
            <li key={family}>
              <strong>{family}</strong>: {count} predictions
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
```

---

## 🧪 Testing Your API

### Using cURL (Command Line)

```bash
# 1. Test prediction endpoint
curl -X POST http://localhost:5000/predict \
  -F "image=@test_plant.jpg"

# 2. Get all predictions
curl http://localhost:5000/api/predictions

# 3. Get prediction by ID
curl http://localhost:5000/api/predictions/1

# 4. Search by name
curl "http://localhost:5000/api/predictions/search/scientific-name-contains?keyword=aloe"

# 5. Get high confidence predictions
curl "http://localhost:5000/api/predictions/search/confidence?threshold=0.9"

# 6. Get statistics
curl http://localhost:5000/api/predictions/stats

# 7. Delete a prediction
curl -X DELETE http://localhost:5000/api/predictions/5
```

### Using Python

Create a test script `test_api.py`:

```python
import requests
import json

BASE_URL = "http://localhost:5000"

# Test 1: Upload and predict
print("Test 1: Upload image")
with open('test_plant.jpg', 'rb') as f:
    files = {'image': f}
    response = requests.post(f"{BASE_URL}/predict", files=files)
    print(f"Status: {response.status_code}")
    print(json.dumps(response.json(), indent=2))

# Test 2: Get all predictions
print("\nTest 2: Get all predictions")
response = requests.get(f"{BASE_URL}/api/predictions?limit=5")
print(json.dumps(response.json(), indent=2))

# Test 3: Search
print("\nTest 3: Search for plants")
response = requests.get(
    f"{BASE_URL}/api/predictions/search/scientific-name-contains",
    params={"keyword": "aloe"}
)
print(json.dumps(response.json(), indent=2))

# Test 4: Get stats
print("\nTest 4: Get statistics")
response = requests.get(f"{BASE_URL}/api/predictions/stats")
print(json.dumps(response.json(), indent=2))
```

Run it:
```bash
python test_api.py
```

### Using Postman

1. **Download Postman** from https://www.postman.com/

2. **Create a new request collection:**
   - Name: "Plant Prediction API"

3. **Add requests:**

**POST /predict:**
- Method: POST
- URL: http://localhost:5000/predict
- Body: form-data
  - Key: image (type: File)
  - Value: Select your image file

**GET /api/predictions:**
- Method: GET
- URL: http://localhost:5000/api/predictions?limit=10&offset=0

**GET /api/predictions/search/scientific-name-contains:**
- Method: GET
- URL: http://localhost:5000/api/predictions/search/scientific-name-contains
- Params:
  - keyword: aloe

---

## 🐛 Troubleshooting

### Problem 1: "Connection Refused" Error

**Symptoms:**
```
curl: (7) Failed to connect to localhost port 5000: Connection refused
```

**Solutions:**

1. **Check if server is running:**
```bash
python app_enhanced.py
```
You should see:
```
 * Running on http://127.0.0.1:5000
```

2. **Check if port is already in use:**
```bash
# On Linux/Mac
lsof -i :5000

# On Windows
netstat -ano | findstr :5000
```

3. **Use a different port:**
```python
# In app_enhanced.py, change the last line to:
if __name__ == "__main__":
    app.run(debug=True, port=5001)
```

---

### Problem 2: CORS Error in Browser

**Symptoms:**
```
Access to fetch at 'http://localhost:5000/predict' from origin 'http://localhost:3000' 
has been blocked by CORS policy
```

**Solution:**

Make sure `flask-cors` is installed and enabled:

```python
# At the top of app_enhanced.py
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # ← This line must be present
```

If still not working, specify allowed origins:

```python
CORS(app, resources={
    r"/api/*": {"origins": "http://localhost:3000"},
    r"/predict": {"origins": "http://localhost:3000"}
})
```

---

### Problem 3: "No module named 'inference'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'inference'
```

**Solutions:**

1. **Make sure `inference.py` exists** in the same folder as `app_enhanced.py`

2. **Check your `inference.py` has a `predict` function:**
```python
# inference.py
def predict(image_path):
    # Your model code here
    return {
        "final": "Plant Name",
        "confidence": 0.95
    }
```

3. **If using a different file name**, change the import:
```python
# If your file is named my_model.py
from my_model import predict
```

---

### Problem 4: Images Not Being Saved

**Symptoms:**
- Predictions work but images aren't in `uploads/` folder

**Explanation:**
This is actually **normal behavior**! The code deletes images after processing:

```python
finally:
    if os.path.exists(image_path):
        os.remove(image_path)  # ← Deletes the image
```

**To keep images:**

Remove or comment out the cleanup code:

```python
finally:
    pass  # Don't delete images
    # if os.path.exists(image_path):
    #     os.remove(image_path)
```

Or save to a permanent folder:

```python
PERMANENT_FOLDER = "permanent_uploads"
os.makedirs(PERMANENT_FOLDER, exist_ok=True)

# After prediction
import shutil
permanent_path = os.path.join(PERMANENT_FOLDER, filename)
shutil.copy2(image_path, permanent_path)
```

---

### Problem 5: Trefle API Not Working

**Symptoms:**
```
⚠️  No results found for 'aloe-vera'
❌ Trefle API error: 401
```

**Solutions:**

1. **Check if API key is set:**
```python
# Make sure you replaced the placeholder
"token": "YOUR_ACTUAL_TOKEN_HERE"  # Not ['TREFLE_TOKEN']
```

2. **Test API manually:**
```bash
curl "https://trefle.io/api/v1/plants/search?token=YOUR_TOKEN&q=aloe"
```

3. **Check Trefle API status:**
- Visit https://trefle.io/
- Make sure service is running
- Check if you've exceeded rate limits

4. **Make prediction work without Trefle:**
```python
# In predict_route(), make Trefle optional
plant_info = get_plant_info(scientific_name)
if plant_info:
    result["plant_details"] = plant_info
else:
    # Still return result even without Trefle data
    print("Trefle unavailable, continuing without plant details")
```

---

### Problem 6: JSON File Corrupted

**Symptoms:**
```
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**Solution:**

Reset the predictions file:

```bash
# Backup the corrupted file
mv prediction_history/predictions.json prediction_history/predictions.json.backup

# Create a fresh empty file
echo "[]" > prediction_history/predictions.json
```

Or in Python:

```python
import json

with open('prediction_history/predictions.json', 'w') as f:
    json.dump([], f)
```

---

### Problem 7: Model Loading Error

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'models/plant_model.pth'
```

**Solutions:**

1. **Check if model file exists:**
```bash
ls -la models/
```

2. **Update path in `inference.py`:**
```python
# Use absolute path
import os
model_path = os.path.join(os.path.dirname(__file__), 'models', 'plant_model.pth')
model = torch.load(model_path)
```

3. **Check file permissions:**
```bash
chmod 644 models/plant_model.pth
```

---

## 🚀 Advanced Features

### Feature 1: Add Image Preview URLs

**Problem:** You want to show thumbnails of uploaded images in frontend

**Solution:** Save images permanently and return URLs

```python
# Add this configuration
PERMANENT_UPLOADS = "permanent_uploads"
os.makedirs(PERMANENT_UPLOADS, exist_ok=True)

# In predict_route(), after file.save():
import shutil
import uuid

# Generate unique filename
unique_filename = f"{uuid.uuid4()}_{filename}"
permanent_path = os.path.join(PERMANENT_UPLOADS, unique_filename)
shutil.copy2(image_path, permanent_path)

# Add to result
result["image_url"] = f"/uploads/{unique_filename}"

# Add route to serve images
from flask import send_from_directory

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(PERMANENT_UPLOADS, filename)
```

Now frontend can display images:
```jsx
<img src={`http://localhost:5000${result.image_url}`} alt="Uploaded plant" />
```

---

### Feature 2: Add User Authentication

**Problem:** You want to track which user made which prediction

**Solution:** Add user ID to predictions

```python
# Install Flask-JWT
pip install flask-jwt-extended

# In app_enhanced.py
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app.config['JWT_SECRET_KEY'] = 'your-secret-key-change-this'
jwt = JWTManager(app)

# Login endpoint
@app.route("/login", methods=["POST"])
def login():
    username = request.json.get('username')
    password = request.json.get('password')
    
    # Validate user (simplified - use proper auth in production)
    if username == "admin" and password == "password":
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token)
    
    return jsonify({"error": "Invalid credentials"}), 401

# Protect predict endpoint
@app.route("/predict", methods=["POST"])
@jwt_required()  # ← Requires valid token
def predict_route():
    current_user = get_jwt_identity()
    
    # ... existing code ...
    
    # Add user to result
    result["user"] = current_user
    save_prediction_to_history(result)
    
    return jsonify(result)
```

Frontend usage:
```javascript
// Login
const loginResponse = await fetch('http://localhost:5000/login', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({username: 'admin', password: 'password'})
});
const {access_token} = await loginResponse.json();

// Use token for predictions
const formData = new FormData();
formData.append('image', file);

const response = await fetch('http://localhost:5000/predict', {
  method: 'POST',
  headers: {'Authorization': `Bearer ${access_token}`},
  body: formData
});
```

---

### Feature 3: Rate Limiting

**Problem:** Prevent API abuse

**Solution:** Add rate limiting

```python
# Install Flask-Limiter
pip install flask-limiter

# In app_enhanced.py
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply to specific endpoints
@app.route("/predict", methods=["POST"])
@limiter.limit("10 per minute")  # Max 10 predictions per minute
def predict_route():
    # ... existing code ...
```

---

### Feature 4: Email Notifications

**Problem:** Send results via email

**Solution:** Add email functionality

```python
# Install Flask-Mail
pip install flask-mail

from flask_mail import Mail, Message

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your-app-password'

mail = Mail(app)

# Add email parameter to predict
@app.route("/predict", methods=["POST"])
def predict_route():
    email = request.form.get('email')  # Optional email field
    
    # ... existing prediction code ...
    
    if email:
        msg = Message(
            'Plant Identification Result',
            sender='your-email@gmail.com',
            recipients=[email]
        )
        msg.body = f"""
        Your plant has been identified!
        
        Scientific Name: {result['scientific_name']}
        Confidence: {result['confidence']*100:.2f}%
        
        View full details: http://yourwebsite.com/results/{result['id']}
        """
        mail.send(msg)
    
    return jsonify(result)
```

---

### Feature 5: Export to CSV

**Problem:** Export prediction history to Excel/CSV

**Solution:** Add export endpoint

```python
import csv
from flask import make_response
from io import StringIO

@app.route("/api/predictions/export/csv", methods=["GET"])
def export_to_csv():
    predictions = load_all_predictions()
    
    # Create CSV in memory
    si = StringIO()
    writer = csv.writer(si)
    
    # Write header
    writer.writerow(['ID', 'Scientific Name', 'Indonesian Name', 
                     'Confidence', 'Family', 'Timestamp'])
    
    # Write data
    for pred in predictions:
        writer.writerow([
            pred.get('id', ''),
            pred.get('scientific_name', ''),
            pred.get('indonesian_name', ''),
            pred.get('confidence', ''),
            pred.get('plant_details', {}).get('family', ''),
            pred.get('timestamp', '')
        ])
    
    # Create response
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = "attachment; filename=predictions.csv"
    output.headers["Content-type"] = "text/csv"
    
    return output
```

Usage:
```bash
# Download CSV file
curl http://localhost:5000/api/predictions/export/csv > predictions.csv
```

---

## 📝 Best Practices

### 1. Environment Variables

**Don't hardcode sensitive data:**

```python
# ❌ Bad
"token": "sk-abc123xyz456"

# ✅ Good
import os
"token": os.getenv('TREFLE_API_KEY')
```

Create a `.env` file:
```
TREFLE_API_KEY=sk-abc123xyz456
TREFLE_API_URL=https://trefle.io/api/v1/plants/search
FLASK_SECRET_KEY=your-secret-key
```

Load it:
```python
from dotenv import load_dotenv
load_dotenv()

app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY')
```

---

### 2. Error Handling

**Always handle errors gracefully:**

```python
@app.route("/predict", methods=["POST"])
def predict_route():
    try:
        # ... your code ...
        return jsonify(result)
        
    except FileNotFoundError as e:
        return jsonify({"error": "Model file not found"}), 500
        
    except ValueError as e:
        return jsonify({"error": "Invalid image format"}), 400
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500
```

---

### 3. Input Validation

**Validate all inputs:**

```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/predict", methods=["POST"])
def predict_route():
    if 'image' not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    
    file = request.files['image']
    
    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Use PNG, JPG, or JPEG"}), 400
    
    # Continue processing...
```

---

### 4. Logging

**Add proper logging:**

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@app.route("/predict", methods=["POST"])
def predict_route():
    logger.info(f"Prediction request received from {request.remote_addr}")
    
    try:
        result = predict(image_path)
        logger.info(f"Prediction successful: {result['scientific_name']}")
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Prediction failed: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500
```

---

### 5. Database Migration (Future)

**When you outgrow JSON, migrate to SQLite or PostgreSQL:**

```python
# Using SQLAlchemy
from flask_sqlalchemy import SQLAlchemy

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///predictions.db'
db = SQLAlchemy(app)

class Prediction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    scientific_name = db.Column(db.String(200))
    indonesian_name = db.Column(db.String(200))
    confidence = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
# Create tables
with app.app_context():
    db.create_all()

# Save prediction
new_prediction = Prediction(
    scientific_name=scientific_name,
    confidence=confidence
)
db.session.add(new_prediction)
db.session.commit()

# Query
predictions = Prediction.query.filter_by(scientific_name="Aloe Vera").all()
```

---

## 🎓 Summary

### What You've Learned

1. ✅ **Flask Basics** - Routes, requests, responses
2. ✅ **File Uploads** - Handling multipart/form-data
3. ✅ **REST API Design** - GET, POST, DELETE methods
4. ✅ **Database Operations** - CRUD with JSON
5. ✅ **External APIs** - Calling Trefle API
6. ✅ **Query Patterns** - JPA-style repositories
7. ✅ **CORS** - Frontend-backend communication
8. ✅ **Error Handling** - Try-catch, status codes
9. ✅ **Data Persistence** - JSON file storage
10. ✅ **Frontend Integration** - React examples

### Quick Reference Card

```
POST   /predict                    → Upload and predict
GET    /api/predictions            → List all (paginated)
GET    /api/predictions/:id        → Get one by ID
GET    /api/predictions/search/*   → Search/filter
GET    /api/predictions/stats      → Analytics
DELETE /api/predictions/:id        → Delete one
```

### Next Steps

1. **Add authentication** (JWT tokens)
2. **Migrate to real database** (PostgreSQL/MySQL)
3. **Add caching** (Redis for faster queries)
4. **Deploy to production** (Heroku, AWS, or DigitalOcean)
5. **Add automated tests** (pytest)
6. **Set up CI/CD** (GitHub Actions)
7. **Add monitoring** (Sentry for errors)
8. **Scale horizontally** (Load balancer + multiple instances)

---

## 🆘 Getting Help

### Common Resources

- **Flask Documentation**: https://flask.palletsprojects.com/
- **Stack Overflow**: https://stackoverflow.com/questions/tagged/flask
- **Flask Discord**: https://discord.gg/pallets
- **Your Code**: Read error messages carefully!

### Debugging Tips

1. **Check the terminal** where Flask is running - errors appear there
2. **Use `print()` statements** to see what's happening
3. **Test with cURL first** before blaming your frontend
4. **Read the error message** - it usually tells you exactly what's wrong
5. **Google the error** - someone has likely had the same issue

---

**Happy coding! 🚀 Your plant prediction API is ready to grow! 🌱**
