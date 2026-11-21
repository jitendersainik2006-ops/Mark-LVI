import json
import re
from datetime import datetime
from threading import Lock
from pathlib import Path
import sys


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR         = get_base_dir()
MEMORY_PATH      = BASE_DIR / "memory" / "long_term.json"
_lock            = Lock()
MAX_VALUE_LENGTH = 380


def _log(msg: str) -> None:
    try:
        print(msg)
    except (UnicodeEncodeError, Exception):
        try:
            print(str(msg).encode("ascii", "replace").decode("ascii"))
        except Exception:
            pass


_active_user_id: str | None = None


def set_active_user(user_id: str | None) -> None:
    """Set the currently active user for user-scoped memory isolation."""
    global _active_user_id
    _active_user_id = user_id


def get_active_user() -> str | None:
    """Get the currently active user ID."""
    return _active_user_id


def get_memory_path(user_id: str | None = None) -> Path:
    """Resolve storage path for long_term.json.

    If user_id is provided or an active user is set, isolates storage to:
        data/users/<user_id>/memory/long_term.json
    Otherwise defaults to the legacy/global path:
        memory/long_term.json
    """
    target_uid = user_id or _active_user_id
    if target_uid:
        safe_uid = re.sub(r"[^a-zA-Z0-9_\-]", "", str(target_uid))
        if safe_uid:
            p = BASE_DIR / "data" / "users" / safe_uid / "memory" / "long_term.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            return p
    return MEMORY_PATH

# ── Why there are two very different numbers here ────────────────────────────
#
# There used to be one: MEMORY_MAX_CHARS = 2200, applied to the whole store. It
# was a *storage* limit, and it existed only because the entire memory was
# pasted into the system prompt on every connect — so growing the memory grew
# every single request. When it filled, _trim_to_limit() deleted the oldest
# entries and printed one line to a console nobody reads. A memory described as
# "deeply remembers projects, preferences and personal context" was in practice
# two pages long, and quietly forgot your sister's name after a few weeks.
#
# Storage and prompt budget are now separate concerns:
#
#   MEMORY_MAX_CHARS  — a runaway guard, not a feature limit. Nothing normal
#                       reaches it; a bug writing in a loop does.
#   PROMPT_CORE_CHARS — what actually rides in the system prompt every session.
#                       Smaller than the old whole-memory dump, so sessions
#                       start *faster* than before, not slower.
#
# Everything above the core stays on disk and is fetched on demand by the
# recall_memory tool — see search_memory() and format_memory_for_prompt().
MEMORY_MAX_CHARS  = 200_000
PROMPT_CORE_CHARS = 900
PROMPT_INDEX_CHARS = 420
# Most entries any one category may contribute to the core block, so a person
# with forty stored preferences still gets their sister into the prompt.
PROMPT_MAX_PER_CATEGORY = 6

# Strict credential filtering patterns: API keys, bearer tokens, passwords
_CREDENTIAL_PATTERNS = [
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z\-_]{30,45}", re.IGNORECASE),

    re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE),
    re.compile(r"glpat-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"xox[baprs]-[0-9a-zA-Z]{10,48}", re.IGNORECASE),
    re.compile(r"(?:bearer\s+|token\s*[:=]\s*)[a-zA-Z0-9_\-\.]{16,}", re.IGNORECASE),
    re.compile(r"(?:api[_-]?key|secret|password|passwd|pwd)\s*[:=]\s*[^\s,;]+", re.IGNORECASE),
]

def contains_credentials(text: str) -> bool:
    """Detect presence of sensitive API keys, tokens, or passwords."""
    if not isinstance(text, str):
        return False
    return any(p.search(text) for p in _CREDENTIAL_PATTERNS)

def redact_credentials(text: str) -> str:
    """Filter out API keys, tokens, and passwords from memory values."""
    if not isinstance(text, str):
        return str(text or "")
    clean = str(text)
    for p in _CREDENTIAL_PATTERNS:
        clean = p.sub("[REDACTED_CREDENTIAL]", clean)
    return clean

def is_memory_enabled() -> bool:
    """Check if memory storage and injection are enabled in configuration."""
    try:
        from memory.config_manager import get_memory_enabled
        return get_memory_enabled()
    except Exception:
        return True

