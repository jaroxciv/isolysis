import pandas as pd
import json
import os
import uuid

# Paths
DATA_DIR = "data"
xlsx_path = os.path.join(DATA_DIR, "coords.xlsx")
json_path = os.path.join(DATA_DIR, "coords.json")

# Load Excel
df = pd.read_excel(xlsx_path)

# Rename columns to match Pydantic model fields
df = df.rename(
    columns={
        "Latitud": "lat",
        "Longitud": "lon",
        "Region": "region",
        "Departamento": "department",
        "Municipio": "municipality",
        "Unidad SIS": "unit_sis",
        "Nombre": "name",
    }
)

# Drop ISO columns if present
for col in ["ISO1", "ISO2", "ISO3"]:
    if col in df.columns:
        df = df.drop(columns=col)

# Add a UUID for each row (string type)
df["id"] = [str(uuid.uuid4()) for _ in range(len(df))]

# Convert DataFrame to list of dicts (records)
records = df.where(pd.notnull(df), None).to_dict(orient="records")

# Save as JSON
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(records, f, ensure_ascii=False, indent=2)

print(f"Saved {len(records)} records to {json_path}")
