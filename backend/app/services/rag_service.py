import chromadb
from pathlib import Path
from typing import List, Optional
import google.generativeai as genai
from app.config import settings

# Setup local persistent storage path for ChromaDB
CHROMA_DB_PATH = Path(__file__).parent.parent.parent / "chroma_db"
CHROMA_DB_PATH.mkdir(exist_ok=True)

# Initialize persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path=str(CHROMA_DB_PATH))

# Setup Qdrant client connection state
_qdrant_client = None
_qdrant_init_failed = False

def get_qdrant_client():
  global _qdrant_client, _qdrant_init_failed
  if _qdrant_client is not None:
    return _qdrant_client
  if _qdrant_init_failed:
    return None

  q_url = settings.QDRANT_URL.strip()
  if not q_url:
    return None

  try:
    from qdrant_client import QdrantClient
    print(f"RAGService: Connecting to Qdrant at {q_url}...")
    _qdrant_client = QdrantClient(url=q_url, api_key=settings.QDRANT_API_KEY.strip() or None)
    return _qdrant_client
  except Exception as e:
    print(f"RAGService: Qdrant client initialization error ({type(e).__name__}: {e}). Falling back to ChromaDB.")
    _qdrant_init_failed = True
    return None

class RAGService:
  @staticmethod
  def get_embeddings(texts: List[str]) -> List[List[float]]:
    """
    Generates vector embeddings for a list of texts using Gemini's API.
    If the GEMINI_API_KEY is not configured, it gracefully falls back to mock vectors.
    """
    api_key = settings.GEMINI_API_KEY.strip()
    
    # Check if the key is empty or still contains placeholder text
    if not api_key or "YOUR_GEMINI_API_KEY" in api_key:
      print("RAGService: [Warning] GEMINI_API_KEY is not configured in .env. Falling back to mock 768-dim embeddings.")
      # Return mock 768-dimensional float vectors (Gemini text-embedding-004 style)
      return [[0.01 * (i % 10) for i in range(768)] for _ in texts]

    try:
      genai.configure(api_key=api_key)
      response = genai.embed_content(
        model="models/text-embedding-004",
        content=texts,
        task_type="retrieval_document"
      )
      return response["embedding"]
    except Exception as e:
      print("RAGService: Error calling Gemini Embeddings API:", e)
      # Return mock vector on failure so execution can continue
      return [[0.01 * (i % 10) for i in range(768)] for _ in texts]

  @classmethod
  def chunk_transcript(cls, video_id: str, segments: List[dict], chunk_size: int = 1000, overlap: int = 200) -> List[dict]:
    """
    Groups small transcript lines into larger, timestamp-aware chunks.
    Ensures start and end times are preserved in chunk metadata.
    """
    chunks = []
    current_chunk_text = ""
    current_start = 0.0
    current_end = 0.0
    
    for segment in segments:
      text = segment["text"]
      start = segment["start"]
      end = segment["end"]
      
      if not current_chunk_text:
        current_start = start
        current_chunk_text = text
      else:
        current_chunk_text += " " + text
      
      current_end = end
      
      if len(current_chunk_text) >= chunk_size:
        chunks.append({
          "text": current_chunk_text,
          "metadata": {
            "video_id": video_id,
            "timestamp_start": current_start,
            "timestamp_end": current_end,
            "source": "transcript"
          }
        })
        
        # Keep overlapping suffix for the next chunk
        words = current_chunk_text.split()
        overlap_text = " ".join(words[-15:]) # Approximate overlap by trailing words
        current_chunk_text = overlap_text
        current_start = start
        
    # Append any remaining segment text
    if current_chunk_text.strip():
      chunks.append({
        "text": current_chunk_text,
        "metadata": {
          "video_id": video_id,
          "timestamp_start": current_start,
          "timestamp_end": current_end,
          "source": "transcript"
        }
      })
      
    return chunks

  @classmethod
  def index_transcript(cls, database_video_id: str, youtube_video_id: str, segments: List[dict]):
    """Chunks transcript segments, generates embeddings, and saves them in Qdrant (or ChromaDB)."""
    chunks = cls.chunk_transcript(database_video_id, segments)
    if not chunks:
      return

    collection_name = f"video_{youtube_video_id}"
    
    # 1. Try Qdrant Indexing
    q_client = get_qdrant_client()
    if q_client:
      try:
        from qdrant_client.http import models as qmodels
        
        # Reset collection if exists
        try:
          q_client.delete_collection(collection_name)
        except Exception:
          pass
          
        q_client.create_collection(
          collection_name=collection_name,
          vectors_config=qmodels.VectorParams(size=768, distance=qmodels.Distance.COSINE)
        )
        
        texts = [c["text"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]
        embeddings = cls.get_embeddings(texts)
        
        points = []
        for i, (text, meta, emb) in enumerate(zip(texts, metadatas, embeddings)):
          points.append(
            qmodels.PointStruct(
              id=i,
              vector=emb,
              payload={"text": text, **meta}
            )
          )
        
        q_client.upsert(collection_name=collection_name, points=points)
        print(f"RAGService: Successfully indexed {len(chunks)} chunks in Qdrant collection '{collection_name}'")
        return
      except Exception as e:
        print(f"RAGService: Qdrant indexing failed ({e}). Falling back to ChromaDB...")

    # 2. ChromaDB Fallback
    try:
      chroma_client.delete_collection(name=collection_name)
    except Exception:
      pass
      
    collection = chroma_client.create_collection(name=collection_name)

    texts = [c["text"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]
    ids = [f"chunk_{youtube_video_id}_{i}" for i in range(len(chunks))]
    
    embeddings = cls.get_embeddings(texts)
    
    collection.add(
      documents=texts,
      embeddings=embeddings,
      metadatas=metadatas,
      ids=ids
    )
    print(f"RAGService: Successfully indexed {len(chunks)} chunks in ChromaDB collection '{collection_name}'")

  @classmethod
  def retrieve_context(cls, youtube_video_id: str, query: str, k: int = 5) -> List[dict]:
    """
    Queries Qdrant (or ChromaDB fallback) to find the top k matching chunks for the search query.
    Performs cosine similarity search.
    """
    collection_name = f"video_{youtube_video_id}"
    
    # 1. Try Qdrant retrieval
    q_client = get_qdrant_client()
    if q_client:
      try:
        query_embeddings = cls.get_embeddings([query])
        if not query_embeddings:
          return []
          
        results = q_client.search(
          collection_name=collection_name,
          query_vector=query_embeddings[0],
          limit=k
        )
        
        retrieved_chunks = []
        for point in results:
          retrieved_chunks.append({
            "text": point.payload.get("text", ""),
            "metadata": point.payload,
            "distance": point.score
          })
        return retrieved_chunks
      except Exception as e:
        print(f"RAGService: Qdrant search failed ({e}). Falling back to ChromaDB...")

    # 2. ChromaDB Fallback retrieval
    try:
      collection = chroma_client.get_collection(name=collection_name)
    except Exception:
      print(f"RAGService: Collection '{collection_name}' not found. Cannot retrieve context.")
      return []

    query_embeddings = cls.get_embeddings([query])
    if not query_embeddings:
      return []
      
    results = collection.query(
      query_embeddings=query_embeddings,
      n_results=k
    )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    retrieved_chunks = []
    for i in range(len(documents)):
      retrieved_chunks.append({
        "text": documents[i],
        "metadata": metadatas[i],
        "distance": distances[i]
      })
      
    return retrieved_chunks

  @classmethod
  def get_all_chunks(cls, youtube_video_id: str) -> List[str]:
    """Retrieves all text documents indexed for a specific YouTube Video ID."""
    collection_name = f"video_{youtube_video_id}"
    
    # 1. Try Qdrant scroll
    q_client = get_qdrant_client()
    if q_client:
      try:
        records, _ = q_client.scroll(
          collection_name=collection_name,
          limit=1000,
          with_payload=True,
          with_vectors=False
        )
        records.sort(key=lambda x: x.id)
        return [r.payload.get("text", "") for r in records if r.payload]
      except Exception as e:
        print(f"RAGService: Qdrant scroll failed ({e}). Falling back to ChromaDB...")

    # 2. ChromaDB Fallback scroll
    try:
      collection = chroma_client.get_collection(name=collection_name)
      results = collection.get()
      return results.get("documents", []) or []
    except Exception:
      return []

  @classmethod
  def get_condensed_context(cls, youtube_video_id: str, max_chars: int = 12000) -> str:
    """
    Retrieves and condenses the transcript chunks for a video to fit within a character budget.
    Uses heuristic scoring (technical terms, average word length, filler word penalties)
    to select the most informative chunks, then returns them in chronological order.
    """
    chunks = cls.get_all_chunks(youtube_video_id)
    if not chunks:
      return "No transcript chunks found."
      
    full_text = "\n\n".join(chunks)
    if len(full_text) <= max_chars:
      return full_text
      
    scored_chunks = []
    
    # Common tech/tutorial keywords carrying high information density
    tech_keywords = {
      "function", "class", "import", "const", "return", "database", "api", "route",
      "server", "client", "config", "deploy", "schema", "query", "install", "npm",
      "python", "javascript", "code", "run", "test", "build", "component", "state",
      "module", "package", "method", "variable", "object", "array", "list", "key",
      "important", "concept", "explain", "example", "step", "learn", "define"
    }
    
    # Common filler keywords carrying low information density
    filler_keywords = {
      "um", "uh", "like", "you know", "sort of", "kind of", "basically", "actually",
      "so yeah", "stuff", "things", "just", "hey guys", "welcome back", "subscribe",
      "sponsor", "channel"
    }
    
    for idx, chunk in enumerate(chunks):
      words = chunk.lower().split()
      if not words:
        continue
        
      tech_count = sum(1 for w in words if any(k in w for k in tech_keywords))
      filler_count = sum(1 for w in words if any(f in w for f in filler_keywords))
      avg_word_len = sum(len(w) for w in words) / len(words)
      
      # Heuristic score formulation
      score = (tech_count * 3.0) + (avg_word_len * 2.0) - (filler_count * 2.0)
      
      scored_chunks.append({
        "index": idx,
        "text": chunk,
        "score": score
      })
      
    # Sort by score descending to get high information density first
    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    
    # Select chunks fitting the character budget
    selected = []
    current_len = 0
    
    for item in scored_chunks:
      chunk_len = len(item["text"])
      if current_len + chunk_len + 2 > max_chars:
        if selected:
          break
      selected.append(item)
      current_len += chunk_len + 2
      
    # Sort chronologically by original index to preserve tutorial progression flow
    selected.sort(key=lambda x: x["index"])
    
    return "\n\n".join(item["text"] for item in selected)