def set_memory_enabled(enabled: bool) -> None:
    """Toggle memory storage and injection in configuration."""
    try:
        from memory.config_manager import save_memory_enabled
        save_memory_enabled(enabled)
    except Exception as e:
        _log(f"[Memory] ⚠️ set_memory_enabled error: {e}")

def is_auto_create_enabled() -> bool:
    """Check if automatic extraction of memories from chat conversation is active."""
    try:
        from memory.config_manager import get_auto_create_memory
        return get_auto_create_memory()
    except Exception:
        return True

def set_auto_create_enabled(enabled: bool) -> None:
    """Toggle automatic extraction of memories from chat conversation."""
    try:
        from memory.config_manager import save_auto_create_memory
        save_auto_create_memory(enabled)
    except Exception as e:
        _log(f"[Memory] ⚠️ set_auto_create_enabled error: {e}")

def _empty_memory() -> dict:

    return {
        "identity":      {},
        "preferences":   {},
        "projects":      {},
        "relationships": {},
        "wishes":        {},
        "notes":         {},
    }

def load_memory(user_id: str | None = None) -> dict:
    path = get_memory_path(user_id)
    if not path.exists():
        return _empty_memory()
    with _lock:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                base = _empty_memory()
                for key in base:
                    if key not in data:
                        data[key] = {}
                return data
            return _empty_memory()
        except Exception as e:
            _log(f"[Memory] ⚠️ Load error: {e}")
            return _empty_memory()

def _all_entries(memory: dict) -> list[tuple]:
    entries = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            if isinstance(entry, dict) and "value" in entry:
                entries.append((cat, key, entry))
    return entries


# Set by main.py so a trim can reach the activity log. Deleting something a
# person told you and mentioning it only on stdout is how a memory loses trust.
_trim_notifier = None


def set_trim_notifier(fn) -> None:
    """Register a callable(str) that surfaces trims to the user."""
    global _trim_notifier
    _trim_notifier = fn


def _trim_to_limit(memory: dict) -> dict:
    if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
        return memory
    entries = _all_entries(memory)
    entries.sort(key=lambda t: t[2].get("updated", "0000-00-00"))
    dropped = []
    for cat, key, _ in entries:
        if len(json.dumps(memory, ensure_ascii=False)) <= MEMORY_MAX_CHARS:
            break
        del memory[cat][key]
        dropped.append(f"{cat}/{key}")
        _log(f"[Memory] 🗑️  Trimmed {cat}/{key}")
    if dropped and _trim_notifier:
        try:
            _trim_notifier(
                f"SYS: Memory full — forgot {len(dropped)} oldest entries "
                f"({', '.join(dropped[:3])}{'…' if len(dropped) > 3 else ''})"
            )
        except Exception:
            pass
    return memory

def save_memory(memory: dict, user_id: str | None = None) -> None:
    if not is_memory_enabled():
        _log("[Memory] ⏸️ Memory disabled — skipped save.")
        return
    if not isinstance(memory, dict):
        return
    memory = _trim_to_limit(memory)
    path = get_memory_path(user_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _lock:
        path.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )


def _truncate_value(val: str) -> str:
    if isinstance(val, str) and len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH].rstrip() + "…"
    return val


def _recursive_update(target: dict, updates: dict, default_source: str = "user_fact") -> bool:
    changed = False
    for key, value in updates.items():
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        if isinstance(value, dict) and "value" not in value:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
                changed = True
            if _recursive_update(target[key], value, default_source):
                changed = True
        else:
            raw_val = value.get("value") if isinstance(value, dict) else value
            source = value.get("source", default_source) if isinstance(value, dict) else default_source
            confidence = value.get("confidence", 1.0) if isinstance(value, dict) else 1.0

            clean_val = redact_credentials(str(raw_val or ""))
            new_val  = _truncate_value(clean_val)
            entry    = {
                "value": new_val,
                "updated": datetime.now().strftime("%Y-%m-%d"),
                "source": str(source or "user_fact"),
                "confidence": float(confidence if confidence is not None else 1.0),
            }
            existing = target.get(key, {})
            if (not isinstance(existing, dict)
                    or existing.get("value") != new_val
                    or existing.get("source") != entry["source"]):
                target[key] = entry
                changed = True
    return changed


