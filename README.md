# 🧠 Hiresense AI – Backend

This is the backend service for **Hiresense AI**, an intelligent resume screening and matching platform. It provides RESTful APIs for resume parsing, LLM-based matching, ATS scoring, and job description analysis using FastAPI.

---
🔗 **Frontend Repository**: [HireSense-Ai-frontend](https://github.com/RohithRamesh28/HireSense-Ai-frontend)
## 🚀 Features

- 📄 Resume Upload & Parsing (PDF)
- 🧠 LLM-based Resume-to-JD Matching
- 📊 ATS-Style Scoring
- 🔍 Fast Vector Search/DB (FAISS)
- 📝 JD Parsing via Text or PDF
- 👁 Inline Resume Download

---

## ⚙️ Tech Stack

- Python 3.10+
- FastAPI
- OpenAI API
- FAISS (for vector search/vector storage)
- PyMuPDF / pdfplumber (PDF parsing)
- Uvicorn (ASGI Server)

---

## 📦 Installation

### 1. Clone the repository
```bash
git clone https://github.com/RohithRamesh28/HireSense-Ai-backend.git
cd HireSense-Ai-backend

python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

2. Set up a virtual environment
python -m venv venv --> your environment name
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

3. Install dependencies
pip install -r requirements.txt

🔐 Environment Setup
OPENAI_API_KEY=your_openai_key_here
⚠️ Do not commit your .env file. It contains sensitive secrets.

▶️ Running the Server
Start the FastAPI server using Uvicorn on port 8070:
uvicorn main:app --reload --port 8070
⚠️ Make sure you use localhost:8070 — the frontend expects this URL for API communication.

```

📤 Upload & Match API Usage

POST /upload/: Upload resumes
POST /match/: Match resumes to JD (text or PDF)
POST /ats-score/: Get ATS score
POST /instant-upload-match/ - Match Resumes with Jd and resumes
POST /ats-jd-score/ - Get ATS score and JD combined
GET /view-resume/{resume_id}: download resume PDF

🧪 Sample .env.example
# Rename this file to .env and insert your actual key
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxx

✅ Notes
Only .pdf files are supported for resume and JD input.
Make sure to use port 8070 as it's the default expected by the frontend.

🛠️ Thanks for running the backend... but without the frontend, it's like hiring with your eyes closed. Don't forget to start the frontend too — or you'll be staring at ports like it's magic! 😄




