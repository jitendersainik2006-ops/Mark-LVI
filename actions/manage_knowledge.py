"""
actions/manage_knowledge.py — J.A.R.V.I.S. Human-Provided Knowledge Management Tool

Allows J.A.R.V.I.S. and the user to:
- Learn directly from text, notes, tutorials, and guidelines.
- Import files (PDF, DOCX, TXT, Markdown, JSON, Code).
- View, search, update, reindex, or delete knowledge sources.
- Enable or disable specific sources or the entire knowledge base.
- Provide source attribution, citations, and version-aware answers.
"""

from typing import Optional
from core.knowledge_manager import knowledge_manager


def manage_knowledge(parameters: dict, player=None, **_) -> str:
    action = str(parameters.get("action", "list_sources")).strip().lower()
    source_id = str(parameters.get("source_id", "")).strip()
    title = str(parameters.get("title", "")).strip()
    text = str(parameters.get("text", "")).strip()
    file_path = str(parameters.get("file_path", "")).strip()
    query = str(parameters.get("query", "")).strip()
    enabled = parameters.get("enabled")

    if action == "status":
        st = "enabled" if knowledge_manager.is_enabled() else "disabled"
        sources = knowledge_manager.list_sources()
        active = sum(1 for s in sources if s.get("enabled"))
        total_chunks = sum(s.get("chunk_count", 0) for s in sources)
        return (
            f"📚 Knowledge Base Status: {st.upper()}\n"
            f"Total Sources: {len(sources)} ({active} active)\n"
            f"Indexed Chunks: {total_chunks}"
        )

    if action == "add_text":
        if not text:
            return "Please provide the 'text' or note content to add to the knowledge base."
        doc_title = title or f"Note ({text[:25]}...)"
        source = knowledge_manager.add_text_knowledge(title=doc_title, text=text)
        if player:
            player.write_log(f"[Knowledge] 📖 Added: '{source.title}' ({source.chunk_count} chunks)")
        return (
            f"Knowledge added successfully!\n"
            f"Source ID: {source.id}\n"
            f"Title: {source.title}\n"
            f"Indexed Chunks: {source.chunk_count}\n"
            f"Version: v{source.version}"
        )

    if action == "import_file":
        if not file_path:
            return "Please specify the 'file_path' of the document to import (PDF, DOCX, TXT, MD, etc.)."
        try:
            source = knowledge_manager.import_file(file_path_str=file_path, title=title or None)
            if player:
                player.write_log(f"[Knowledge] 📄 Imported: '{source.title}' ({source.chunk_count} chunks)")
            return (
                f"Document imported and indexed successfully!\n"
                f"Source ID: {source.id}\n"
                f"Title: {source.title}\n"
                f"File: {source.file_path}\n"
                f"Indexed Chunks: {source.chunk_count}\n"
                f"Version: v{source.version}"
            )
        except Exception as e:
            return f"Failed to import file: {e}"

    if action == "list_sources":
        sources = knowledge_manager.list_sources()
        if not sources:
            return "No knowledge sources registered. Use action='add_text' or action='import_file' to teach J.A.R.V.I.S."
        lines = [f"Found {len(sources)} knowledge source(s):"]
        for s in sources:
            st = "active" if s.get("enabled") else "disabled"
            lines.append(f"- [{st.upper()}] {s['title']} (ID: {s['id']}, v{s['version']}, {s['chunk_count']} chunks, type: {s['source_type']})")
        return "\n".join(lines)

    if action == "get_source":
        if not source_id:
            return "Please specify the 'source_id' to inspect."
        src = knowledge_manager.get_source(source_id)
        if not src:
            return f"Knowledge source '{source_id}' not found."
        return (
            f"Source: {src['title']} (ID: {src['id']})\n"
            f"Type: {src['source_type']}\n"
            f"Status: {'Active' if src['enabled'] else 'Disabled'}\n"
            f"Version: v{src['version']}\n"
            f"Chunks: {src['chunk_count']}\n"
            f"Created: {src['created_at']}\n"
            f"Updated: {src['updated_at']}\n"
            f"File Path: {src.get('file_path') or 'Direct text'}"
        )

    if action == "search":
        search_q = query or text
        if not search_q:
            return "Please provide a 'query' to search in the knowledge base."
        matches = knowledge_manager.search(search_q, top_k=4)
        if not matches:
            return f"No relevant knowledge passages found for '{search_q}'."
        lines = [f"Found {len(matches)} relevant passage(s):"]
        for i, m in enumerate(matches, 1):
            lines.append(f"\n[{i}] Source: {m['source_title']} (Section: {m['section']}, v{m['version']}, score: {m['score']:.2f})")
            lines.append(f"\"{m['text']}\"")
        return "\n".join(lines)

    if action == "update_source":
        if not source_id:
            return "Please specify the 'source_id' to update."
        try:
            source = knowledge_manager.update_source(source_id=source_id, new_text=text or None, new_file_path=file_path or None)
            if player:
                player.write_log(f"[Knowledge] 🔄 Updated: '{source.title}' to v{source.version}")
            return f"Knowledge source '{source.id}' updated to version v{source.version} ({source.chunk_count} chunks reindexed)."
        except Exception as e:
            return f"Failed to update source: {e}"

    if action == "delete_source":
        if not source_id:
            return "Please specify the 'source_id' to remove."
        ok = knowledge_manager.delete_source(source_id)
        if ok:
            if player:
                player.write_log(f"[Knowledge] 🗑️ Deleted source: {source_id}")
            return f"Knowledge source '{source_id}' and all its indexed passages removed."
        return f"Could not find or delete source '{source_id}'."

    if action == "toggle_source":
        if not source_id:
            return "Please specify the 'source_id' to toggle."
        new_state = knowledge_manager.toggle_source(source_id, enabled=enabled)
        state_str = "enabled" if new_state else "disabled"
        if player:
            player.write_log(f"[Knowledge] Source {source_id} {state_str}")
        return f"Knowledge source '{source_id}' is now {state_str}."

    if action == "toggle_knowledge_base":
        new_state = knowledge_manager.toggle_knowledge_base(enabled=enabled)
        state_str = "enabled" if new_state else "disabled"
        if player:
            player.write_log(f"[Knowledge] System {state_str}")
        return f"Knowledge base is now {state_str}."

    return f"Unknown knowledge action: '{action}'. Use status, add_text, import_file, list_sources, get_source, search, update_source, delete_source, toggle_source, or toggle_knowledge_base."


