from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.db import bootstrap_inventory_db


if __name__ == "__main__":
    bootstrap_inventory_db(Path("inventory.db"))
    print("Bootstrapped inventory.db")
