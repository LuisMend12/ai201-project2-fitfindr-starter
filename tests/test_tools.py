from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


def test_search_returns_results():
    results = search_listings("vintage graphic tee", size=None, max_price=50)
    assert isinstance(results, list)
    assert len(results) > 0


def test_search_empty_results():
    results = search_listings("designer ballgown", size="XXS", max_price=5)
    assert results == []  # empty list, no exception


def test_search_price_filter():
    results = search_listings("jacket", size=None, max_price=50)
    assert all(item["price"] <= 50 for item in results)


def test_search_size_filter():
    results = search_listings("tee", size="M", max_price=None)
    assert all("m" in item["size"].lower() for item in results)


def test_search_top_result_matches_description():
    results = search_listings("vintage graphic tee", size=None, max_price=30.0)
    assert results[0]["id"] == "lst_006"


def test_suggest_outfit_with_wardrobe_names_items():
    item = search_listings("vintage graphic tee", size=None, max_price=30.0)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    assert isinstance(outfit, str)
    assert outfit.strip() != ""


def test_suggest_outfit_with_empty_wardrobe_does_not_crash():
    item = search_listings("vintage graphic tee", size=None, max_price=30.0)[0]
    outfit = suggest_outfit(item, get_empty_wardrobe())
    assert isinstance(outfit, str)
    assert outfit.strip() != ""


def test_create_fit_card_returns_nonempty_string():
    item = search_listings("vintage graphic tee", size=None, max_price=30.0)[0]
    outfit = suggest_outfit(item, get_example_wardrobe())
    card = create_fit_card(outfit, item)
    assert isinstance(card, str)
    assert card.strip() != ""


def test_create_fit_card_handles_empty_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=30.0)[0]
    card = create_fit_card("", item)
    assert isinstance(card, str)
    assert card.strip() != ""


def test_create_fit_card_handles_whitespace_outfit():
    item = search_listings("vintage graphic tee", size=None, max_price=30.0)[0]
    card = create_fit_card("   ", item)
    assert isinstance(card, str)
    assert card.strip() != ""
