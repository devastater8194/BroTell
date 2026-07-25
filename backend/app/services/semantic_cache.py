from typing import Optional
from app.services.rag_service import get_qdrant_client, chroma_client, RAGService

class SemanticCache:
  """
  Provides semantic caching for chat endpoints using query embeddings.
  It queries Qdrant (or fallback ChromaDB) to match incoming queries with historical queries.
  """
  @classmethod
  def lookup(cls, youtube_video_id: str, query: str) -> Optional[str]:
    # 1. Generate query embedding
    embs = RAGService.get_embeddings([query])
    if not embs:
      return None
    query_emb = embs[0]
    
    collection_name = f"video_{youtube_video_id}_cache"
    
    # 2. Try Qdrant lookup
    q_client = get_qdrant_client()
    if q_client:
      try:
        if not q_client.collection_exists(collection_name):
          return None
          
        results = q_client.search(
          collection_name=collection_name,
          query_vector=query_emb,
          limit=1
        )
        if results and results[0].score >= 0.90:
          print(f"SemanticCache: Hit (Qdrant) with similarity score {results[0].score:.3f}")
          return results[0].payload.get("response")
      except Exception as e:
        print(f"SemanticCache Qdrant lookup error: {e}")
        
    # 3. Fallback to ChromaDB lookup
    try:
      collection = chroma_client.get_collection(name=collection_name)
      results = collection.query(
        query_embeddings=[query_emb],
        n_results=1
      )
      if results and results["documents"] and results["documents"][0]:
        distance = results["distances"][0][0]
        # Cosine distance to similarity conversion
        similarity = 1.0 - distance
        if similarity >= 0.90:
          print(f"SemanticCache: Hit (ChromaDB) with similarity score {similarity:.3f}")
          return results["metadatas"][0][0].get("response")
    except Exception:
      pass
      
    return None

  @classmethod
  def save(cls, youtube_video_id: str, query: str, response: str):
    # 1. Generate query embedding
    embs = RAGService.get_embeddings([query])
    if not embs:
      return
    query_emb = embs[0]
    
    collection_name = f"video_{youtube_video_id}_cache"
    
    # 2. Try Qdrant save
    q_client = get_qdrant_client()
    if q_client:
      try:
        from qdrant_client.http import models as qmodels
        if not q_client.collection_exists(collection_name):
          q_client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=768, distance=qmodels.Distance.COSINE)
          )
        
        import uuid
        point_id = str(uuid.uuid4())
        q_client.upsert(
          collection_name=collection_name,
          points=[
            qmodels.PointStruct(
              id=point_id,
              vector=query_emb,
              payload={"query": query, "response": response}
            )
          ]
        )
        return
      except Exception as e:
        print(f"SemanticCache Qdrant save error: {e}")

    # 3. Fallback to ChromaDB save
    try:
      try:
        collection = chroma_client.get_collection(name=collection_name)
      except Exception:
        collection = chroma_client.create_collection(name=collection_name)
      
      import uuid
      doc_id = str(uuid.uuid4())
      collection.add(
        documents=[query],
        embeddings=[query_emb],
        metadatas=[{"response": response}],
        ids=[doc_id]
      )
    except Exception as e:
      print(f"SemanticCache ChromaDB save error: {e}")
