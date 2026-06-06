import os

from dotenv import load_dotenv
from flask import Blueprint, jsonify, request
import supabase as supabase_client

from core.plant_info import get_plant_info

load_dotenv()

explore_bp = Blueprint("explore", __name__)

REMEDY_SELECT = (
    "instructions, used_for, dosage, side_effects, contraindications, warnings, "
    "interactions, part_used, herbs(herb_name)"
)

EXPLORE_SELECT = (
    "recipe_id, herb_id, instructions, used_for, dosage, side_effects, "
    "contraindications, warnings, interactions, part_used, "
    "herbs(herb_id, herb_name, scientific_name)"
)

supabase = supabase_client.create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)


def format_remedy(item):
    herb = item.get("herbs") or {}
    return {
        "herb_name": herb.get("herb_name"),
        "instructions": item.get("instructions"),
        "used_for": item.get("used_for"),
        "dosage": item.get("dosage"),
        "side_effects": item.get("side_effects"),
        "contraindications": item.get("contraindications"),
        "warnings": item.get("warnings"),
        "interactions": item.get("interactions"),
        "part_used": item.get("part_used"),
    }


@explore_bp.route("/api/remedies", methods=["GET"])
def get_remedies():
    res = supabase.table("herbal_recipes").select(REMEDY_SELECT).execute()

    return jsonify([format_remedy(item) for item in res.data]), 200


@explore_bp.route("/api/remedies/by/<herb_name>", methods=["GET"])
def get_remedies_by_herb(herb_name):
    herb_res = supabase.table("herbs") \
        .select("herb_id, herb_name") \
        .eq("herb_name", herb_name) \
        .execute()

    if not herb_res.data:
        return jsonify([]), 200

    herb_ids = [row["herb_id"] for row in herb_res.data]

    res = supabase.table("herbal_recipes") \
        .select(REMEDY_SELECT) \
        .in_("herb_id", herb_ids) \
        .execute()

    return jsonify([format_remedy(item) for item in res.data]), 200


@explore_bp.route("/api/explore", methods=["GET"])
def get_explore():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 6, type=int)

    start = (page - 1) * per_page
    end = page * per_page - 1

    remedies_res = supabase.table("herbal_recipes").select(
        EXPLORE_SELECT
    ).order(
        "recipe_id", desc=False
    ).range(
        start, end
    ).execute()

    count_res = supabase.table("herbal_recipes").select("recipe_id", count="exact").execute()
    total = count_res.count or 0
    total_pages = max(1, -(-total // per_page))

    result = []

    for item in remedies_res.data:
        herb = item.get("herbs") or {}

        recipe_id = item.get("recipe_id")
        herb_id = item.get("herb_id")
        scientific_name = herb.get("scientific_name") or ""
        herb_name = herb.get("herb_name") or ""

        search_term = scientific_name or herb_name
        plant_info = get_plant_info(search_term) if search_term else None

        result.append({
            "id": recipe_id,
            "recipe_id": recipe_id,
            "herb_id": herb_id,
            "herb_name": herb_name,
            "scientific_name": (plant_info.get("scientific_name") if plant_info else None) or scientific_name,
            "common_name": (plant_info.get("common_name") if plant_info else None) or herb_name,
            "image_url": plant_info.get("image_url") if plant_info else None,
            "remedies": [{
                "recipe_id": recipe_id,
                "used_for": item.get("used_for"),
                "part_used": item.get("part_used"),
                "dosage": item.get("dosage"),
                "instructions": item.get("instructions"),
                "side_effects": item.get("side_effects"),
                "contraindications": item.get("contraindications"),
                "warnings": item.get("warnings"),
                "interactions": item.get("interactions"),
            }],
        })

    return jsonify({
        "herbs": result,
        "total_pages": total_pages,
        "total": total,
        "page": page,
    }), 200
