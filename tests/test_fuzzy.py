"""
Tests for fuzzy matching — search_single() and batch_search().
"""
import pytest
from app.core.fuzzy import batch_search, search_single, BatchItem, AUTO_THRESHOLD
from tests.conftest import FUZZY_CANDIDATES


# ── search_single ──────────────────────────────────────────────────────────

def test_exact_match_returns_first():
    results = search_single("Lugia VSTAR", FUZZY_CANDIDATES)
    assert results, "Expected at least one result"
    assert results[0][0]["productId"] == 451396
    assert results[0][1] >= AUTO_THRESHOLD


def test_apostrophe_normalized():
    results = search_single("Lillie's Clefairy ex", FUZZY_CANDIDATES)
    assert results[0][0]["productId"] == 999001
    assert results[0][1] >= AUTO_THRESHOLD


def test_card_number_stripped():
    for query in ("Lillie's Clefairy ex 76",
                  "Lillie's Clefairy ex 076/217",
                  "lillies clefairy ex"):
        results = search_single(query, FUZZY_CANDIDATES)
        assert results[0][0]["productId"] == 999001, f"Failed for query: {query!r}"
        assert results[0][1] >= AUTO_THRESHOLD


def test_case_insensitive():
    results = search_single("LUGIA VSTAR", FUZZY_CANDIDATES)
    assert results[0][0]["productId"] == 451396


def test_returns_at_most_max_suggestions():
    from app.core.fuzzy import MAX_SUGGESTIONS
    results = search_single("Charizard ex", FUZZY_CANDIDATES)
    assert len(results) <= MAX_SUGGESTIONS


# ── batch_search ───────────────────────────────────────────────────────────

def test_batch_exact_matches_auto_confirmed():
    items = batch_search(
        ["Lugia VSTAR", "Charizard ex"],
        FUZZY_CANDIDATES,
    )
    assert len(items) == 2
    assert all(i.status == "confirmed" for i in items)


def test_batch_normalization_end_to_end():
    items = batch_search(
        ["Lillie's Clefairy ex 076/217"],
        FUZZY_CANDIDATES,
    )
    assert len(items) == 1
    assert items[0].matched_product["productId"] == 999001
    assert items[0].status == "confirmed"


def test_batch_skips_empty_lines():
    items = batch_search(
        ["Lugia VSTAR", "", "   ", "Charizard ex"],
        FUZZY_CANDIDATES,
    )
    assert len(items) == 2


def test_batch_preserves_original_input_text():
    query = "Lillie's Clefairy ex 76"
    items = batch_search([query], FUZZY_CANDIDATES)
    assert items[0].input_text == query    # original text, not normalized


def test_batch_not_found_for_gibberish():
    items = batch_search(["xyzthisisnotacardxyz123"], FUZZY_CANDIDATES)
    assert len(items) == 1
    assert items[0].status in ("review", "not_found")


def test_batch_suggestions_populated():
    items = batch_search(["Lugia VSTAR"], FUZZY_CANDIDATES)
    assert items[0].suggestions
    assert items[0].suggestions[0]["product"]["productId"] == 451396


def test_batch_empty_list_returns_empty():
    items = batch_search([], FUZZY_CANDIDATES)
    assert items == []


def test_batch_progress_callback_called():
    calls = []
    batch_search(
        ["Lugia VSTAR", "Charizard ex"],
        FUZZY_CANDIDATES,
        progress_cb=lambda c, t, q: calls.append((c, t, q)),
    )
    # At least one call was made
    assert len(calls) >= 1
