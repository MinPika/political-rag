from sqlalchemy import create_engine, text
import pandas as pd
import json
from config.db_config import engine

# ---------- 2️⃣ SQL Join Query ----------
join_query = text(
    """
    SELECT 
        s.source_url,
        s.title,
        s.domain,
        s.source_type,
        s.geo,
        c.source_id,
        c.text,
        c.entities,
        c.tags,
        c.sentiment,
        c.leadership_polarity
    FROM chunks c
    JOIN sources s ON c.source_id = s.id
"""
)

# ---------- 3️⃣ Fetch Joined Data ----------
with engine.connect() as conn:
    df_combined = pd.read_sql(join_query, conn)

print("✅ Data joined successfully. Number of rows:", len(df_combined))

# ---------- 4️⃣ Convert dict/list columns to JSON strings ----------
json_cols = ["entities", "tags", "sentiment", "leadership_polarity", "geo"]

for col in json_cols:
    if col in df_combined.columns:
        df_combined[col] = df_combined[col].apply(
            lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
        )

# ---------- 5️⃣ Write DataFrame to Database ----------
table_name = "visualizer"  # or "combined_data"

df_combined.to_sql(
    name=table_name,
    con=engine,
    if_exists="replace",  # replace table if exists
    index=False,
    dtype=None,  # SQLAlchemy will infer datatypes
)

print(f"✅ New table '{table_name}' created successfully in the database.")
