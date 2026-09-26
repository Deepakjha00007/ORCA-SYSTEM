import os
from langchain_ollama import ChatOllama
from core_db.vector_ingestion import get_retriever

llm = ChatOllama(
    model="llama3.2",
    temperature=0.2,
    base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
)

def run_rag_advisory(user_query: str, telemetry_context: str) -> str:
    # 1. Fetch relevant context from vector store
    retriever = get_retriever()
    docs = retriever.invoke(user_query)
    retrieved_knowledge = "\n".join([doc.page_content for doc in docs])
    
    # 2. Build RAG prompt with retrieved knowledge and live telemetry
    prompt = f"""
    You are ORCA Marine Intelligence Assistant.
    
    [RETRIEVED KNOWLEDGE]
    {retrieved_knowledge}
    
    [LIVE VESSEL TELEMETRY]
    {telemetry_context}
    
    [USER QUERY]
    {user_query}
    
    Provide a concise, high-priority maritime advisory using the retrieved knowledge and telemetry.
    """
    
    response = llm.invoke(prompt)
    return response.content