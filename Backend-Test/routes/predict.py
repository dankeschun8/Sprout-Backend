import os
import re

from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from core.inference import predict
from core.plant_info import get_plant_info

load_dotenv()

predict_bp = Blueprint("predict", __name__)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def extract_plant_name(class_label):
    match = re.match(r"^(.+?)\s*\(", class_label)
    return match.group(1).strip() if match else class_label.strip()


def get_indonesian_name(class_label):
    match = re.search(r"\((.+?)\)", class_label)
    return match.group(1).strip() if match else None


@predict_bp.route("/predict", methods=["POST"])
def predict_route():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "Empty filename"}), 400

    filename = secure_filename(file.filename)
    image_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(image_path)

    try:
        result = predict(image_path)
        class_label = result.get("final")

        if class_label and class_label != "Unknown":
            scientific_name = extract_plant_name(class_label)
            indonesian_name = get_indonesian_name(class_label)

            result["scientific_name"] = scientific_name
            if indonesian_name:
                result["indonesian_name"] = indonesian_name

            plant_info = get_plant_info(scientific_name)
            if plant_info:
                result["plant_details"] = plant_info

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)
