"""
fuzzy.py
--------
Pure-python fuzzy matching and ranking for node search.
No `hou` or Qt imports — unit-testable anywhere.

Scoring tiers (lower is better):
    0.0  exact match (name, base name, or label)
    1.x  prefix of name / base name
    2.x  prefix of label, or prefix of any word token
    3.x  acronym match (first letters of tokens, e.g. "ctp" -> copy to points)
    4.x  substring anywhere in the name
    5.x  substring anywhere in the label
    6.x  ordered subsequence in the name (gap-penalized)
    8.x  alias tier (assigned by the caller, kept above subsequence noise)

Fractional part encodes gap penalties / lengths so ties break sensibly.
"""

import re

_TOKEN_RE = re.compile(r"[a-z0-9]+")

MAX_SCORE = 100.0


def base_name(full_name):
    """
    Strip namespace and version from a node type name.
    'kinefx::rigdoctor'  -> 'rigdoctor'
    'curve::2.0'         -> 'curve'
    'labs::edge_damage::2.0' -> 'edge_damage'
    """
    if "::" not in full_name:
        return full_name
    parts = full_name.split("::")
    # Drop a trailing version component (digits and dots)
    if parts and parts[-1].replace(".", "").isdigit():
        parts = parts[:-1]
    return parts[-1] if parts else full_name


def tokenize(text):
    """Lowercase word tokens: 'Copy to Points' -> ['copy','to','points']."""
    return _TOKEN_RE.findall(text.lower())


def acronym(text):
    """First letters of each token: 'copy to points' -> 'ctp'."""
    return "".join(t[0] for t in tokenize(text))


def subsequence_positions(query, target):
    """
    Greedy ordered subsequence match of `query` inside `target`.
    Returns (positions, gap_penalty) or None. Both strings must be lowercase.
    """
    positions = []
    ti = 0
    gaps = 0
    last = -1
    for ch in query:
        idx = target.find(ch, ti)
        if idx == -1:
            return None
        if last >= 0 and idx > last + 1:
            gaps += 1
        positions.append(idx)
        last = idx
        ti = idx + 1
    return positions, gaps


def _score_single(token, name_l, base_l, label_l):
    """Score one query token against one entry. Returns (score, positions)."""
    # positions refer to indices in the *name* string when applicable
    if token == name_l or token == base_l or token == label_l:
        return 0.0, _substr_positions(name_l, token)
    if name_l.startswith(token) or base_l.startswith(token):
        return 1.0 + len(name_l) * 0.001, _substr_positions(name_l, token)
    if label_l.startswith(token):
        return 2.0, []
    for word in tokenize(label_l) + name_l.replace("::", "_").split("_"):
        if word and word.startswith(token) and word != label_l:
            return 2.2, _substr_positions(name_l, token)
    acr = acronym(label_l)
    if acr and acr.startswith(token) and len(token) >= 2:
        return 3.0, []
    idx = name_l.find(token)
    if idx >= 0:
        return 4.0 + idx * 0.01, list(range(idx, idx + len(token)))
    if token in label_l:
        return 5.0, []
    # Subsequence only for tokens of 3+ chars to avoid noise
    if len(token) >= 3:
        sub = subsequence_positions(token, name_l)
        if sub is not None:
            positions, gaps = sub
            return 6.0 + min(gaps, 20) * 0.05 + len(name_l) * 0.001, positions
    return None, []


def _substr_positions(name_l, token):
    idx = name_l.find(token)
    if idx < 0:
        return []
    return list(range(idx, idx + len(token)))


def score(query, name, label):
    """
    Score a (possibly multi-word) query against a node name + label.
    Returns (score, name_highlight_positions) or (None, []) when no match.
    """
    name_l = name.lower()
    base_l = base_name(name_l)
    label_l = label.lower()

    tokens = query.lower().split()
    if not tokens:
        return 0.0, []

    total = 0.0
    all_positions = []
    for token in tokens:
        s, positions = _score_single(token, name_l, base_l, label_l)
        if s is None:
            return None, []
        total += s
        all_positions.extend(positions)
    # Slight penalty per extra token keeps single-token exact hits on top
    total += (len(tokens) - 1) * 0.1
    return total, sorted(set(all_positions))


# Score assigned per alias-match tier (see aliases.AliasHit). An exact alias
# term ("cloner") must beat every partial direct match — the alias IS the
# user's word for the node — while looser alias matches slot between
# word-prefix matches and subsequence noise.
ALIAS_TIER_SCORES = {0: 0.3, 1: 3.5, 2: 6.5, 3: 7.0}


def _alias_lookup(alias_hits):
    """Normalize {name: AliasHit|term} to a lowercase-keyed dict."""
    return {key.lower(): value for key, value in alias_hits.items()}


def _alias_parts(hit):
    """(term, score) from an AliasHit, tolerating plain-string values."""
    term = getattr(hit, "term", hit)
    tier = getattr(hit, "tier", 2)
    return term, ALIAS_TIER_SCORES.get(tier, 6.5)


def rank(entries, query, alias_hits=None, suggested=(), favorites=(), limit=60):
    """
    Rank index entries against a query.

    entries    : iterable with .name, .label, .base attributes
    query      : raw user text
    alias_hits : {base_or_full_name: AliasHit (or plain term string)} —
                 entries matched via a cross-DCC alias (e.g. 'cloner').
                 Matched case-insensitively against base and full names, so
                 namespaced HDA toolkits (MOPs::Instancer) resolve too.
    suggested  : set of base names that are contextual suggestions (boost)
    favorites  : set of full names that are favorites (small boost)

    Returns list of dicts:
      {entry, score, positions, alias} sorted best-first, capped at limit.
    """
    alias_hits = _alias_lookup(alias_hits) if alias_hits else {}
    suggested = set(suggested)
    favorites = set(favorites)
    query = query.strip()

    results = []
    for entry in entries:
        s, positions = score(query, entry.name, entry.label)
        hit = None
        if alias_hits:
            hit = (alias_hits.get(entry.base.lower())
                   or alias_hits.get(entry.name.lower()))
        alias_term = None
        if hit is not None:
            alias_term, alias_score = _alias_parts(hit)
            # The alias score can only help: an exact alias term outranks a
            # weak direct match, but a strong direct match keeps its score.
            s = alias_score if s is None else min(s, alias_score)
            positions = positions or []
        elif s is None:
            continue

        if entry.base in suggested:
            s -= 0.4
        if entry.name in favorites:
            s -= 0.2

        results.append({
            "entry": entry,
            "score": s,
            "positions": positions,
            "alias": alias_term,
        })

    results.sort(key=lambda r: (r["score"], len(r["entry"].name), r["entry"].name))
    return results[:limit]