def update_memory(memory_update: dict, default_source: str = "user_fact", user_id: str | None = None) -> dict:
    if not isinstance(memory_update, dict) or not memory_update:
        return load_memory(user_id)
    if not is_memory_enabled():
        _log("[Memory] ⏸️ Memory disabled — skipped update.")
        return load_memory(user_id)
    memory = load_memory(user_id)
    if _recursive_update(memory, memory_update, default_source=default_source):
        save_memory(memory, user_id)
        _log(f"[Memory] 💾 Saved: {list(memory_update.keys())}")
    return memory


def _entry_value(entry) -> str:
    """Accept both the {'value': ..., 'updated': ...} shape and a bare string,
    because early versions of the store wrote plain strings."""
    if isinstance(entry, dict):
        return str(entry.get("value", "") or "").strip()
    return str(entry or "").strip()


def _pretty(key: str) -> str:
    return key.replace("_", " ").strip()


# Identity is always in the prompt; these categories compete for the remaining
# budget by recency.
_CATEGORY_LABELS = {
    "preferences":   "Preferences",
    "projects":      "Active projects / goals",
    "relationships": "People in their life",
    "wishes":        "Wishes / plans",
    "notes":         "Notes",
}

_IDENTITY_FIELDS = ["name", "age", "birthday", "city", "job",
                    "language", "school", "nationality"]


