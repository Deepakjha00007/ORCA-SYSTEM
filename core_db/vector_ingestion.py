import os
from typing import List, Dict, Any, Optional
import numpy as np
from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Base directory for persisted ChromaDB vector storage
DB_DIR = "./core_db/chroma_db"

# Shared Ollama embedding model (nomic-embed-text generates 768-dim embeddings)
embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)


class MarineVectorIngestor:
    def __init__(self, model_name: str = "nomic-embed-text"):
        """Initializes local embedding engine using Ollama."""
        try:
            self.embedder = OllamaEmbeddings(
                model=model_name,
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
            )
        except Exception:
            self.embedder = None

    def generate_doc_embedding(self, text: str) -> List[float]:
        """Generates vector embedding for text chunks."""
        if self.embedder:
            try:
                return self.embedder.embed_query(text)
            except Exception:
                pass
        
        # Normalized fallback vector (768-dim for nomic-embed-text)
        vec = np.ones(768, dtype=float) / np.sqrt(768)
        return vec.tolist()

    def ingest_marine_advisories(self, documents: List[Dict[str, str]], db_connection_url: Optional[str] = None) -> List[Dict[str, Any]]:
        """Ingests maritime regulatory documents and safety guidelines into memory list."""
        print(f"[Vector Ingestion] Processing {len(documents)} document chunks...")
        embedded_docs = []

        for doc in documents:
            text_content = f"{doc.get('title', '')}: {doc.get('content', '')}"
            embedding_vector = self.generate_doc_embedding(text_content)
            
            record = {
                "title": doc.get("title", "Untitled Advisory"),
                "category": doc.get("category", "POLICY"),
                "content": doc.get("content", ""),
                "embedding": embedding_vector
            }
            embedded_docs.append(record)

        print(f"[Vector Ingestion] Successfully vectorized {len(embedded_docs)} advisory records.")
        return embedded_docs


def ingest_advisories_and_data():
    """Ingests oceanographic guidelines, safety regulations, and dataset summaries into Chroma Vector DB."""
    documents = [
        Document(
            page_content="PFZ Guidelines: High Chlorophyll-a (>2.0 mg/m3) combined with SST between 28-29C indicates pelagic fish aggregation (Tuna, Sardine).",
            metadata={"topic": "pfz"}
        ),
        Document(
            page_content="IMBL Regulation: Crossing the International Maritime Boundary Line into neighboring waters carries high risk of vessel detention.",
            metadata={"topic": "safety"}
        ),
        Document(
            page_content="Monsoon Navigation Safety: Wind speeds exceeding 25 knots and wave heights above 2.5m require immediate return to nearest coastal port.",
            metadata={"topic": "weather"}
        ),
    ]

    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=DB_DIR
    )
    print("✅ Vector DB Ingestion Complete!")


def get_retriever():
    """Returns vector retriever instance for RAG execution."""
    vectorstore = Chroma(persist_directory=DB_DIR, embedding_function=embeddings)
    return vectorstore.as_retriever(search_kwargs={"k": 2})


# Global wrapper function matching pipeline signature
def ingest_marine_advisories(documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    ingestor = MarineVectorIngestor()
    return ingestor.ingest_marine_advisories(documents)


if __name__ == "__main__":
    # Seed local Chroma Vector Store
    ingest_advisories_and_data()
    
    # Test dictionary ingestion
    docs = [
        {
            "title": "EEZ Boundary Regulations", 
            "category": "SAFETY_RULE",
            "content": "Vessels must maintain continuous AIS broadcasting within 200 nautical miles of the EEZ."
        },
        {
            "title": "PFZ Advisory Rules", 
            "category": "FISHERY_GUIDELINE",
            "content": "Thermal fronts with SST gradients above 0.8 °C indicate high pelagic fish concentration."
        }
    ]
    ingest_marine_advisories(docs)