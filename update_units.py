import json
import re

with open("color_scales.json", "r", encoding="utf-8") as f:
    data = json.load(f)

for var, var_data in data.items():
    if not isinstance(var_data, dict):
        continue
    
    # default unit
    base_unit = ""
    name = var_data.get("name", "")
    match = re.search(r'\(([^)]+)\)$', name)
    if match:
        base_unit = match.group(1).strip()
    
    for jenis in ["KLIMATOLOGI", "TREND", "CHANGE", "VALUE"]:
        if jenis in var_data:
            if jenis == "KLIMATOLOGI":
                var_data[jenis]["unit"] = base_unit
            elif jenis == "TREND":
                var_data[jenis]["unit"] = f"{base_unit}/decade" if base_unit else "per decade"
            elif jenis == "CHANGE":
                var_data[jenis]["unit"] = "%"
            elif jenis == "VALUE":
                var_data[jenis]["unit"] = base_unit

with open("color_scales.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