def format_memory_for_prompt(memory: dict | None = None, user_id: str | None = None) -> str:
    """Build the memory block that goes into the system prompt.

    This used to dump everything. It now sends three things:

      1. IDENTITY  - always, in full. It is small, and it is wrong for the
         assistant to have to look up your name.
      2. RECENT    - the most recently updated entries from every other
         category, up to PROMPT_CORE_CHARS. Recency is the cheapest useful
         relevance signal available without embeddings.
      3. AN INDEX  - the *keys* of everything else, values omitted.

    Point 3 is what makes recall work at all. A model cannot decide to look
    something up if it does not know the thing exists: with only points 1 and 2,
    "who is Ayse?" would get "I don't know" while ayse_sister sat on disk
    unread. The index costs a few hundred characters and turns recall from a
    gamble into a lookup.

    Net effect on latency: this block is SMALLER than the old full dump, so
    every session connects with fewer tokens. Occasionally the model spends one
    extra round trip on recall_memory - covered by the acknowledgment it
    already speaks before any slow step."""
    if memory is None:
        memory = load_memory(user_id)
    if not memory or not is_memory_enabled():
        return ""

    core_lines: list[str] = []

    # 1. Identity - always, in full
    identity = memory.get("identity", {}) or {}
    for field in _IDENTITY_FIELDS:
        val = _entry_value(identity.get(field))
        if not val:
            continue
        if field == "language":
            # Labelled as an observation, not a setting. A bare "Language:
            # English" line written months ago reads like a standing order and
            # was one of the reasons a Turkish question came back in English.
            core_lines.append(
                f"Has spoken to you in: {val} (an observation about the past — "
                f"always answer in the language of their CURRENT message)")
        else:
            core_lines.append(f"{field.title()}: {val}")
    for key, entry in identity.items():
        if key in _IDENTITY_FIELDS:
            continue
        val = _entry_value(entry)
        if val:
            src = entry.get("source", "user_fact") if isinstance(entry, dict) else "user_fact"
            src_tag = " [unconfirmed assumption]" if src in ("assumption", "inferred") else ""
            core_lines.append(f"{_pretty(key).title()}: {val}{src_tag}")

    # 2. Everything else, pinned entries first, then most recently updated
    rest: list[tuple[str, str, str, str, str, bool]] = []   # (updated, cat, key, value, source, pinned)
    for cat in _CATEGORY_LABELS:
        for key, entry in (memory.get(cat, {}) or {}).items():
            val = _entry_value(entry)
            if not val:
                continue
            updated = (entry.get("updated", "") if isinstance(entry, dict) else "") or "0000-00-00"
            src = (entry.get("source", "user_fact") if isinstance(entry, dict) else "user_fact")
            is_pinned = bool(entry.get("pinned", False)) if isinstance(entry, dict) else False
            rest.append((updated, cat, key, val, src, is_pinned))
    # Pinned first (1 > 0), then newest updated first
    rest.sort(key=lambda t: (1 if t[5] else 0, t[0]), reverse=True)

    used    = sum(len(l) + 1 for l in core_lines)
    shown: dict[str, list[str]] = {}
    overflow: dict[str, list[str]] = {}

    # Recency and pin status decide order. Pinned items are guaranteed presentation.
    per_cat_used: dict[str, int] = {}
    for _updated, cat, key, val, src, is_pinned in rest:
        src_tag = " [unconfirmed assumption]" if src in ("assumption", "inferred") else ""
        pin_tag = " 📌" if is_pinned else ""
        line = f"  - {_pretty(key).title()}: {val}{src_tag}{pin_tag}"
        if is_pinned or (per_cat_used.get(cat, 0) < PROMPT_MAX_PER_CATEGORY and used + len(line) + 1 <= PROMPT_CORE_CHARS):
            shown.setdefault(cat, []).append(line)
            per_cat_used[cat] = per_cat_used.get(cat, 0) + 1
            used += len(line) + 1
        else:
            overflow.setdefault(cat, []).append(_pretty(key))


    # The index is a table of contents, so it is interleaved across categories
    # rather than continuing in recency order. Sorted by recency it would list
    # twenty-four preferences before the first relationship, and the one entry
    # the index exists for — the old fact the model has no other way to know
    # about — would fall off the end.
    indexed: list[str] = []
    if overflow:
        cats  = [c for c in _CATEGORY_LABELS if overflow.get(c)]
        cursor = {c: 0 for c in cats}
        while cats:
            for cat in list(cats):
                i = cursor[cat]
                if i >= len(overflow[cat]):
                    cats.remove(cat)
                    continue
                indexed.append(overflow[cat][i])
                cursor[cat] = i + 1

    for cat, label in _CATEGORY_LABELS.items():
        if shown.get(cat):
            core_lines.append("")
            core_lines.append(f"{label}:")
            core_lines.extend(shown[cat])

    if not core_lines and not indexed:
        return ""

    out = [
        "[WHAT YOU KNOW ABOUT THIS PERSON — use naturally, never recite like a list]",
        *core_lines,
    ]

    # 3. The index of what is on disk but not in this prompt
    if indexed:
        budget, names = PROMPT_INDEX_CHARS, []
        for n in indexed:
            if budget - len(n) - 2 < 0:
                break
            names.append(n)
            budget -= len(n) + 2
        if names:
            out.append("")
            out.append(
                "[ALSO REMEMBERED — values not shown here. Call recall_memory "
                "with a keyword to read any of these before saying you do not know]"
            )
            out.append(", ".join(names)
                       + (f" (+{len(indexed) - len(names)} more)"
                          if len(indexed) > len(names) else ""))

    return "\n".join(out) + "\n"


# ── Recall ────────────────────────────────────────────────────────────────────

def _score(query_words: list[str], cat: str, key: str, value: str) -> int:
    """Cheap lexical relevance. No embeddings, no network, no model call - this
    runs in well under a millisecond, which is the entire point: recall must
    cost one model round trip, never two."""
    hay_key = _pretty(key).lower()
    hay_val = value.lower()
    score   = 0
    for w in query_words:
        if not w:
            continue
        if w == hay_key:
            score += 10
        elif w in hay_key:
            score += 6
        if w in hay_val:
            score += 3
        if w in cat:
            score += 1
    return score


