"""
Fuzzy matching logic using rapidfuzz.
Wraps batch and single-query search against the product catalog.
"""
import re
from dataclasses import dataclass, field
from typing import Callable

from rapidfuzz import process, fuzz

AUTO_THRESHOLD  = 90
MAX_SUGGESTIONS = 5

# ── Key cache ──────────────────────────────────────────────────────────────
# Stores (candidates_id, keys_list) so keys are rebuilt only when the
# candidates list object changes between calls.
_key_cache: tuple[int, list[str]] | None = None


@dataclass
class BatchItem:
    input_text     : str
    status         : str            # 'confirmed' | 'review' | 'not_found'
    matched_product: dict | None = None
    score          : int = 0
    suggestions    : list[dict] = field(default_factory=list)
    metadata       : dict = field(default_factory=dict)  # extra info from input line


def parse_batch_line(line: str) -> tuple[str, dict]:
    """
    Parse a single batch input line that may contain tab-separated metadata.

    Supported formats:
        "Lugia VSTAR"
        "Lugia VSTAR 139/195"
        "Lugia VSTAR 139/195\\tIdioma\\tEN\\tRareza\\tDouble Rare"

    Columns after the first are treated as label→value pairs:
        Idioma  EN  Rareza  Double Rare
        → {"idioma": "EN", "rareza": "Double Rare"}

    Returns (card_query, metadata_dict).
    """
    parts = [p.strip() for p in line.split("\t")]
    card_query = parts[0] if parts else ""

    metadata: dict[str, str] = {}
    i = 1
    while i + 1 <= len(parts) - 1:
        key = parts[i].strip().lower()
        val = parts[i + 1].strip()
        if key and val:
            metadata[key] = val
        i += 2

    return card_query, metadata


# ── Normalization ──────────────────────────────────────────────────────────

def normalize(text: str) -> str:
    """
    Normalize a card name string for fuzzy comparison.

    Handles cases like:
      "Lillie's Clefairy ex 76"   → "lillies clefairy ex"
      "Lillie's Clefairy ex 076/217" → "lillies clefairy ex"
      "Pikachu VMAX"              → "pikachu vmax"

    Rules applied (in order):
      1. Lowercase
      2. Remove typographic apostrophes and backticks  (' ' `)
      3. Remove card-number suffixes:
           "076/217", "076 / 217", "76", "076" at the end of the string
      4. Remove remaining punctuation (keep letters, digits, spaces)
      5. Collapse multiple spaces
    """
    if not text:
        return ""
    t = text.lower()
    # 1 – normalize apostrophes  (straight and curly)
    t = t.replace("'", "").replace("\u2019", "").replace("\u2018", "").replace("`", "")
    # 2 – remove card number at end: "076/217", "076 / 217", " 76"
    t = re.sub(r"\s+\d{1,4}\s*/\s*\d{1,4}\s*$", "", t)   # e.g.  076/217
    t = re.sub(r"\s+0*\d{1,3}\s*$", "", t)                # e.g.  76  or  076
    # 3 – strip remaining punctuation
    t = re.sub(r"[^\w\s]", " ", t)
    # 4 – collapse whitespace
    return re.sub(r"\s+", " ", t).strip()


def normalize_for_sql(text: str) -> str:
    """
    Like normalize() but keeps apostrophes stripped so SQL LIKE can match
    against the `cleanName` column (which already has them removed).
    Returns the normalized string suitable for a LIKE %…% query.
    """
    return normalize(text)


def _choice_key(p: dict) -> str:
    """Normalized string used for fuzzy matching against a candidate product."""
    base = p.get("cleanName") or p.get("name") or ""
    return normalize(base)


def search_single(query: str, candidates: list[dict],
                  prebuilt_keys: list[str] | None = None) -> list[tuple[dict, int]]:
    """
    Search one query against all candidates.
    Pass `prebuilt_keys` to reuse a pre-computed key list (avoids rebuilding it).
    Returns [(product_dict, score), ...] sorted best-first, up to MAX_SUGGESTIONS.
    """
    keys    = prebuilt_keys if prebuilt_keys is not None else [_choice_key(c) for c in candidates]
    results = process.extract(
        normalize(query), keys, scorer=fuzz.token_sort_ratio, limit=MAX_SUGGESTIONS
    )
    return [(candidates[idx], int(score)) for _, score, idx in results]


