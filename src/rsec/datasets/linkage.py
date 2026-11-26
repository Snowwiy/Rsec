"""Bounded lexical/code linkage plus explicit provenance and translation families."""

import re
from collections import defaultdict

from rsec.datasets.quality import normalize
from rsec.errors import RsecError
from rsec.utils import digest


def prompt_text(row):
    return normalize("\n".join(m.content for m in row.messages if m.role == "user"))


def code_fingerprint(code):
    # Whitespace/comment-only variants link across languages where this conservative lexer applies.
    if not code:
        return None
    return digest(re.sub(r"\s+", "", re.sub(r"(?m)^\s*(#|//).*$", "", code)))


def shingles(text):
    words = re.findall(r"\w+", text)
    if len(words) > 12000:
        raise RsecError("Lexical token budget exceeded")
    return {tuple(words[i : i + 3]) for i in range(max(1, len(words) - 2))}


def related(rows, max_pairs=200000):
    parent = list(range(len(rows)))
    members = {}
    postings = defaultdict(list)
    features = []
    links = []
    pairs = set()

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j, reason):
        a, b = root(i), root(j)
        if a != b:
            parent[max(a, b)] = min(a, b)
            links.append({"a": rows[i].id, "b": rows[j].id, "reason": reason})

    for i, row in enumerate(rows):
        keys = ["origin:" + row.origin_id, *["family:" + v for v in row.families]]
        if row.translation_of:
            keys += ["id:" + row.translation_of]
        keys += ["id:" + row.id]
        fp = code_fingerprint(row.code)
        if fp:
            keys += ["code:" + fp]
        for key in keys:
            if key in members:
                union(i, members[key], "provenance_translation_or_code")
            else:
                members[key] = i
        s = shingles(prompt_text(row))
        features.append(s)
        candidates = set(j for word in s for j in postings[word])
        for j in sorted(candidates):
            pair = (j, i)
            if pair in pairs:
                continue
            pairs.add(pair)
            if len(pairs) > max_pairs:
                raise RsecError("Similarity candidate budget exceeded; shard by reviewed families")
            other = features[j]
            if len(s & other) / max(1, len(s | other)) >= 0.75:
                union(i, j, "lexical_prompt_similarity")
        for word in s:
            postings[word].append(i)
    # Forward translation_of references need resolution after all IDs are known.
    by_id = {r.id: i for i, r in enumerate(rows)}
    for i, r in enumerate(rows):
        if r.translation_of and r.translation_of in by_id:
            union(i, by_id[r.translation_of], "translation")
    groups = defaultdict(list)
    for i in range(len(rows)):
        groups[root(i)].append(i)
    return list(groups.values()), links


def contamination(candidates, reserved):
    combined = [*candidates, *reserved]
    groups, links = related(combined)
    polluted = set()
    offset = len(candidates)
    for group in groups:
        if any(i >= offset for i in group):
            polluted.update(combined[i].id for i in group if i < offset)
    return {
        "contaminated_ids": sorted(polluted),
        "candidate_records": len(candidates),
        "reserved_records": len(reserved),
        "link_count": len(links),
        "limits": "Provenance/translation IDs, lexical overlap and whitespace-normalized code; no universal semantic or cross-language detector",
    }


def approximate_duplicates(rows, max_pairs=200000):
    """Remove near prompts only when language, evidence and target answer also agree."""
    buckets = defaultdict(list)
    removed = set()
    comparisons = 0
    for row in rows:
        key = (row.language, normalize(row.evidence), normalize(row.messages[-1].content))
        current = shingles(prompt_text(row))
        for other in buckets[key]:
            comparisons += 1
            if comparisons > max_pairs:
                raise RsecError("Approximate deduplication budget exceeded")
            if len(current & other) / max(1, len(current | other)) >= 0.92:
                removed.add(row.id)
                break
        if row.id not in removed:
            buckets[key].append(current)
    return removed
