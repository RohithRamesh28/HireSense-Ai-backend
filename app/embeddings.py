import openai
import os
import faiss
import numpy as np
import json
from dotenv import load_dotenv

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

embedding_dim = 1536 
FAISS_FILE = "resume_index.faiss"
ID_MAP_FILE = "resume_ids.json"


if os.path.exists(FAISS_FILE):
    index = faiss.read_index(FAISS_FILE)
else:
    index = faiss.IndexFlatIP(embedding_dim)


if os.path.exists(ID_MAP_FILE):
    with open(ID_MAP_FILE, "r") as f:
        resume_id_map = json.load(f)
else:
    resume_id_map = []

def save_index():
    print(f"📝 Saving index with {len(resume_id_map)} IDs")
    faiss.write_index(index, FAISS_FILE)
    with open(ID_MAP_FILE, "w") as f:
        json.dump(resume_id_map, f)
    print(f"💾 Saved to {ID_MAP_FILE}")

def get_embedding(text: str) -> np.ndarray:
    response = openai.Embedding.create(
        input=[text],
        model="text-embedding-3-small"
    )
    vector = np.array(response["data"][0]["embedding"], dtype=np.float32)
    norm_vector = vector / np.linalg.norm(vector)  # ✅ Normalize for cosine
    return norm_vector

def add_resume_vector(resume_id: str, text: str):
    global resume_id_map
    vector = get_embedding(text)
    index.add(np.array([vector]))
    resume_id_map.append(resume_id)
    print(f"✅ Appended resume ID: {resume_id}")
    save_index()

def search_similar_resumes(job_desc_text: str, top_k: int = 5):
    if index.ntotal == 0:
        print("❌ FAISS index is empty.")
        return []

    top_k = min(top_k, len(resume_id_map))
    query_vector = get_embedding(job_desc_text)
    distances, indices = index.search(np.array([query_vector]), top_k)

    results = []
    for i, dist in zip(indices[0], distances[0]):
        if i < len(resume_id_map):
            similarity_score = round(float(dist), 3)  
            results.append({
                "resume_id": resume_id_map[i],
                "score": similarity_score
            })

    return results
