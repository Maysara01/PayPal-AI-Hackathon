
import json
from pathlib import Path


DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "demo_products.json"
)


class ProductRepository:
    def get_all(self) -> list[dict]:
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    def get_by_id(self, product_id: str) -> dict | None:
        for product in self.get_all():
            if product["id"] == product_id:
                return product
        return None