TOOL = {
    "name": "manage_knowledge",
    "tier": "core",
    "brief": "Add, import, search, update, inspect, or manage human-provided knowledge sources.",
    "description": (
        "Accesses J.A.R.V.I.S. Human-Provided Knowledge Base. "
        "Use action='add_text' to teach J.A.R.V.I.S. instructions, notes, or facts. "
        "Use action='import_file' to index approved documents (PDF, DOCX, TXT, MD). "
        "Use action='search' to look up verified passages and citations for user questions. "
        "Use action='list_sources' or action='get_source' to inspect registered material. "
        "Use action='update_source' to revise existing documents with versioning. "
        "Use action='delete_source' to remove a source. "
        "Use action='toggle_source' or action='toggle_knowledge_base' to temporarily enable/disable."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "action": {
                "type": "STRING",
                "description": "add_text | import_file | search | list_sources | get_source | update_source | delete_source | toggle_source | toggle_knowledge_base | status"
            },
            "title": {
                "type": "STRING",
                "description": "Title or descriptive label for the knowledge source"
            },
            "text": {
                "type": "STRING",
                "description": "Content of the note, instruction, or update"
            },
            "file_path": {
                "type": "STRING",
                "description": "File path of the document to import or update"
            },
            "query": {
                "type": "STRING",
                "description": "Search query to find passages in the knowledge base"
            },
            "source_id": {
                "type": "STRING",
                "description": "Unique source ID for get_source, update_source, delete_source, or toggle_source"
            },
            "enabled": {
                "type": "BOOLEAN",
                "description": "Boolean flag for toggle_source or toggle_knowledge_base"
            }
        },
        "required": ["action"]
    },
    "handler": manage_knowledge,
}
