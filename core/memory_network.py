"""
core/memory_network.py — Visual Memory Network & Relational Knowledge Graph

Provides an expanded, categorized, graph-connected personal memory network:
- 9 Strict Categories: user, people, preferences, projects, plans, devices, conversations, tasks, learned.
- Relational graph links between memory nodes.
- Source tracking, confidence scoring, search, edit, delete, export/import.
- Thread-safe persistence backing memory/long_term.json and data/memory_graph.json.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("JARVIS.MemoryNetwork")

BASE_DIR = Path(__file__).resolve().parent.parent
GRAPH_PATH = BASE_DIR / "data" / "memory_graph.json"

CATEGORIES = [
    "user",
    "people",
    "preferences",
    "projects",
    "plans",
    "devices",
    "conversations",
    "tasks",
    "learned",
]


@dataclass
class MemoryNode:
    id: str
    category: str
    key: str
    value: str
    source: str = "operator"
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    related_ids: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    @property
    def label(self) -> str:
        return self.key

    @property
    def content(self) -> str:
        return self.value

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["label"] = self.key
        d["content"] = self.value
        return d

    @classmethod
    def from_dict(cls, data: dict) -> MemoryNode:
        clean = dict(data)
        if clean.get("category") not in CATEGORIES:
            clean["category"] = "learned"
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in clean.items() if k in valid_keys}
        return cls(**filtered)


class MemoryNetwork:
    """Thread-safe Visual Memory Network with relational connections."""

    _instance: Optional[MemoryNetwork] = None

    @classmethod
    def get_instance(cls) -> MemoryNetwork:
        if cls._instance is None:
            cls._instance = MemoryNetwork()
        return cls._instance

    def __init__(self, graph_file: Path = GRAPH_PATH):
        self._graph_file = graph_file
        self._lock = threading.Lock()
        self._nodes: Dict[str, MemoryNode] = {}
        self._load()

    def _load(self):
        with self._lock:
            if not self._graph_file.exists():
                self._bootstrap_from_long_term_memory()
                return
            try:
                data = json.loads(self._graph_file.read_text(encoding="utf-8"))
                for item in data.get("nodes", []):
                    node = MemoryNode.from_dict(item)
                    self._nodes[node.id] = node
            except Exception as e:
                logger.error(f"[MemoryNetwork] Failed to load graph: {e}")
                self._bootstrap_from_long_term_memory()

    def _bootstrap_from_long_term_memory(self):
        """Seed network from memory/long_term.json if graph is fresh."""
        lt_path = BASE_DIR / "memory" / "long_term.json"
        if not lt_path.exists():
            return
        try:
            raw = json.loads(lt_path.read_text(encoding="utf-8"))
            for cat, items in raw.items():
                target_cat = cat if cat in CATEGORIES else ("preferences" if cat == "identity" else "learned")
                if isinstance(items, dict):
                    for k, v in items.items():
                        val_str = str(v.get("value", v) if isinstance(v, dict) else v)
                        node_id = f"mem_{target_cat}_{re.sub(r'[^a-zA-Z0-9_]', '_', k)}"
                        self._nodes[node_id] = MemoryNode(
                            id=node_id,
                            category=target_cat,
                            key=k,
                            value=val_str,
                            source="seed_migration",
                            confidence=0.95,
                        )
            self._save()
        except Exception as e:
            logger.error(f"[MemoryNetwork] Seed error: {e}")

    def _save(self):
        try:
            self._graph_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": "1.0",
                "categories": CATEGORIES,
                "node_count": len(self._nodes),
                "updated_at": time.time(),
                "nodes": [n.to_dict() for n in self._nodes.values()],
            }
            self._graph_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"[MemoryNetwork] Save error: {e}")

    # ── CRUD & Graph Operations ────────────────────────────────────────────────

    def get_categories(self) -> List[str]:
        return list(CATEGORIES)

    def add_node(
        self,
        arg1: str,
        arg2: str,
        arg3: str,
        source: str = "operator",
        confidence: float = 1.0,
        related_ids: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[dict] = None,
    ) -> MemoryNode:
        # Detect if called as (category, key, value) or (label/key, category, content/value)
        if arg1.lower().strip() in CATEGORIES:
            cat = arg1.lower().strip()
            key_clean = str(arg2).strip()
            val_clean = str(arg3).strip()
        elif arg2.lower().strip() in CATEGORIES:
            key_clean = str(arg1).strip()
            cat = arg2.lower().strip()
            val_clean = str(arg3).strip()
        else:
            cat = "learned"
            key_clean = str(arg1).strip()
            val_clean = str(arg3 or arg2).strip()

        node_id = f"mem_{cat}_{re.sub(r'[^a-zA-Z0-9_]', '_', key_clean)}_{int(time.time()*1000)%100000}"

        with self._lock:
            node = MemoryNode(
                id=node_id,
                category=cat,
                key=key_clean,
                value=val_clean,
                source=source,
                confidence=max(0.1, min(1.0, float(confidence))),
                related_ids=related_ids or [],
                tags=tags or [],
            )
            self._nodes[node_id] = node
            for r_id in node.related_ids:
                if r_id in self._nodes and node_id not in self._nodes[r_id].related_ids:
                    self._nodes[r_id].related_ids.append(node_id)
            self._save()
        return node

    def link_nodes(self, node_id_1: str, node_id_2: str, relation: str = "relates_to") -> bool:
        with self._lock:
            if node_id_1 not in self._nodes or node_id_2 not in self._nodes:
                return False
            n1 = self._nodes[node_id_1]
            n2 = self._nodes[node_id_2]
            if node_id_2 not in n1.related_ids:
                n1.related_ids.append(node_id_2)
            if node_id_1 not in n2.related_ids:
                n2.related_ids.append(node_id_1)
            self._save()
            return True

    def update_node(self, node_id: str, value: Optional[str] = None, related_ids: Optional[List[str]] = None, tags: Optional[List[str]] = None) -> Optional[MemoryNode]:
        with self._lock:
            if node_id not in self._nodes:
                return None
            node = self._nodes[node_id]
            if value is not None:
                node.value = str(value).strip()
            if related_ids is not None:
                node.related_ids = list(related_ids)
            if tags is not None:
                node.tags = list(tags)
            node.updated_at = time.time()
            self._save()
            return node

    def delete_node(self, node_id: str) -> bool:
        with self._lock:
            if node_id not in self._nodes:
                return False
            del self._nodes[node_id]
            # Remove link references
            for n in self._nodes.values():
                if node_id in n.related_ids:
                    n.related_ids.remove(node_id)
            self._save()
            return True

    def get_node(self, node_id: str) -> Optional[MemoryNode]:
        return self._nodes.get(node_id)

    def get_nodes(self) -> List[MemoryNode]:
        with self._lock:
            return list(self._nodes.values())

    def search(self, query: str = "", category: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        q = str(query or "").strip().lower()
        res = []
        with self._lock:
            for n in self._nodes.values():
                if category and n.category.lower() != category.lower():
                    continue
                if not q or (q in n.key.lower() or q in n.value.lower() or any(q in t.lower() for t in n.tags)):
                    res.append(n.to_dict())
        return res[:limit]

    def get_graph(self) -> Dict[str, Any]:
        """Returns node and edge definitions formatted for frontend graph visualizer."""
        with self._lock:
            nodes = []
            edges = []
            seen_edges: Set[str] = set()

            for n in self._nodes.values():
                nodes.append({
                    "id": n.id,
                    "label": f"{n.key}: {n.value[:25]}..." if len(n.value) > 25 else f"{n.key}: {n.value}",
                    "category": n.category,
                    "key": n.key,
                    "value": n.value,
                    "source": n.source,
                    "confidence": n.confidence,
                })
                for rel in n.related_ids:
                    if rel in self._nodes:
                        edge_key = tuple(sorted([n.id, rel]))
                        edge_str = f"{edge_key[0]}->{edge_key[1]}"
                        if edge_str not in seen_edges:
                            seen_edges.add(edge_str)
                            edges.append({"from": edge_key[0], "to": edge_key[1]})

            return {
                "categories": CATEGORIES,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "nodes": nodes,
                "edges": edges,
                "links": [{"source": e.get("from"), "target": e.get("to")} for e in edges],
                "link_count": len(edges),
            }

    def export_graph(self, category: Optional[str] = None) -> Dict[str, Any]:
        """Exports graph structure with category filtering and links alias."""
        graph = self.get_graph()
        if category:
            graph["nodes"] = [n for n in graph["nodes"] if n.get("category") == category]
            graph["node_count"] = len(graph["nodes"])
        return graph

    def export_json(self) -> str:
        with self._lock:
            payload = {
                "exported_at": time.time(),
                "nodes": [n.to_dict() for n in self._nodes.values()]
            }
            return json.dumps(payload, indent=2, ensure_ascii=False)

    def import_json(self, raw_json: str) -> int:
        count = 0
        try:
            data = json.loads(raw_json)
            nodes = data.get("nodes", data if isinstance(data, list) else [])
            with self._lock:
                for item in nodes:
                    if "key" in item and "value" in item:
                        node = MemoryNode.from_dict(item)
                        self._nodes[node.id] = node
                        count += 1
                self._save()
        except Exception as e:
            logger.error(f"[MemoryNetwork] Import error: {e}")
        return count


# Singleton accessor
memory_network = MemoryNetwork.get_instance()
