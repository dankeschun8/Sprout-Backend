import os

import requests


def get_plant_info(plant_name):
    try:
        query_name = plant_name.replace(" ", "-")
        params = {
            "token": [os.getenv("TREFLE_TOKEN")],
            "q": query_name,
        }
        response = requests.get(os.getenv("TREFLE_API_URL"), params=params, timeout=10)

        if response.status_code != 200:
            return None

        data = response.json()
        plants = data.get("data") or []
        if not plants:
            return None

        plant = plants[0]
        return {
            "scientific_name": plant.get("scientific_name"),
            "common_name": plant.get("common_name"),
            "image_url": plant.get("image_url"),
        }
    except Exception as e:
        print(f"Error fetching plant info: {str(e)}")
        return None