def search_memory(query: str, limit: int = 8, user_id: str | None = None) -> str:
    """Find stored facts matching `query`. Backs the recall_memory tool.

    An empty query is treated as "show me everything you know", capped - the
    model asks that when the user says "what do you remember about me?"."""
    if not is_memory_enabled():
        return "Personal memory is currently disabled in settings."
    memory = load_memory(user_id)
    words  = [w for w in re.split(r"[\W_]+", (query or "").lower()) if len(w) > 1]


    rows: list[tuple[int, str, str, str]] = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue                     # skip 'sessions', which is a list
        for key, entry in items.items():
            val = _entry_value(entry)
            if not val:
                continue
            s = _score(words, cat, key, val) if words else 1
            if s > 0:
                rows.append((s, cat, key, val))

    if not rows:
        return (f"Nothing stored about '{query}'." if query
                else "I have not stored anything about this person yet.")

    rows.sort(key=lambda r: (-r[0], r[2]))
    lines = [f"{cat}/{_pretty(key)}: {val}" for _s, cat, key, val in rows[:max(1, limit)]]
    head  = (f"Stored facts matching '{query}':" if query
             else "Everything currently stored:")
    more  = (f"\n(+{len(rows) - len(lines)} more — search with a narrower keyword)"
             if len(rows) > len(lines) else "")
    return head + "\n" + "\n".join(lines) + more


def all_entries_for_ui(user_id: str | None = None) -> list[dict]:
    """Flat list for the memory panel: what JARVIS knows, and when it learned it.
    Sorted newest first so the panel opens on what changed most recently."""
    memory = load_memory(user_id)
    rows = []
    for cat, items in memory.items():
        if not isinstance(items, dict):
            continue
        for key, entry in items.items():
            val = _entry_value(entry)
            if not val:
                continue
            rows.append({
                "category":   cat,
                "key":        key,
                "value":      val,
                "updated":    (entry.get("updated", "") if isinstance(entry, dict) else ""),
                "source":     (entry.get("source", "user_fact") if isinstance(entry, dict) else "user_fact"),
                "confidence": (entry.get("confidence", 1.0) if isinstance(entry, dict) else 1.0),
            })
    rows.sort(key=lambda r: (r["updated"] or "0000-00-00"), reverse=True)
    return rows

def remember(key: str, value: str, category: str = "notes", source: str = "user_fact", user_id: str | None = None) -> str:
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    clean_val = redact_credentials(value)
    update_memory({category: {key: {"value": clean_val, "source": source}}}, user_id=user_id)
    return f"Remembered: {category}/{key} = {clean_val}"


def forget(key: str, category: str = "notes", user_id: str | None = None) -> str:
    memory = load_memory(user_id)
    cat    = memory.get(category, {})
    if key in cat:
        del cat[key]
        memory[category] = cat
        save_memory(memory, user_id)
        return f"Forgotten: {category}/{key}"
    return f"Not found: {category}/{key}"


forget_memory = forget


def edit_memory(category: str, key: str, value: str, source: str = "user_fact", confidence: float = 1.0, user_id: str | None = None) -> bool:
    """Edit or update an existing memory item."""
    if not is_memory_enabled():
        return False
    valid = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
    if category not in valid:
        category = "notes"
    clean_val = redact_credentials(str(value or ""))
    update_memory({category: {key: {"value": clean_val, "source": source, "confidence": confidence}}}, user_id=user_id)
    return True


def delete_memory(category: str, key: str, user_id: str | None = None) -> bool:
    """Delete a memory item."""
    res = forget(key=key, category=category, user_id=user_id)
    return not res.startswith("Not found")



# ── Session memory ─────────────────────────────────────────────────────────────

_SESSION_MAX = 3   # safety cap — in practice 0-1 entries after pop


