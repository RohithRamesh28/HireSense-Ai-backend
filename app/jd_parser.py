import openai
import os
import pdfplumber
from dotenv import load_dotenv
import json

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(file_path):
    with pdfplumber.open(file_path) as pdf:
        return "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )

import json

def parse_job_description(text: str):
    system_prompt = (
        "You are an expert recruiter assistant. Extract the following fields from this job description "
        "and return valid JSON only:\n"
        "- skills (as a list)\n"
        "- education (brief summary)\n"
        "- experience (brief summary)"
    )

    user_prompt = f"Job Description:\n{text[:3500]}"

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0,
    )

    parsed = response["choices"][0]["message"]["content"]

    try:
        return json.loads(parsed)
    except json.JSONDecodeError as e:
        print("❌ JSON parsing failed:", e)
        return {
            "skills": [],
            "education": "Not found",
            "experience": "Not found",
            "error": "LLM returned invalid JSON"
        }
