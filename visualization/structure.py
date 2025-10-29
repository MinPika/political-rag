from sqlalchemy import text
import pandas as pd
import json
from config.db_config import engine


# ---------- 2️⃣ Function to Extract a Row from 'visualizer' ----------
def get_row_as_json(row_id: int, engine):
    """
    Extracts a single row from the 'visualizer' table and returns it as a JSON object.
    row_id: The index (row number) or primary key value if you have one.
    """
    query = text(
        f"""
        SELECT * FROM visualizer
        LIMIT 1 OFFSET :offset
    """
    )
    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={"offset": row_id})

    if df.empty:
        print("❌ No row found for the given ID.")
        return None

    # Convert to dict (single row) → JSON
    row_dict = df.iloc[0].to_dict()

    # Convert stringified JSON columns back to Python dicts if needed
    json_cols = ["entities", "tags", "sentiment", "leadership_polarity", "geo"]
    for col in json_cols:
        if col in row_dict and isinstance(row_dict[col], str):
            try:
                row_dict[col] = json.loads(row_dict[col])
            except json.JSONDecodeError:
                pass  # skip if not valid JSON

    return row_dict


# ---------- 3️⃣ Example Usage ----------
row_id = 129  # first row (0-based index)
row_json = get_row_as_json(row_id, engine)

# ---------- 4️⃣ Output ----------
if row_json:
    print(json.dumps(row_json, indent=2))
 