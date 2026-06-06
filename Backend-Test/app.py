import gdown
import os
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

MODEL_PATH = "weights/internimage.pth"
MODEL_URL = "https://drive.google.com/uc?id=1zcQ6sa-mVxv6y5OWqTtHT5Mn0dyiGrEp"


def model_file_is_invalid(path):
    if not os.path.exists(path):
        return True

    # Real model is around 106 MB.
    # Git LFS pointer file is usually very small.
    if os.path.getsize(path) < 10 * 1024 * 1024:
        return True

    # Detect Git LFS pointer file
    try:
        with open(path, "rb") as f:
            start = f.read(200)
            if b"git-lfs" in start or start.startswith(b"version"):
                return True
    except Exception:
        return True

    return False


if model_file_is_invalid(MODEL_PATH):
    os.makedirs("weights", exist_ok=True)
    print("Downloading model weights...")

    gdown.download(
        MODEL_URL,
        MODEL_PATH,
        quiet=False
    )

    print("Model downloaded.")


from routes.predict import predict_bp
from routes.explore import explore_bp

app = Flask(__name__)
CORS(app)


@app.route("/")
def home():
    return {"message": "Herbify backend is running"}


app.register_blueprint(predict_bp)
app.register_blueprint(explore_bp)


if __name__ == "__main__":
    app.run(debug=True)