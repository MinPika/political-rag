from sqlalchemy import create_engine, text
import pandas as pd
import json
from collections import Counter
from copy import deepcopy
from config.db_config import engine


# ---------- 2️⃣ Cleaning + Enrichment Function ----------
def clean_and_enrich(data: dict):
    """Clean, enrich, and restructure a record from the visualizer table."""
    cleaned = deepcopy(data)

    # Ensure all objects are JSON-safe
    def make_json_safe(obj):
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            if isinstance(obj, (dict, list)):
                return json.loads(json.dumps(obj, default=str))
            return str(obj)

    for k, v in cleaned.items():
        cleaned[k] = make_json_safe(v)

    # ---------- Helper: safely parse strings to JSON ----------
    def parse_json_safe(obj):
        if isinstance(obj, str):
            try:
                return json.loads(obj)
            except json.JSONDecodeError:
                return {}
        return obj or {}

    # Extract main fields safely
    text_content = data.get("text", "") or ""
    sentiment = parse_json_safe(data.get("sentiment", {}))
    leadership = parse_json_safe(data.get("leadership_polarity", {}))
    entities = parse_json_safe(data.get("entities", [])) or []
    tags = parse_json_safe(data.get("tags", {}))
    geo = parse_json_safe(data.get("geo", {}))

    # ---------- Fix: ensure geo is a dict ----------
    if not isinstance(geo, dict):
        geo = {}

    cleaned["metadata_enriched"] = {
        "text_length": len(text_content),
        "word_count": len(text_content.split()),
        "is_government_source": (
            str(data.get("source_type", "")).lower() == "government"
        ),
        "geo_level": (
            ", ".join([v for v in geo.values() if v]) if isinstance(geo, dict) else None
        ),
        "dominant_tone": (
            "Neutral"
            if sentiment.get("polarity") == "neutral"
            else ("Positive" if sentiment.get("score", 0) > 0 else "Negative")
        ),
        "entity_count": len(entities),
        "unique_entity_types": list({e.get("type") for e in entities if e.get("type")}),
        "issue_count": len(tags.get("issues", [])) if isinstance(tags, dict) else None,
    }

    cleaned["summaries"] = {
        "entities_summary": {
            "total_entities": len(entities),
            "most_common_entity_types": dict(
                Counter([e.get("type") for e in entities if e.get("type")]).most_common(
                    5
                )
            ),
            "sample_entities": [
                e.get("text") or e.get("name") for e in entities[:10] if e
            ],
        },
        "tags_summary": {
            "frame": tags.get("frame"),
            "domain": tags.get("domain"),
            "actors": tags.get("actors"),
            "issues": tags.get("issues"),
            "actionability": tags.get("actionability"),
            "leadership_polarity": tags.get("leadership_polarity"),
            "confidence": tags.get("confidence"),
        },
        "sentiment_summary": {
            "overall_polarity": sentiment.get("polarity"),
            "overall_score": sentiment.get("score"),
            "leadership_score": leadership.get("score"),
            "leadership_polarity": leadership.get("polarity"),
        },
    }

    cleaned["data_quality"] = {
        "has_text": bool(text_content.strip()),
        "has_entities": len(entities) > 0,
        "has_geo": bool(geo),
        "has_sentiment": bool(sentiment),
        "has_tags": bool(tags),
        "missing_fields": [k for k, v in data.items() if v in [None, "", [], {}]],
    }

    return cleaned


# ---------- 3️⃣ Extract All Rows from 'visualizer' ----------
print("📤 Fetching all rows from 'visualizer' table...")
with engine.connect() as conn:
    df_raw = pd.read_sql(text("SELECT * FROM visualizer"), conn)

print(f"✅ Retrieved {len(df_raw)} rows.")

# ---------- 4️⃣ Clean + Enrich Each Row ----------
cleaned_records = []
for _, row in df_raw.iterrows():
    data = row.to_dict()
    enriched = clean_and_enrich(data)
    cleaned_records.append(enriched)

# ---------- 5️⃣ Convert to DataFrame ----------
df_cleaned = pd.DataFrame(cleaned_records)

# Convert complex fields (dict/list) → JSON strings before saving
for col in df_cleaned.columns:
    df_cleaned[col] = df_cleaned[col].apply(
        lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
    )

# ---------- 6️⃣ Save as New Table 'cleanedv1' ----------
table_name = "cleanedv1"
print(f"💾 Creating table '{table_name}' in PostgreSQL...")

df_cleaned.to_sql(name=table_name, con=engine, if_exists="replace", index=False)

print(f"✅ Successfully created '{table_name}' with {len(df_cleaned)} rows.")
