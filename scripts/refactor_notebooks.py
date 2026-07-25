import json
import glob
import os

def update_notebook(filepath):
    print(f"Updating {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for cell in nb.get("cells", []):
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        new_source = []
        for line in source:
            if "from dotenv import load_dotenv" in line:
                new_source.append("import sys\n")
                new_source.append("sys.path.append(\"..\")\n")
                new_source.append("import config\n")
            elif "load_dotenv(" in line:
                pass
            elif "from sqlalchemy import create_engine" in line:
                new_source.append(line.replace("create_engine, ", "").replace("create_engine", ""))
            elif line.startswith("DB_") and "os.getenv(" in line:
                pass
            elif "create_engine(" in line and "mysql+pymysql://" in line:
                if "#engine =" not in line:
                    new_source.append("engine = config.get_sqlalchemy_engine()\n")
            elif "ADZUNA_APP_ID = os.getenv(" in line:
                new_source.append("ADZUNA_APP_ID = config.ADZUNA_APP_ID\n")
            elif "ADZUNA_APP_KEY = os.getenv(" in line:
                new_source.append("ADZUNA_APP_KEY = config.ADZUNA_APP_KEY\n")
            elif line.strip() == "from urllib.parse import quote_plus":
                pass
            elif line.strip() == "#engine = create_engine(f\"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}\")":
                pass
            else:
                new_source.append(line)
        cell["source"] = new_source

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
        f.write("\n")

notebooks = glob.glob(os.path.join(os.path.dirname(__file__), "..", "notebooks", "*.ipynb"))
for nb in notebooks:
    update_notebook(nb)
