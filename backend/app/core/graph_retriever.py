# backend/app/core/graph_retriever.py
"""
GraphRAG Context Retriever
===========================
Fetches graph nodes and edges from MongoDB that are linked to the Qdrant chunk IDs
returned from vector search. Builds a compact structured summary string to replace
raw chunk text in the LLM prompt, drastically reducing input token count.

Token Savings Example
---------------------
  Before: 5 raw chunks × 400 words each = 2,000 words (~2,600 tokens)
  After:  1 graph summary block = ~150 words (~200 tokens)
  Savings: ~87% fewer tokens per RAG query
  
Graph Summary Format (sent to LLM)
-----------------------------------
  ENTITIES: Apple Inc. [ORG], Tim Cook [PERSON], iPhone 15 [PRODUCT]
  RELATIONS:
    - Tim Cook → CEO_OF → Apple Inc.
    - Apple Inc. → RELEASED → iPhone 15
"""
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase
import structlog

logger = structlog.get_logger("graph_retriever")


async def fetch_graph_context(
    workspace_id: str,
    chunk_ids: List[str],
    db: AsyncIOMotorDatabase
) -> str:
    """
    Given a workspace ID and the Qdrant point IDs from vector search,
    queries MongoDB for all graph nodes and edges linked to those chunks.
    Returns a compact, structured text block ready for LLM consumption.
    
    Args:
        workspace_id: Tenant isolation filter
        chunk_ids:    Qdrant point UUIDs from vector similarity search
        db:           MongoDB async motor client
        
    Returns:
        A compact graph context string (~50-200 words)
        or an empty string if no graph data exists yet.
    """
    if not chunk_ids:
        return ""
    
    try:
        # ── Fetch Nodes ─────────────────────────────────────────────────────
        nodes_cursor = db.graph_nodes.find({
            "workspace_id": workspace_id,
            "chunk_id": {"$in": chunk_ids}
        })
        
        nodes: List[Dict] = []
        async for node in nodes_cursor:
            nodes.append(node)
        
        if not nodes:
            logger.info("no_graph_nodes_for_chunks", chunk_count=len(chunk_ids))
            return ""
        
        # Deduplicate nodes by name (same entity might appear in multiple chunks)
        seen_names = set()
        unique_nodes = []
        for n in nodes:
            key = n["name"].lower()
            if key not in seen_names:
                seen_names.add(key)
                unique_nodes.append(n)
        
        # ── Fetch Edges ─────────────────────────────────────────────────────
        edges_cursor = db.graph_edges.find({
            "workspace_id": workspace_id,
            "chunk_id": {"$in": chunk_ids}
        })
        
        edges: List[Dict] = []
        async for edge in edges_cursor:
            edges.append(edge)
        
        # ── Build compact summary string ────────────────────────────────────
        summary = build_graph_summary(unique_nodes, edges)
        logger.info("graph_context_built",
                    node_count=len(unique_nodes),
                    edge_count=len(edges),
                    summary_words=len(summary.split()))
        return summary
    
    except Exception as e:
        logger.error("graph_retrieval_failed", error=str(e))
        return ""  # Gracefully degrade — chat still works via raw chunks


def build_graph_summary(nodes: List[Dict], edges: List[Dict]) -> str:
    """
    Formats extracted graph nodes and edges into a compact structured
    string ready for inclusion in an LLM system prompt.
    
    Compact format uses ~10x fewer tokens than raw chunk text.
    """
    if not nodes:
        return ""
    
    lines = []
    
    # Group entities by type for easy reading
    by_type: Dict[str, List[str]] = {}
    for node in nodes:
        entity_type = node.get("entity_type", "CONCEPT")
        name = node.get("name", "")
        if entity_type not in by_type:
            by_type[entity_type] = []
        by_type[entity_type].append(name)
    
    entity_parts = []
    for etype, names in by_type.items():
        # Show max 6 per type to stay concise
        capped = names[:6]
        entity_parts.append(f"{', '.join(capped)} [{etype}]")
    
    lines.append("GRAPH ENTITIES: " + " | ".join(entity_parts))
    
    if edges:
        lines.append("KNOWN RELATIONS:")
        # Deduplicate edges by (from, relation, to) tuple
        seen_edges = set()
        for edge in edges[:20]:  # Cap at 20 relations per query
            from_n = edge.get("from_node", "")
            rel = edge.get("relation", "")
            to_n = edge.get("to_node", "")
            key = (from_n.lower(), rel, to_n.lower())
            if key not in seen_edges and from_n and to_n:
                seen_edges.add(key)
                lines.append(f"  - {from_n} → {rel} → {to_n}")
    
    return "\n".join(lines)