def _get_keys(candidates: list[dict]) -> list[str]:
    """Return normalized keys, rebuilding only when candidates list changes."""
    global _key_cache
    cid = id(candidates)
    if _key_cache is None or _key_cache[0] != cid:
        _key_cache = (cid, [_choice_key(c) for c in candidates])
    return _key_cache[1]


# ── Number-based lookup ────────────────────────────────────────────────────
# Cache: (candidates_id, number_index)
_num_index_cache: tuple[int, dict] | None = None

_RE_NUMBER_FULL = re.compile(r'\b(\d{1,4})\s*/\s*(\d{1,4})\b')   # 123/162
_RE_NUMBER_BARE = re.compile(r'(?<!\d)(\d{2,4})(?!\d)')           # 141, 025


def _extract_query_number(raw: str) -> str | None:
    """
    Extract the card number from a raw query string (before normalization).
    Returns a canonical "NNN/MMM" or "NNN" string, or None if not present.
    """
    m = _RE_NUMBER_FULL.search(raw)
    if m:
        return f"{int(m.group(1)):03d}/{int(m.group(2)):03d}"
    # Bare number only at end: "Noctowl 141"
    m = re.search(r'\s+(\d{2,4})\s*$', raw)
    if m:
        return f"{int(m.group(1)):03d}"
    return None


def _normalize_extnum(ext: str | None) -> str | None:
    """Canonicalize an extNumber from the DB for index lookup."""
    if not ext:
        return None
    ext = ext.strip()
    m = _RE_NUMBER_FULL.search(ext)
    if m:
        return f"{int(m.group(1)):03d}/{int(m.group(2)):03d}"
    m = re.fullmatch(r'\d{1,4}', ext)
    if m:
        return f"{int(ext):03d}"
    return None


def _get_number_index(candidates: list[dict]) -> dict[str, list[dict]]:
    """
    Build (or return cached) number → candidates index.
    Each candidate is indexed by:
      - full "NNN/MMM" key  (e.g. "123/162")
      - short "NNN" key     (e.g. "123") for queries that omit the total
    """
    global _num_index_cache
    cid = id(candidates)
    if _num_index_cache is not None and _num_index_cache[0] == cid:
        return _num_index_cache[1]

    index: dict[str, list[dict]] = {}
    for c in candidates:
        norm = _normalize_extnum(c.get("extNumber"))
        if not norm:
            continue
        index.setdefault(norm, []).append(c)
        short = norm.split("/")[0]       # "123" from "123/162"
        if short != norm:
            index.setdefault(short, []).append(c)

    _num_index_cache = (cid, index)
    return index


def _best_by_number(raw_query: str, candidates: list[dict]) -> tuple[dict, int] | None:
    """
    Two-phase lookup:
      1. Extract card number from raw_query.
      2. Find candidates with that exact extNumber.
      3. Among those, pick the one with best name similarity.
      4. Return (best_candidate, score) if name similarity ≥ 50, else None.

    Score mapping:
      name_sim ≥ 85  →  100  (confirmed)
      name_sim ≥ 70  →   95  (confirmed)
      name_sim ≥ 50  →   85  (review)
    """
    num = _extract_query_number(raw_query)
    if not num:
        return None

    index = _get_number_index(candidates)
    hits  = index.get(num)
    if not hits:
        return None

    norm_name = normalize(raw_query)
    best_hit, best_sim = max(
        # Use normalize(name) — strips trailing numbers like "- 160/217"
        ((h, fuzz.token_sort_ratio(norm_name, normalize(h.get("name") or ""))) for h in hits),
        key=lambda x: x[1],
    )

    if best_sim < 50:
        return None

    if best_sim >= 85:
        score = 100
    elif best_sim >= 70:
        score = 95
    else:
        score = 85

    return best_hit, score


