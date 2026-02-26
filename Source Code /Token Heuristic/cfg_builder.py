# cfg_builder.py
# ------------------------------------------------------------
# Updated to better match the paper's CFG output:
#  1) Uses ONE global counter across all extracted keywords.
#     (Matches: if1, ifexp1, elif2, elifexp2, elif3, elifexp3, else4)
#  2) Removes "print" as a CFG keyword (paper's CFG doesn't include prints).
#  3) Generates if/elif/else edges in the same style as the paper:
#       ifN  -> ifexpN
#       ifN  -> next branch keyword (elif/else/end)
#       elifN -> elifexpN
#       elifN -> next branch keyword (elif/else/end)
#       *expN -> end
#       elseN -> end
#  4) Keeps your for/while sections largely as-is.
# ------------------------------------------------------------

from __future__ import annotations
from typing import List, Tuple, Dict
from collections import defaultdict
import re

KEYWORDS = ["if", "elif", "else", "for", "while"]  # print removed


def indent_level(line: str) -> int:
    """Count leading spaces (tabs treated as 4 spaces)."""
    line = line.replace("\t", " " * 4)
    return len(line) - len(line.lstrip(" "))


def extract_keyword(line: str) -> tuple[str | None, str | None]:
    """
    Return (keyword, remainder) if line begins with a supported keyword,
    else (None, None).
    """
    s = line.strip()
    for kw in KEYWORDS:
        if s.startswith(kw):
            return kw, s[len(kw):].strip()
    return None, None


def build_listM(source: str) -> List[str]:
    """
    Paper-style keyword list building with ONE global counter:

      count = 0
      when keyword appears:
        - if / elif: add kw<count> and kwexp<count>
        - else / for / while: add kw<count>
        - if nested: add 'sp' in the keyword label (and 'spexp' for exp nodes)

    Then add start/end.

    IMPORTANT:
    - print statements are ignored (paper doesn't include them)
    - nesting inferred via indentation stack
    """
    lines = source.splitlines()
    listM: List[str] = []

    # global counter (matches paper)
    count = 0

    # Stack holds active blocks (indent_level, label)
    stack: list[tuple[int, str]] = []

    for line in lines:
        if not line.strip():
            continue

        kw, _rest = extract_keyword(line)
        lvl = indent_level(line)

        # pop blocks that ended
        while stack and lvl <= stack[-1][0]:
            stack.pop()

        nested = bool(stack)

        if kw is None:
            continue

        # increment global count for EVERY extracted keyword occurrence
        count += 1

        if kw in ("if", "elif"):
            if not nested:
                label = f"{kw}{count}"
                explabel = f"{kw}exp{count}"
            else:
                label = f"{kw}sp{count}"
                explabel = f"{kw}spexp{count}"

            listM.append(label)
            listM.append(explabel)
            stack.append((lvl, label))

        elif kw == "else":
            label = f"else{count}" if not nested else f"elsesp{count}"
            listM.append(label)
            stack.append((lvl, label))

        elif kw in ("for", "while"):
            label = f"{kw}{count}" if not nested else f"{kw}sp{count}"
            listM.append(label)
            stack.append((lvl, label))

    listM.insert(0, "start")
    listM.append("end")
    return listM


def create_nodes(listM: List[str]) -> List[str]:
    """Create nodes for all items in list (unique, preserve order)."""
    return list(dict.fromkeys(listM))


def _is_plain_if(token: str) -> bool:
    return re.fullmatch(r"if\d+", token) is not None


def _is_plain_elif(token: str) -> bool:
    return re.fullmatch(r"elif\d+", token) is not None


def _is_plain_else(token: str) -> bool:
    return re.fullmatch(r"else\d+", token) is not None


def _is_plain_exp(token: str) -> bool:
    # matches ifexpN or elifexpN
    return re.fullmatch(r"(ifexp|elifexp)\d+", token) is not None


def _is_branch_kw(token: str) -> bool:
    # next branch keyword in paper diagram is either elifN, elseN, or end
    return _is_plain_elif(token) or _is_plain_else(token) or token == "end"


