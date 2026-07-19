# workers/app/graphify_runner.py
"""
Graphify CLI Integration
========================
Wraps the `graphify` CLI tool (pip install graphifyy) to build a knowledge graph
from ingested document text files. Graphify processes the text and produces:
  - graph.json:       Persistent graph (nodes + edges) used for querying
  - GRAPH_REPORT.md:  Summary of discovered entities and connections

Token Savings
-------------
Graphify's own benchmark: 71.5x fewer tokens per query vs reading raw files.
In our pipeline: we extract the graph.json and store it in MongoDB so the
backend graph_retriever can use it for compact context generation.

How It Works in KnowledgeOS
----------------------------
1. After parsing a PDF, worker saves chunk text to a temp folder
2. graphify CLI runs on that folder and produces graph.json
3. We parse graph.json and upsert nodes/edges into MongoDB
4. Backend graph_retriever reads those MongoDB nodes to build compact context

Reference: https://github.com/Graphify-Labs/graphify
"""
import asyncio
import json
import os
import tempfile
import shutil
import structlog
from typing import List, Dict, Any, Optional
from pathlib import Path
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger("graphify_runner")


async def is_graphify_installed() -> bool:
    """Check if the graphify CLI is available on PATH."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "graphify", "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        await proc.communicate()
        return proc.returncode == 0
    except FileNotFoundError:
        return False


async def run_graphify_on_chunks(
    chunks: List[Dict[str, Any]],
    workspace_id: str,
    document_id: str,
    filename: str,
    db: AsyncIOMotorDatabase,
    timeout: int = 120
) -> bool:
    """
    Main entry point. Saves chunk texts to a temp dir, runs `graphify .` on it,
    then parses graph.json and stores the graph into MongoDB.
    
    Returns True on success, False on any failure (non-blocking by design).
    """
    if not chunks:
        return False

    # Check graphify is available
    if not await is_graphify_installed():
        logger.warn("graphify_not_installed",
                    hint="Run: pip install graphifyy && graphify install")
        return False

    # Create a temporary working directory for this document's chunks
    temp_dir = tempfile.mkdtemp(prefix=f"graphify_{document_id[:8]}_")
    output_dir = os.path.join(temp_dir, "graphify-out")
    
    try:
        # ── Step 1: Write chunks to text files ────────────────────────────────
        chunks_dir = os.path.join(temp_dir, "chunks")
        os.makedirs(chunks_dir, exist_ok=True)
        
        for i, chunk in enumerate(chunks):
            chunk_path = os.path.join(chunks_dir, f"chunk_{i:04d}_page{chunk.get('page_number', 1)}.txt")
            with open(chunk_path, "w", encoding="utf-8") as f:
                # Include filename header for context
                f.write(f"# Source: {filename}\n\n")
                f.write(chunk.get("text", ""))

        logger.info("chunk_files_written", count=len(chunks), temp_dir=temp_dir)

        # ── Step 2: Run graphify CLI ──────────────────────────────────────────
        logger.info("running_graphify_cli", working_dir=chunks_dir)
        
        proc = await asyncio.create_subprocess_exec(
            "graphify", ".",
            cwd=chunks_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "GRAPHIFY_NO_INTERACTIVE": "1"}
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            logger.error("graphify_timeout", timeout_seconds=timeout, document_id=document_id)
            return False
        
        if proc.returncode != 0:
            logger.error("graphify_cli_failed",
                        returncode=proc.returncode,
                        stderr=stderr.decode("utf-8", errors="replace")[:500])
            return False
        
        logger.info("graphify_cli_completed", document_id=document_id)

        # ── Step 3: Parse graph.json output ───────────────────────────────────
        # Graphify outputs to graphify-out/graph.json by default
        graph_json_path = os.path.join(chunks_dir, "graphify-out", "graph.json")
        
        # Fallback: search recursively if path differs
        if not os.path.exists(graph_json_path):
            found = list(Path(chunks_dir).rglob("graph.json"))
            if not found:
                logger.warn("graphify_graph_json_not_found", document_id=document_id)
                return False
            graph_json_path = str(found[0])

        with open(graph_json_path, "r", encoding="utf-8") as f:
            graph_data = json.load(f)
        
        logger.info("graphify_graph_json_loaded",
                    node_count=len(graph_data.get("nodes", [])),
                    edge_count=len(graph_data.get("edges", [])))

        # ── Step 4: Store graph to MongoDB ────────────────────────────────────
        await store_graphify_graph(graph_data, workspace_id, document_id, db)
        return True

    except Exception as e:
        logger.error("graphify_pipeline_error", error=str(e), document_id=document_id)
        return False
    finally:
        # Always clean up temp files to avoid disk bloat
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug("graphify_temp_dir_cleaned", temp_dir=temp_dir)


async def store_graphify_graph(
    graph_data: Dict,
    workspace_id: str,
    document_id: str,
    db: AsyncIOMotorDatabase
) -> None:
    """
    Maps Graphify's graph.json schema to our MongoDB graph_nodes / graph_edges
    collections for unified querying by the backend graph_retriever.
    
    Graphify graph.json schema:
    {
      "nodes": [{"id": "...", "label": "...", "type": "...", "summary": "..."}],
      "edges": [{"source": "...", "target": "...", "relation": "..."}]
    }
    """
    nodes = graph_data.get("nodes", [])
    edges = graph_data.get("edges", [])
    
    if not nodes:
        logger.warn("graphify_empty_graph", document_id=document_id)
        return
    
    # Build node_id lookup: graphify node id → MongoDB doc _id
    node_id_map: Dict[str, str] = {}
    node_docs = []
    
    for node in nodes:
        graphify_id = node.get("id", "")
        name = node.get("label", node.get("name", graphify_id)).strip()
        entity_type = node.get("type", "CONCEPT").upper()
        context = node.get("summary", node.get("description", ""))
        
        if not name:
            continue
        
        import uuid
        mongo_id = str(uuid.uuid4())
        node_id_map[graphify_id] = mongo_id
        
        node_docs.append({
            "_id": mongo_id,
            "workspace_id": workspace_id,
            "document_id": document_id,
            "chunk_id": document_id,  # Use document_id as chunk_id for graphify nodes
            "name": name,
            "entity_type": entity_type,
            "context": context[:500] if context else "",  # Cap to 500 chars
            "source": "graphify"
        })
    
    if node_docs:
        try:
            await db.graph_nodes.insert_many(node_docs, ordered=False)
            logger.info("graphify_nodes_stored", count=len(node_docs))
        except Exception as e:
            logger.warn("graphify_nodes_partial_insert", error=str(e))
    
    # Insert edges
    edge_docs = []
    for edge in edges:
        source_graphify_id = edge.get("source", "")
        target_graphify_id = edge.get("target", "")
        relation = edge.get("relation", edge.get("label", "RELATED_TO")).upper()
        
        from_node_id = node_id_map.get(source_graphify_id)
        to_node_id = node_id_map.get(target_graphify_id)
        
        if not from_node_id or not to_node_id:
            continue
        
        # Get display names from node docs
        from_name = next((n["name"] for n in node_docs if n["_id"] == from_node_id), source_graphify_id)
        to_name = next((n["name"] for n in node_docs if n["_id"] == to_node_id), target_graphify_id)
        
        import uuid
        edge_docs.append({
            "_id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "chunk_id": document_id,
            "from_node": from_name,
            "from_node_id": from_node_id,
            "relation": relation,
            "to_node": to_name,
            "to_node_id": to_node_id,
            "source": "graphify"
        })
    
    if edge_docs:
        try:
            await db.graph_edges.insert_many(edge_docs, ordered=False)
            logger.info("graphify_edges_stored", count=len(edge_docs))
        except Exception as e:
            logger.warn("graphify_edges_partial_insert", error=str(e))