def batch_search(
    queries    : list[str],
    candidates : list[dict],
    progress_cb: Callable[[int, int, str], None] | None = None,
) -> list[BatchItem]:
    """
    Process all queries in one parallelized operation using process.cdist.

    Strategy:
      1. Normalize all queries and build candidate keys ONCE.
      2. Call process.cdist(queries, keys, workers=-1) — rapidfuzz uses all
         CPU cores internally via C-level threading, no GIL contention.
      3. For each query row in the score matrix, extract the top-K matches.

    This is 10-50x faster than sequential extract() calls for large lists.
    Falls back to per-query extract() for very large query sets (>500) to
    avoid excessive memory usage.
    """
    # Filter empty/whitespace lines, keep original text for display
    valid: list[tuple[str, str]] = []   # (original_text, normalized_text)
    for q in queries:
        stripped = q.strip()
        if stripped:
            valid.append((stripped, normalize(stripped)))

    if not valid:
        return []

    total = len(valid)

    # ── Step 1: build candidate keys once (cached) ───────────────────────
    if progress_cb:
        progress_cb(0, total, f"Preparando {total} consultas contra {len(candidates):,} productos…")

    keys = _get_keys(candidates)

    # ── Step 2: score matrix (parallel, all CPUs) ─────────────────────────
    norm_queries = [nq for _, nq in valid]

    if progress_cb:
        progress_cb(0, total,
                    f"Calculando {total} × {len(candidates):,} scores en paralelo…")

    if total <= 500:
        # Bulk path: one C-level parallel call, returns numpy array
        # shape → (len(norm_queries), len(candidates))
        score_matrix = process.cdist(
            norm_queries, keys,
            scorer=fuzz.token_sort_ratio,   # faster than WRatio, sufficient for card names
            workers=-1,                      # all CPU cores
        )
        _use_matrix = True
    else:
        _use_matrix = False

    # ── Step 3: extract top-K per query ───────────────────────────────────
    items: list[BatchItem] = []

    for i, (orig_text, norm_text) in enumerate(valid):
        if progress_cb and (i % max(1, total // 20) == 0 or i == total - 1):
            progress_cb(i + 1, total, orig_text)

        # ── Phase 1: number-based exact lookup ──────────────────────────
        # If the query contains a card number (e.g. 123/162 or bare 141),
        # try to find a candidate with that exact extNumber first.
        # This prevents false 100% matches on same-name / different-number cards.
        num_result = _best_by_number(orig_text, candidates)
        if num_result:
            best_product, best_score = num_result
            # Build suggestions: start with number match, then add name matches
            if _use_matrix:
                row     = score_matrix[i]
                top_idx = row.argsort()[::-1][:MAX_SUGGESTIONS]
                name_matches = [(candidates[j], int(row[j])) for j in top_idx if row[j] > 0]
            else:
                name_matches = search_single(orig_text, candidates, prebuilt_keys=keys)

            suggestions = [{"product": best_product, "score": best_score}]
            for p, s in name_matches:
                if p.get("productId") != best_product.get("productId"):
                    suggestions.append({"product": p, "score": s})
            suggestions = suggestions[:MAX_SUGGESTIONS]

            items.append(BatchItem(
                input_text      = orig_text,
                status          = "confirmed" if best_score >= AUTO_THRESHOLD else "review",
                matched_product = best_product,
                score           = best_score,
                suggestions     = suggestions,
            ))
            continue

        # ── Phase 2: name-only fuzzy (fallback when no number in query) ──
        if _use_matrix:
            row      = score_matrix[i]
            top_idx  = row.argsort()[::-1][:MAX_SUGGESTIONS]
            matches  = [(candidates[j], int(row[j])) for j in top_idx if row[j] > 0]
        else:
            matches = search_single(orig_text, candidates, prebuilt_keys=keys)

        if not matches:
            items.append(BatchItem(input_text=orig_text, status="not_found"))
            continue

        best_product, best_score = matches[0]
        suggestions = [{"product": p, "score": s} for p, s in matches]

        items.append(BatchItem(
            input_text      = orig_text,
            status          = "confirmed" if best_score >= AUTO_THRESHOLD else "review",
            matched_product = best_product,
            score           = best_score,
            suggestions     = suggestions,
        ))

    return items
