# workers/app/graph_extractor.py
"""
GraphRAG Entity Extractor
=========================
Extracts named entities and relationships from text chunks using Gemini Flash API.
Stores them in MongoDB as a lightweight knowledge graph (no extra graph DB needed).

Graph Schema
------------
graph_nodes: { _id, workspace_id, document_id, chunk_id, name, entity_type, context }
graph_edges: { _id, workspace_id, from_node, relation, to_node, chunk_id }

Token Savings
-------------
Instead of sending 5 raw chunks (avg 2000 tokens) to the LLM, we send a compact
entity+relation summary (~200 tokens). That's ~87% token reduction per query.
"""
import json
import re
import uuid
import structlog
from typing import List, Dict, Any
from motor.motor_asyncio import AsyncIOMotorDatabase

logger = structlog.get_logger("graph_extractor")

# ─────────────────────────────────────────
# Prompt used to extract entities + edges
# ─────────────────────────────────────────
EXTRACTION_PROMPT = """You are an expert knowledge graph extractor.
Given the following text, extract:
1. Named Entities: people, organizations, products, locations, concepts, dates
2. Relations between those entities (subject → predicate → object triples)

Return ONLY a valid JSON object in this exact format, nothing else:
{
  "entities": [
    {"name": "entity name", "type": "PERSON|ORG|PRODUCT|LOCATION|CONCEPT|DATE"}
  ],
  "relations": [
    {"from": "entity A", "relation": "RELATION_VERB", "to": "entity B"}
  ]
}

Text to analyze:
\"\"\"
{TEXT}
\"\"\"
"""

def _regex_fallback_extract(text: str) -> Dict:
    """
    CPU-only regex fallback when Gemini API is unavailable.
    Extracts capitalized noun phrases as CONCEPT entities.
    Does not extract relations (graph edges will be empty).
    """
    # Match sequences of 1-3 capitalized words (rough entity approximation)
    pattern = re.compile(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+){0,2})\b')
    found = set(pattern.findall(text))
    
    # Filter common stop words that are often capitalized (e.g., "The", "This", "In")
    stopwords = {"The", "This", "In", "At", "On", "For", "With", "From", "To", "And", "Or"}
    entities = [{"name": name, "type": "CONCEPT"} for name in found if name not in stopwords]
    
    logger.info("regex_fallback_extraction", entity_count=len(entities))
    return {"entities": entities[:15], "relations": []}  # Cap at 15 to limit noise


async def extract_entities_from_chunk(
    chunk_text: str,
    gemini_api_key: str
) -> Dict:
    """
    Calls Gemini Flash to extract entities and relations from a single chunk.
    Falls back to regex extraction on API failure or quota exhaustion.
    """
    try:
        import google.generativeai as genai
        genai.configure(api_key=gemini_api_key)
        
        model = genai.GenerativeModel("gemini-1.5-flash")
        prompt = EXTRACTION_PROMPT.replace("{TEXT}", chunk_text[:2000])  # Cap input at 2000 chars
        
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.0,  # Deterministic for structured extraction
                max_output_tokens=512,
            )
        )
        
        raw_text = response.text.strip()
        
        # Strip markdown code fences if present (e.g. ```json ... ```)
        if raw_text.startswith("```"):
            raw_text = re.sub(r"```(?:json)?\n?", "", raw_text).strip().rstrip("```").strip()
        
        parsed = json.loads(raw_text)
        entities = parsed.get("entities", [])
        relations = parsed.get("relations", [])
        
        logger.info("gemini_extraction_success",
                    entity_count=len(entities),
                    relation_count=len(relations))
        return {"entities": entities, "relations": relations}
    
    except json.JSONDecodeError as e:
        logger.warn("gemini_extraction_json_parse_failed", error=str(e))
        return _regex_fallback_extract(chunk_text)
    
    except Exception as e:
        logger.warn("gemini_extraction_api_failed_falling_back", error=str(e))
        return _regex_fallback_extract(chunk_text)


async def store_graph_to_mongo(
    graph_data: Dict,
    chunk_id: str,
    workspace_id: str,
    document_id: str,
    db: AsyncIOMotorDatabase
) -> None:
    """
    Persists extracted entities (nodes) and relations (edges) into MongoDB.
    
    Collections used:
    - graph_nodes: one document per unique entity per chunk
    - graph_edges: one document per relation triple per chunk
    """
    entities = graph_data.get("entities", [])
    relations = graph_data.get("relations", [])
    
    if not entities:
        logger.info("no_entities_to_store", chunk_id=chunk_id)
        return
    
    # Build node name → stored node_id map for edge resolution
    node_id_map: Dict[str, str] = {}
    
    # ── Insert Nodes ─────────────────────────────────────────────────────────
    node_docs = []
    for entity in entities:
        name = entity.get("name", "").strip()
        if not name:
            continue
        node_id = str(uuid.uuid4())
        node_id_map[name.lower()] = node_id
        node_docs.append({
            "_id": node_id,
            "workspace_id": workspace_id,
            "document_id": document_id,
            "chunk_id": chunk_id,
            "name": name,
            "entity_type": entity.get("type", "CONCEPT"),
            "context": ""  # Could store surrounding sentence for richer display
        })
    
    if node_docs:
        # Use unordered=False to skip duplicates without halting the batch
        try:
            await db.graph_nodes.insert_many(node_docs, ordered=False)
        except Exception as e:
            logger.warn("graph_nodes_partial_insert", error=str(e))
    
    # ── Insert Edges ─────────────────────────────────────────────────────────
    edge_docs = []
    for relation in relations:
        from_name = relation.get("from", "").strip().lower()
        to_name = relation.get("to", "").strip().lower()
        rel_verb = relation.get("relation", "RELATED_TO").strip().upper()
        
        from_node_id = node_id_map.get(from_name)
        to_node_id = node_id_map.get(to_name)
        
        if not from_node_id or not to_node_id:
            # Skip edges whose nodes weren't captured (hallucinated names)
            continue
        
        edge_docs.append({
            "_id": str(uuid.uuid4()),
            "workspace_id": workspace_id,
            "chunk_id": chunk_id,
            "from_node": relation.get("from", "").strip(),
            "from_node_id": from_node_id,
            "relation": rel_verb,
            "to_node": relation.get("to", "").strip(),
            "to_node_id": to_node_id
        })
    
    if edge_docs:
        try:
            await db.graph_edges.insert_many(edge_docs, ordered=False)
        except Exception as e:
            logger.warn("graph_edges_partial_insert", error=str(e))

    logger.info("graph_stored",
                nodes=len(node_docs),
                edges=len(edge_docs),
                chunk_id=chunk_id)


async def extract_and_store_graph(
    chunk_text: str,
    chunk_id: str,
    workspace_id: str,
    document_id: str,
    gemini_api_key: str,
    db: AsyncIOMotorDatabase
) -> None:
    """
    Main entry point called by the indexer after Qdrant upsert.
    Extracts graph data from text and stores into MongoDB.
    
    Designed to be non-blocking: if this fails, ingestion still succeeds.
    """
    try:
        graph_data = await extract_entities_from_chunk(chunk_text, gemini_api_key)
        await store_graph_to_mongo(graph_data, chunk_id, workspace_id, document_id, db)
    except Exception as e:
        # Never let graph extraction failure break the main ingestion pipeline
        logger.error("graph_extraction_pipeline_error", error=str(e), chunk_id=chunk_id)
