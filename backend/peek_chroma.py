# ============================================================
# GenResearch — ChromaDB Data Extractor
# Use this to verify stored chunks and metadata
# ============================================================
import chromadb
from chromadb.config import Settings as ChromaSettings
from pathlib import Path
import json

# Configuration (matches your config.py)
CHROMA_PATH = str(Path(__file__).resolve().parent / "chroma_db")

def peek_chroma():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    
    print(f"\n--- ChromaDB Inspection @ {CHROMA_PATH} ---")
    
    # 1. List all collections
    collections = client.list_collections()
    if not collections:
        print("No collections found. The database is empty.")
        return

    print(f"Found {len(collections)} collection(s):")
    for col in collections:
        print(f" - Collection: {col.name}")
        
        # 2. Get data from the collection
        # We'll get the first 5 items as a sample
        data = col.get(limit=5, include=["documents", "metadatas"])
        
        count = col.count()
        print(f"   Total Chunks: {count}")
        
        if count > 0:
            print("   Sample Data (First 5 chunks):")
            for i in range(len(data['ids'])):
                print(f"   [{i+1}] ID: {data['ids'][i]}")
                print(f"       Metadata: {json.dumps(data['metadatas'][i], indent=7)}")
                # Print first 100 chars of the text
                snippet = data['documents'][i][:100].replace('\n', ' ')
                print(f"       Text Snippet: {snippet}...")
                print("-" * 30)
        else:
            print("   (Collection is empty)")

if __name__ == "__main__":
    peek_chroma()
