"""
Tests for fuzzy.normalize() — the card name normalization function.
"""
import pytest
from app.core.fuzzy import normalize


@pytest.mark.parametrize("inp, expected", [
    # Apostrophes (straight and curly)
    ("Lillie's Clefairy ex",         "lillies clefairy ex"),
    ("Lillie\u2019s Clefairy ex",    "lillies clefairy ex"),   # curly apostrophe
    # Card number at end  — NNN/MMM format
    ("Lillie's Clefairy ex 076/217", "lillies clefairy ex"),
    ("Lugia VSTAR 139/195",          "lugia vstar"),
    ("Charizard ex 199/165",         "charizard ex"),
    # Card number at end  — bare number
    ("Lillie's Clefairy ex 76",      "lillies clefairy ex"),
    ("Pikachu VMAX 44",              "pikachu vmax"),
    # Leading zeros in bare number
    ("Gengar VMAX 057",              "gengar vmax"),
    # No change cases
    ("Pikachu VMAX",                 "pikachu vmax"),
    ("Arceus VSTAR",                 "arceus vstar"),
    # Edge cases
    ("",                             ""),
    ("   spaces   ",                 "spaces"),
    # Punctuation removal — & and - become spaces, final whitespace is collapsed
    ("Mewtwo & Mew-GX",             "mewtwo mew gx"),
    # Number that is NOT a card code (not at the end preceded by space)
    ("151 Venusaur ex",              "151 venusaur ex"),
])
def test_normalize(inp, expected):
    assert normalize(inp) == expected