def generate_cfg(listM: List[str]) -> tuple[List[str], List[Tuple[str, str]], List[str], Dict[str, int]]:
    """
    Generates CFG edges.

    Key change (to match paper):
    - For non-nested if/elif/else tokens, build edges exactly like the paper’s example.
    - Then fall back to your original loop logic for loops/nested cases.
    """
    nodes = create_nodes(listM)
    edges: List[Tuple[str, str]] = []

    # Always connect start -> first node
    if len(listM) >= 2:
        edges.append((listM[0], listM[1]))

    # Used for pseudo-like bookkeeping
    list3: List[str] = []
    i = 1

    st = None
    en = None
    stfor = None
    enfor = None

    # --- Paper-style handling for top-level if/elif/else chains (non-nested) ---
    # This is what fixes your diagram mismatch.
    while i < len(listM) - 1:
        cur = listM[i]
        nxt = listM[i + 1] if i + 1 < len(listM) else None

        # IMPORTANT: exp nodes should NOT fall through to next tokens.
        # In the paper, ifexp/elifexp connect to end only.
        if _is_plain_exp(cur):
            i += 1
            continue

        # PAPER: ifN / elifN: connect to its exp node and to next branch keyword
        if (_is_plain_if(cur) or _is_plain_elif(cur)) and nxt and _is_plain_exp(nxt):
            # cur -> exp
            edges.append((cur, nxt))
            list3.extend([cur, nxt])

            # find next branch after exp (elif/else/end)
            j = i + 2
            next_branch = None
            while j < len(listM):
                if _is_branch_kw(listM[j]):
                    next_branch = listM[j]
                    break
                j += 1

            if next_branch is not None:
                edges.append((cur, next_branch))
                list3.append(next_branch)

            # exp -> end
            edges.append((nxt, "end"))

            i += 1
            continue

        # PAPER: elseN -> end
        if _is_plain_else(cur):
            edges.append((cur, "end"))
            list3.append(cur)
            i += 1
            continue

        # --- Keep your existing logic for loops/nested tokens ---
        nxt2 = listM[i + 2] if i + 2 < len(listM) else None

        # forsp
        if cur.startswith("forsp"):
            edges.append((cur, cur))
            if i - 1 >= 0 and ("for" in listM[i - 1]):
                edges.append((cur, listM[i - 1]))
            elif nxt and ("sp" in nxt):
                edges.append((cur, nxt))
            elif st is not None and en is not None and (st <= i <= en):
                edges.append((cur, "f"))
            else:
                if nxt:
                    edges.append((cur, nxt))
            i += 1
            continue

        # for (non-nested)
        if cur.startswith("for") and ("sp" not in cur):
            f1 = cur
            if nxt and ("sp" not in nxt):
                edges.append((cur, cur))

            stfor = i
            j = None
            for k in range(i + 1, len(listM)):
                if "sp" not in listM[k]:
                    j = k
                    break

            if j is not None:
                enfor = j
                edges.append((cur, listM[j]))
                if nxt and listM[i + 1] != listM[j]:
                    edges.append((cur, listM[i + 1]))

            i += 1
            continue

        # while (non-nested)
        if cur.startswith("while") and ("sp" not in cur):
            f = cur
            if nxt and ("sp" not in nxt):
                edges.append((cur, cur))

            st = i
            j = None
            for k in range(i + 1, len(listM)):
                if "sp" not in listM[k]:
                    j = k
                    break

            if j is not None:
                en = j
                edges.append((cur, listM[j]))
                if nxt and listM[i + 1] != listM[j]:
                    edges.append((cur, listM[i + 1]))

            i += 1
            continue

        # whilesp
        if cur.startswith("whilesp"):
            if st is not None and en is not None and (st <= i <= en):
                edges.append((cur, "f"))
            else:
                if nxt:
                    edges.append((cur, nxt))
            edges.append((cur, cur))
            i += 1
            continue

        # nested ifsp / elifsp / elsesp etc:
        # keep minimal default behavior
        if nxt:
            edges.append((cur, nxt))
        i += 1

    # --- De-duplicate edges (preserve order) ---
    seen = set()
    uniq_edges: List[Tuple[str, str]] = []
    for e in edges:
        if e not in seen and e[0] is not None and e[1] is not None:
            uniq_edges.append(e)
            seen.add(e)

    # frequency dict from list3 (kept for compatibility with your tool)
    freq = defaultdict(int)
    for n in list3:
        if n is not None:
            freq[n] += 1

    return nodes, uniq_edges, list3, dict(freq)


def build_adj_from_edges(edges: List[Tuple[str, str]]) -> Dict[str, List[str]]:
    """Helper: convert edge list to adjacency dict."""
    d: Dict[str, List[str]] = defaultdict(list)
    for a, b in edges:
        d[a].append(b)
    return d
