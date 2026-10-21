import pytest

from app.services.product_service import ProductService


class FakeRepository:
    def __init__(self, products):
        self._products = products

    def get_all(self):
        return self._products


def make_product(pid, name="Laptop", price=500, currency="USD", **extra):
    product = {"id": pid, "name": name, "currency": currency, "specs": {}}
    if price is not ...:
        product["price"] = price
    product.update(extra)
    return product


def search_ids(query, products):
    service = ProductService()
    service.repository = FakeRepository(products)
    return [p["id"] for p in service.search(query)]


# --- budget extraction -----------------------------------------------------

@pytest.mark.parametrize(
    "query, expected",
    [
        ("Find a laptop under $600", (None, 600.0)),
        ("Find a laptop below $600", (None, 600.0)),
        ("Find a laptop less than $600", (None, 600.0)),
        ("Find a laptop up to $600", (None, 600.0)),
        ("Find a laptop maximum $600", (None, 600.0)),
        ("Find a laptop max $600", (None, 600.0)),
        ("Find a laptop budget of $600", (None, 600.0)),
        ("Find a laptop budget: $600", (None, 600.0)),
        ("Find a laptop under 600 USD", (None, 600.0)),
        ("Find a laptop below 600 usd", (None, 600.0)),
        ("Find a laptop under $1,200", (None, 1200.0)),
        ("Find a laptop under $599.99", (None, 599.99)),
        ("Find a laptop between $400 and $600", (400.0, 600.0)),
        ("Find a laptop from $400 to $600", (400.0, 600.0)),
        ("Find a laptop between 400 and 600 USD", (400.0, 600.0)),
        ("Find a laptop between $600 and $400", (400.0, 600.0)),  # reversed
        ("Find a laptop from $400-$600", (400.0, 600.0)),
        # most restrictive cap wins when several are given
        ("laptop under $800, ideally under $600", (None, 600.0)),
    ],
)
def test_extract_budget(query, expected):
    assert ProductService.extract_budget(query) == expected


@pytest.mark.parametrize(
    "query",
    [
        "Find a laptop",
        "Find a laptop $600",            # bare amount is ambiguous
        "Find a laptop with $600 coupon",
        "Find a laptop under 16GB",      # unit, not a price
        "Find a laptop between 8 and 16",  # no currency marker
        "Find a laptop from 8 to 16 GB",
        "Find a laptop from $400",       # not a range, no cap word
    ],
)
def test_extract_budget_ignores_ambiguous_amounts(query):
    assert ProductService.extract_budget(query) == (None, None)


def test_range_first_amount_is_not_the_maximum():
    low, high = ProductService.extract_budget("laptop between $400 and $600")
    assert (low, high) == (400.0, 600.0)
    assert high != low


# --- price ranges and caps in search ---------------------------------------

CATALOG = [
    make_product("laptop-350", price=350),
    make_product("laptop-001", price=499),
    make_product("laptop-002", price=799),
]


def test_under_600_includes_499_excludes_799():
    ids = search_ids("Find a laptop under $600", CATALOG)
    assert "laptop-001" in ids
    assert "laptop-002" not in ids


def test_between_400_and_600_enforces_both_bounds():
    assert search_ids("Find a laptop between $400 and $600", CATALOG) == ["laptop-001"]


def test_from_400_to_600_enforces_both_bounds():
    assert search_ids("Find a laptop from $400 to $600", CATALOG) == ["laptop-001"]


def test_bounds_are_inclusive():
    products = [make_product("a", price=400), make_product("b", price=600)]
    assert search_ids("laptop between $400 and $600", products) == ["a", "b"]


def test_no_budget_returns_all_matching_category():
    assert search_ids("Find a laptop", CATALOG) == [
        "laptop-350", "laptop-001", "laptop-002",
    ]


def test_ambiguous_dollar_amount_does_not_filter():
    assert search_ids("Find a laptop $600", CATALOG) == [
        "laptop-350", "laptop-001", "laptop-002",
    ]


