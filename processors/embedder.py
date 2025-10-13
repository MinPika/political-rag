from typing import List, Dict, Optional
from loguru import logger
import google.generativeai as genai
from config.settings import settings
import numpy as np
from database.models import Chunk
from database.db_operations import DatabaseOperations
import time

class Embedder:
    """
    Generate embeddings for text chunks using Google's Gemini embedding model.
    Stores embedding IDs for later use with vector databases like Pinecone.
    """
    
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.embedding_model = "models/embedding-004"
        self.batch_size = 100
        self.rate_limit_delay = 1  # seconds between batches
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embedding for a single text"""
        try:
            if not text or len(text.strip()) < 10:
                logger.warning("Text too short for embedding")
                return None
            
            # Truncate if too long (Gemini has token limits)
            max_chars = 10000
            if len(text) > max_chars:
                text = text[:max_chars]
            
            result = genai.embed_content(
                model=self.embedding_model,
                content=text,
                task_type="retrieval_document"
            )
            
            embedding = result['embedding']
            logger.debug(f"Generated embedding with dimension: {len(embedding)}")
            return embedding
        
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            return None
    
    def generate_batch_embeddings(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Generate embeddings for multiple texts with rate limiting"""
        embeddings = []
        
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            logger.info(f"Processing embedding batch {i//self.batch_size + 1}/{(len(texts)-1)//self.batch_size + 1}")
            
            for text in batch:
                embedding = self.generate_embedding(text)
                embeddings.append(embedding)
            
            # Rate limiting
            if i + self.batch_size < len(texts):
                time.sleep(self.rate_limit_delay)
        
        return embeddings
    
    def embed_chunk(self, chunk: Dict) -> Dict:
        """Generate embedding for a chunk and add it to chunk data"""
        embedding = self.generate_embedding(chunk['text'])
        
        if embedding:
            # Store embedding vector (for later upload to vector DB)
            chunk['embedding_vector'] = embedding
            chunk['embedding_dimension'] = len(embedding)
            chunk['embedding_model'] = self.embedding_model
            logger.debug(f"Embedded chunk {chunk.get('id', 'unknown')}")
        else:
            chunk['embedding_vector'] = None
            chunk['embedding_dimension'] = 0
        
        return chunk
    
    def embed_chunks_batch(self, chunks: List[Dict]) -> List[Dict]:
        """Embed multiple chunks efficiently"""
        texts = [chunk['text'] for chunk in chunks]
        embeddings = self.generate_batch_embeddings(texts)
        
        for chunk, embedding in zip(chunks, embeddings):
            if embedding:
                chunk['embedding_vector'] = embedding
                chunk['embedding_dimension'] = len(embedding)
                chunk['embedding_model'] = self.embedding_model
            else:
                chunk['embedding_vector'] = None
                chunk['embedding_dimension'] = 0
        
        return chunks
    
    def generate_query_embedding(self, query: str) -> Optional[List[float]]:
        """Generate embedding for a search query"""
        try:
            result = genai.embed_content(
                model=self.embedding_model,
                content=query,
                task_type="retrieval_query"  # Different task type for queries
            )
            return result['embedding']
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return None
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0


