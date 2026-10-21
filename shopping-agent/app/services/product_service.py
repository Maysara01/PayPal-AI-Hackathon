import math
import re
from typing import Optional

from app.repositories.product_repository import ProductRepository

# A number such as 600, 600.50 or 1,200. The comma form is tried first so
# "1,200" is not read as "1".
_NUMBER = r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)"

# One money amount: optional "$", the number, optional "USD"/"dollars".
# The lookaheads stop the match when the number is really something else,
# e.g. "16GB", "15 inch", "10 hours".
# Groups: (1) "$" marker, (2) number, (3) USD/dollars marker.
_MONEY = (
    r"(\$)?\s*" + _NUMBER + r"(\s*(?:usd|dollars?))?"
    r"(?!\.?\d)"
    r"(?!\s*(?:(?:gb|tb|mb|kg|hz|mah|inch(?:es)?|hrs?|hours?)\b|%))"
)

# "between $400 and $600", "from $400 to $600", "$400-$600" after between/from.
_RANGE_RE = re.compile(
    r"\b(?:between|from)\s+" + _MONEY + r"(?:\s+(?:and|to)\s+|\s*[-–]\s*)" + _MONEY
)

# Words that explicitly state an upper limit on price.
_CAP_RE = re.compile(
    r"\b(?:under|below|less\s+than|up\s+to|at\s+most|"
    r"(?:maximum|max|budget)(?:\s+(?:of|is))?)\s*:?\s*" + _MONEY
)


def _to_float(number: str) -> float:
    return float(number.replace(",", ""))


class ProductService:
    def __init__(self):
        self.repository = ProductRepository()

    @staticmethod
    def extract_budget(text: str) -> tuple[Optional[float], Optional[float]]:
        """Return (min_price, max_price) found in a query; None means no limit.

        Only explicit price phrasing counts. A bare "$600" is ambiguous and
        is NOT treated as a budget. Limits are inclusive.
        """
        text = text.lower()

        # Ranges first, so the first amount is never mistaken for the maximum.
        # A range needs a currency marker on at least one amount so that
        # "between 8 and 16" is not read as a price.
        for match in _RANGE_RE.finditer(text):
            has_marker = any(match.group(i) for i in (1, 3, 4, 6))
            if not has_marker:
                continue
            low, high = _to_float(match.group(2)), _to_float(match.group(5))
            if low > high:
                low, high = high, low
            return low, high

        # Otherwise explicit "under / below / up to / max / budget" caps.
        # If several are given, the most restrictive one wins.
        caps = [_to_float(m.group(2)) for m in _CAP_RE.finditer(text)]
        if caps:
            return None, min(caps)

        return None, None

    @staticmethod
    def _parse_price(value) -> Optional[float]:
        """Return a usable positive price, or None if it is missing/invalid."""
        if value is None or isinstance(value, bool):
            return None
        try:
            price = float(value.strip() if isinstance(value, str) else value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(price) or price <= 0:
            return None
        return price

    def search(self, query: str) -> list[dict]:
        products = self.repository.get_all()
        text = query.lower()
        min_price, max_price = self.extract_budget(text)
        has_budget = min_price is not None or max_price is not None

        # Detect broad product category.
        wants_laptop = any(
            word in text for word in ["laptop", "computer", "notebook"]
        )
        wants_headphones = any(
            word in text for word in ["headphones", "headphone", "earphones"]
        )

        results = []

        for product in products:
            name = (product.get("name") or "").lower()
            specs = product.get("specs") or {}
            searchable = f"{name} {' '.join(str(v).lower() for v in specs.values())}"

            if wants_laptop and not any(
                word in searchable for word in ["laptop", "computer", "notebook"]
            ):
                continue

            if wants_headphones and not any(
                word in searchable for word in ["headphones", "headphone", "earphones"]
            ):
                continue

            # This demo catalog uses USD prices. Without explicit, correct
            # currency conversion, anything that is not USD is excluded.
            if has_budget:
                currency = product.get("currency")
                if not isinstance(currency, str) or currency.strip().upper() != "USD":
                    continue

                price = self._parse_price(product.get("price"))
                if price is None:
                    continue
                if min_price is not None and price < min_price:
                    continue
                if max_price is not None and price > max_price:
                    continue

            results.append(product)

        return results