def save_session_summary(summary: str, language: str = "", user_id: str | None = None) -> None:
    """Append a 1-2 sentence session summary to long_term.json['sessions']."""
    summary = (summary or "").strip()
    if not summary:
        return
    memory   = load_memory(user_id)
    sessions = memory.get("sessions", [])
    if not isinstance(sessions, list):
        sessions = []
    entry: dict = {
        "date":    datetime.now().strftime("%Y-%m-%d"),
        "summary": summary[:280],
    }
    if language:
        entry["language"] = language
    sessions.append(entry)
    memory["sessions"] = sessions[-_SESSION_MAX:]
    path = get_memory_path(user_id)
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(memory, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
    _log(f"[Memory] 📝 Session saved ({entry['date']}): {summary[:60]}…")


def pop_last_session(user_id: str | None = None) -> dict | None:
    """
    Return AND remove the most recent session entry.
    Calling this consumes the entry so it is never repeated in future briefings.
    """
    path = get_memory_path(user_id)
    with _lock:
        if not path.exists():
            return None
        try:
            memory   = json.loads(path.read_text(encoding="utf-8"))
            sessions = memory.get("sessions", [])
            if not isinstance(sessions, list) or not sessions:
                return None
            entry = sessions.pop()          # remove the last entry
            memory["sessions"] = sessions
            path.write_text(
                json.dumps(memory, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            return entry
        except Exception as e:
            _log(f"[Memory] ⚠️ pop_last_session error: {e}")
            return None


# ── Advanced Memory & Retention Controls ──────────────────────────────────────

def pin_memory(category: str, key: str, pinned: bool = True, user_id: str | None = None) -> bool:
    """Pin or unpin a memory item so it is prioritized in the prompt and never auto-trimmed."""
    memory = load_memory(user_id)
    cat = memory.get(category, {})
    if key in cat and isinstance(cat[key], dict):
        cat[key]["pinned"] = bool(pinned)
        memory[category] = cat
        save_memory(memory, user_id)
        return True
    return False


def get_retention_days() -> int:
    try:
        from memory.config_manager import get_memory_retention_days
        return get_memory_retention_days()
    except Exception:
        return 0


def set_retention_days(days: int) -> None:
    try:
        from memory.config_manager import save_memory_retention_days
        save_memory_retention_days(days)
    except Exception as e:
        _log(f"[Memory] Retention error: {e}")


def apply_retention_policy(user_id: str | None = None) -> int:
    """Archive or prune entries older than retention_days if policy is set. Never deletes pinned entries."""
    retention_days = get_retention_days()
    if retention_days <= 0:
        return 0
    from datetime import datetime, timedelta
    cutoff = datetime.now() - timedelta(days=retention_days)
    cutoff_str = cutoff.strftime("%Y-%m-%d")

    memory = load_memory(user_id)
    dropped = 0
    for cat in ("preferences", "projects", "relationships", "wishes", "notes"):
        items = memory.get(cat, {})
        if not isinstance(items, dict):
            continue
        to_del = []
        for key, entry in items.items():
            if isinstance(entry, dict):
                if entry.get("pinned", False):
                    continue
                upd = entry.get("updated", "")
                if upd and upd < cutoff_str:
                    to_del.append(key)
        for k in to_del:
            del items[k]
            dropped += 1
        memory[cat] = items

    if dropped > 0:
        save_memory(memory, user_id)
        _log(f"[Memory] Applied retention policy ({retention_days} days): pruned {dropped} expired entries.")
    return dropped


def export_memory_backup(backup_path: Path | None = None, user_id: str | None = None) -> Path:
    """Export clean JSON backup of memory to data/backups/."""
    target_uid = user_id or _active_user_id
    suffix = f"_{target_uid}" if target_uid else ""
    dst = backup_path or (BASE_DIR / "data" / "backups" / f"memory_backup{suffix}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    memory = load_memory(user_id)
    dst.write_text(json.dumps(memory, indent=2, ensure_ascii=False), encoding="utf-8")
    return dst


def import_memory_backup(backup_path: Path, merge: bool = True, user_id: str | None = None) -> dict:
    """Import and restore memory from JSON backup."""
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found at {backup_path}")
    raw = json.loads(backup_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("Invalid memory backup format.")

    if merge:
        current = load_memory(user_id)
        for cat, items in raw.items():
            if cat not in current:
                current[cat] = items
            elif isinstance(items, dict) and isinstance(current[cat], dict):
                current[cat].update(items)
            elif cat == "sessions" and isinstance(items, list):
                current["sessions"] = items
        save_memory(current, user_id)
        return current
    else:
        save_memory(raw, user_id)
        return raw


def export_user_data_bundle(user_id: str | None = None) -> dict:
    """Generate a sanitized export bundle of memory and configuration."""
    memory = load_memory(user_id)
    return {
        "export_date": datetime.now().isoformat(),
        "user_id": user_id or _active_user_id or "default",
        "assistant_identity": memory.get("identity", {}),
        "preferences": memory.get("preferences", {}),
        "projects": memory.get("projects", {}),
        "relationships": memory.get("relationships", {}),
        "wishes": memory.get("wishes", {}),
        "notes": memory.get("notes", {}),
        "total_entries": len(_all_entries(memory)),
    }