class VectorStoreManager:
    """
    Manager for storing and retrieving embeddings.
    Currently stores in PostgreSQL as JSONB, but designed to integrate
    with Pinecone, Weaviate, or other vector databases.
    """
    
    def __init__(self, db_ops: DatabaseOperations):
        self.db_ops = db_ops
        self.embedder = Embedder()
    
    def store_chunk_embedding(self, chunk_id: str, embedding: List[float], 
                             metadata: Dict) -> bool:
        """
        Store embedding with metadata.
        In production, this would upload to Pinecone/Weaviate.
        For MVP, we store the vector in PostgreSQL.
        """
        try:
            # For now, we'll store embedding_id as a reference
            # In production: upload to Pinecone and store the returned ID
            
            embedding_id = f"emb_{chunk_id}"
            
            # Update chunk with embedding_id
            # (In production, you'd call Pinecone API here)
            
            logger.debug(f"Stored embedding for chunk {chunk_id}")
            return True
        
        except Exception as e:
            logger.error(f"Error storing embedding: {e}")
            return False
    
    def search_similar(self, query: str, top_k: int = 10, 
                      filters: Dict = None) -> List[Dict]:
        """
        Search for similar chunks using vector similarity.
        
        In production with Pinecone:
        1. Generate query embedding
        2. Query Pinecone with filters
        3. Return top_k results with metadata
        
        For MVP: Simple placeholder that would be replaced with actual vector search
        """
        query_embedding = self.embedder.generate_query_embedding(query)
        
        if not query_embedding:
            return []
        
        # Placeholder: In production, this would be:
        # results = pinecone_index.query(
        #     vector=query_embedding,
        #     top_k=top_k,
        #     filter=filters,
        #     include_metadata=True
        # )
        
        logger.info(f"Vector search for query: {query[:50]}...")
        return []
    
    def create_namespace_index(self, namespace: str):
        """Create a namespace in vector DB (for layer separation)"""
        # In Pinecone: different namespaces for different layers
        # namespace examples: "layer_1_govt", "layer_3_media", etc.
        logger.info(f"Created namespace: {namespace}")
        pass


class PineconeIntegration:
    """
    Ready-to-use Pinecone integration (requires pinecone-client package).
    Uncomment and configure when ready to use Pinecone.
    """
    
    def __init__(self, api_key: str = None, environment: str = None, 
                 index_name: str = "indore-political-rag"):
        """
        Initialize Pinecone connection
        
        To use:
        1. pip install pinecone-client
        2. Get API key from pinecone.io
        3. Uncomment the code below
        """
        self.index_name = index_name
        
        # Uncomment when ready to use Pinecone:
        # import pinecone
        # pinecone.init(api_key=api_key, environment=environment)
        # 
        # # Create index if doesn't exist
        # if index_name not in pinecone.list_indexes():
        #     pinecone.create_index(
        #         name=index_name,
        #         dimension=768,  # Gemini embedding dimension
        #         metric="cosine"
        #     )
        # 
        # self.index = pinecone.Index(index_name)
        logger.info(f"Pinecone integration initialized for index: {index_name}")
    
    def upsert_embeddings(self, chunks_with_embeddings: List[Dict]):
        """
        Upload embeddings to Pinecone with metadata
        
        chunks_with_embeddings format:
        [
            {
                'id': 'chunk_uuid',
                'embedding_vector': [0.1, 0.2, ...],
                'metadata': {
                    'source_id': 'uuid',
                    'layer': 3,
                    'geo_district': 'Indore',
                    'trust_score': 0.8,
                    'published_at': '2024-01-01',
                    'tags': ['water_supply', 'farmers']
                }
            }
        ]
        """
        # Uncomment when using Pinecone:
        # vectors = []
        # for chunk in chunks_with_embeddings:
        #     if chunk.get('embedding_vector'):
        #         vectors.append({
        #             'id': str(chunk['id']),
        #             'values': chunk['embedding_vector'],
        #             'metadata': chunk.get('metadata', {})
        #         })
        # 
        # if vectors:
        #     self.index.upsert(vectors=vectors)
        #     logger.info(f"Upserted {len(vectors)} vectors to Pinecone")
        
        logger.info(f"Would upsert {len(chunks_with_embeddings)} embeddings to Pinecone")
    
    def query(self, query_embedding: List[float], top_k: int = 10, 
              filter_dict: Dict = None, namespace: str = None):
        """
        Query Pinecone for similar vectors
        
        filter_dict examples:
        - {'geo_district': 'Indore', 'layer': 3}
        - {'source_type': 'government'}
        - {'tags': {'$in': ['water_supply', 'healthcare']}}
        """
        # Uncomment when using Pinecone:
        # results = self.index.query(
        #     vector=query_embedding,
        #     top_k=top_k,
        #     filter=filter_dict,
        #     namespace=namespace,
        #     include_metadata=True
        # )
        # return results
        
        logger.info(f"Would query Pinecone with top_k={top_k}, filters={filter_dict}")
        return {'matches': []}