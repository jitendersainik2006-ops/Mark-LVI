"""
actions/manage_memory.py — Personal memory management tool for J.A.R.V.I.S.

Allows inspecting, editing, deleting, saving, and toggling personal long-term memory.
Enforces credential filtering (no API keys, secrets, or passwords stored) and
tracks entry sources (user_fact vs assumption/inferred).
"""

from typing import Optional
from memory.memory_manager import (
    all_entries_for_ui,
    search_memory,
    remember,
    forget,
    edit_memory,
    delete_memory,
    is_memory_enabled,
    set_memory_enabled,
    contains_credentials,
)


def manage_memory(parameters: dict, player=None, **_) -> str:
    action = str(parameters.get("action", "list")).strip().lower()
    category = str(parameters.get("category", "")).strip().lower()
    key = str(parameters.get("key", "")).strip().lower().replace(" ", "_")
    value = str(parameters.get("value", "")).strip()
    source = str(parameters.get("source", "user_fact")).strip().lower()
    enabled = parameters.get("enabled")

    if action == "status":
        state = "enabled" if is_memory_enabled() else "disabled"
        count = len(all_entries_for_ui())
        return f"Personal memory is currently {state}. Total remembered entries: {count}."

    if action == "toggle":
        if enabled is None:
            # flip state if not explicitly specified
            new_state = not is_memory_enabled()
        else:
            new_state = bool(enabled)
        set_memory_enabled(new_state)
        state_str = "enabled" if new_state else "disabled"
        if player:
            player.write_log(f"[Memory] ⚙️ Memory {state_str}")
        return f"Personal memory has been {state_str}."

    if action == "list":
        if not is_memory_enabled():
            return "Personal memory is currently disabled in settings."
        query = parameters.get("query") or key or category or ""
        return search_memory(query, limit=10)

    if action == "save":
        if not is_memory_enabled():
            return "Cannot save: personal memory is currently disabled."
        if not key or not value:
            return "Please provide both 'key' and 'value' to save a memory."
        if contains_credentials(value):
            return "Security refusal: memory values cannot contain API keys, credentials, or passwords."
        valid_cats = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
        cat = category if category in valid_cats else "notes"
        src = source if source in ("user_fact", "preference", "assumption", "inferred") else "user_fact"
        remember(key=key, value=value, category=cat, source=src)
        if player:
            player.write_log(f"[Memory] 💾 Saved {cat}/{key}")
        return f"Saved to memory: {cat}/{key} = {value} (source: {src})"

    if action == "edit":
        if not is_memory_enabled():
            return "Cannot edit: personal memory is currently disabled."
        if not key or not value:
            return "Please provide both 'key' and 'value' to update a memory."
        if contains_credentials(value):
            return "Security refusal: memory values cannot contain API keys, credentials, or passwords."
        valid_cats = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
        cat = category if category in valid_cats else "notes"
        src = source if source in ("user_fact", "preference", "assumption", "inferred") else "user_fact"
        ok = edit_memory(category=cat, key=key, value=value, source=src)
        if ok:
            if player:
                player.write_log(f"[Memory] ✏️ Edited {cat}/{key}")
            return f"Updated memory: {cat}/{key} = {value}"
        return f"Could not update memory for {cat}/{key}."

    if action in ("delete", "forget"):
        if not is_memory_enabled():
            return "Cannot delete: personal memory is currently disabled."
        if not key:
            return "Please specify the 'key' of the memory item to delete."
        valid_cats = {"identity", "preferences", "projects", "relationships", "wishes", "notes"}
        cat = category if category in valid_cats else "notes"
        ok = delete_memory(category=cat, key=key)
        if ok:
            if player:
                player.write_log(f"[Memory] 🗑️ Deleted {cat}/{key}")
            return f"Deleted from memory: {cat}/{key}"
        return f"Memory item not found: {cat}/{key}"

    return f"Unknown memory action: '{action}'. Use list, save, edit, delete, toggle, or status."


TOOL = {
    "name": "manage_memory",
    "tier": "core",
    "brief": "Inspect, save, edit, delete, or toggle personal long-term memory.",
    "description": (
        "Inspect, save, edit, delete, or toggle personal long-term memory. "
        "Use action='list' to inspect stored facts or search with a query. "
        "Use action='save' to store a confirmed fact or preference. "
        "Use action='edit' to update an existing fact. "
        "Use action='delete' to forget a fact. "
        "Use action='toggle' to turn memory storage on or off."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "list | save | edit | delete | toggle | status"
            },
            "category": {
                "type": "STRING",
                "description": "Category: identity | preferences | projects | relationships | wishes | notes"
            },
            "key": {
                "type": "STRING",
                "description": "Unique key (e.g. favorite_color, brother_name, project_goal)"
            },
            "value": {
                "type": "STRING",
                "description": "Value to store or update"
            },
            "source": {
                "type": "STRING",
                "description": "user_fact (confirmed by user) | preference | assumption (inferred/tentative)"
            },
            "enabled": {
                "type": "BOOLEAN",
                "description": "Used with action='toggle' (true to enable, false to disable)"
            },
            "query": {
                "type": "STRING",
                "description": "Search keyword when action='list'"
            }
        },
        "required": ["action"]
    },
    "handler": manage_memory,
}
