import torch
from PIL import Image
import json
from torchvision import transforms

from core.model import InternImageClassifier

WEIGHTS_PATH = "weights/internimage.pth"
CLASS_NAMES_PATH = "class_names.json"
IMAGE_SIZE = 128
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

torch.set_grad_enabled(False)

with open(CLASS_NAMES_PATH, "r") as f:
    class_names = json.load(f)

num_classes = len(class_names)

model = InternImageClassifier(
    num_classes=num_classes,
    pretrained=False
)
model.to(DEVICE)

checkpoint = torch.load(
    WEIGHTS_PATH,
    map_location=DEVICE,
    weights_only=True
)
model.load_state_dict(checkpoint["model_state_dict"])
model.eval()

transform = transforms.Compose([
    transforms.Resize((IMAGE_SIZE, IMAGE_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize(
        mean=[0.485, 0.456, 0.406],
        std=[0.229, 0.224, 0.225]
    )
])


def predict(image_path: str):
    image = Image.open(image_path).convert("RGB")
    tensor = transform(image).unsqueeze(0).to(DEVICE)

    outputs = model(tensor)
    probs = torch.softmax(outputs, dim=1)

    topk_conf, topk_idx = torch.topk(probs, k=3)

    results = []
    for conf, idx in zip(topk_conf[0], topk_idx[0]):
        results.append({
            "class": class_names[idx.item()],
            "confidence": round(conf.item(), 4)
        })

    if results[0]["confidence"] < 0.7:
        return {
            "predictions": results,
            "final": "Unknown"
        }

    return {
        "final": results[0]["class"],
        "predictions": results
    }