# --- category filtering ----------------------------------------------------

def test_category_filter_laptops_only():
    products = [
        make_product("l1", name="Student Laptop", price=499),
        make_product("h1", name="Wireless Headphones", price=99),
    ]
    assert search_ids("laptop under $600", products) == ["l1"]


def test_category_filter_headphones_only():
    products = [
        make_product("l1", name="Student Laptop", price=499),
        make_product("h1", name="Wireless Headphones", price=99),
        make_product("h2", name="Studio Headphones", price=299),
    ]
    assert search_ids("headphones between $100 and $400", products) == ["h2"]


def test_category_detected_from_specs():
    products = [make_product("n1", name="Zen", price=499, specs={"type": "notebook"})]
    assert search_ids("laptop under $600", products) == ["n1"]


def test_product_with_null_name_and_specs_does_not_crash():
    products = [make_product("x", name=None, price=499, specs=None)]
    assert search_ids("under $600", products) == ["x"]


# --- missing / invalid prices ----------------------------------------------

def test_missing_price_is_excluded_by_budget():
    products = [make_product("ok", price=499), make_product("nop", price=...)]
    assert search_ids("laptop under $600", products) == ["ok"]


@pytest.mark.parametrize(
    "bad_price",
    [None, "", "   ", "abc", "$499", "499 USD", "nan", "inf", float("nan"),
     float("inf"), float("-inf"), -5, 0, "-1", True, False, [], {}, "1e999"],
)
def test_invalid_price_is_excluded_by_under(bad_price):
    products = [make_product("bad", price=bad_price)]
    assert search_ids("laptop under $600", products) == []


@pytest.mark.parametrize("bad_price", [None, "abc", float("nan"), -5, 0, True])
def test_invalid_price_is_excluded_by_range(bad_price):
    products = [make_product("bad", price=bad_price)]
    assert search_ids("laptop between $400 and $600", products) == []


@pytest.mark.parametrize("good_price", [499, 499.0, "499", "499.00", " 499 "])
def test_valid_price_formats_are_accepted(good_price):
    products = [make_product("ok", price=good_price)]
    assert search_ids("laptop under $600", products) == ["ok"]


def test_invalid_price_still_listed_when_no_budget():
    products = [make_product("bad", price="abc")]
    assert search_ids("Find a laptop", products) == ["bad"]


# --- currency handling -----------------------------------------------------

@pytest.mark.parametrize("currency", ["EUR", "GBP", "MAD", "", None, 840, "US"])
def test_non_usd_is_excluded_by_budget(currency):
    products = [make_product("x", price=100, currency=currency)]
    assert search_ids("laptop under $600", products) == []
    assert search_ids("laptop between $50 and $600", products) == []


def test_missing_currency_is_excluded_by_budget():
    product = make_product("x", price=100)
    del product["currency"]
    assert search_ids("laptop under $600", [product]) == []


@pytest.mark.parametrize("currency", ["USD", "usd", " USD "])
def test_usd_in_any_case_is_accepted(currency):
    products = [make_product("x", price=100, currency=currency)]
    assert search_ids("laptop under $600", products) == ["x"]


def test_non_usd_not_compared_as_usd_even_when_numerically_cheaper():
    products = [
        make_product("eur", price=100, currency="EUR"),
        make_product("usd", price=499, currency="USD"),
    ]
    assert search_ids("laptop under $600", products) == ["usd"]


def test_non_usd_still_listed_when_no_budget():
    products = [make_product("eur", price=100, currency="EUR")]
    assert search_ids("Find a laptop", products) == ["eur"]


# --- stand-in catalog sanity (uses the real repository class) ---------------

def test_default_repository_end_to_end():
    service = ProductService()
    ids_under = [p["id"] for p in service.search("Find a laptop under $600")]
    ids_range = [p["id"] for p in service.search("Find a laptop between $400 and $600")]
    assert "laptop-001" in ids_under and "laptop-002" not in ids_under
    assert "laptop-001" in ids_range and "laptop-002" not in ids_range