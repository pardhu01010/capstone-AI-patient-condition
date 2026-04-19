from qdrant_client import QdrantClient
from backend.services.rag import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, PROTOCOL_LIBRARY

def seed_qdrant():
    print(f"Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY if QDRANT_API_KEY else None)
    
    # Qdrant client with fastembed handles vectorization and collection creation automatically via `add`
    # Just need documents and their metadata
    
    documents = []
    metadata = []
    ids = []
    
    for i, protocol in enumerate(PROTOCOL_LIBRARY):
        # We index a descriptive text that captures the condition
        docs_text = f"Title: {protocol['title']}. Symptoms and conditions: {', '.join(protocol['keywords'])}. Action: {protocol['detail']}"
        documents.append(docs_text)
        metadata.append({"title": protocol["title"], "detail": protocol["detail"]})
        ids.append(i + 1)
        
    print(f"Adding {len(documents)} protocols to Qdrant collection '{COLLECTION_NAME}'...")
    
    # This will automatically download a fastembed model and encode on CPU
    client.add(
        collection_name=COLLECTION_NAME,
        documents=documents,
        metadata=metadata,
        ids=ids
    )
    
    print("Seeding complete!")

if __name__ == "__main__":
    seed_qdrant()
