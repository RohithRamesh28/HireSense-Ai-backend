

import openai
import os
import pdfplumber
import json
from dotenv import load_dotenv


load_dotenv() #only for openAI now
openai.api_key = os.getenv("OPENAI_API_KEY")

def extract_text_from_pdf(file_path):
    """
    Extract text from all pages of a PDF using pdfplumber.
    """
    with pdfplumber.open(file_path) as pdf:
        text = "\n".join(
            page.extract_text() for page in pdf.pages if page.extract_text()
        )
    return text


def call_openai_resume_parser(text):
    """
    Call OpenAI's GPT model to parse resume text and return structured JSON.
    """
    system_prompt = (
        "You are an expert resume parser. Extract the following fields from the text and return a valid JSON:\n"
        "- name\n- email\n- phone\n- skills (as a list)\n- education (brief summary)\n- experience (brief summary)"
    )

    user_prompt = f"Resume Text:\n{text[:3500]}"  

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
        parsed_json = json.loads(parsed)
    except json.JSONDecodeError:
        parsed_json = eval(parsed)

    return parsed_json


def extract_resume_data_via_ai(file_path):
    """
    Full pipeline: extract text → parse with OpenAI → split metadata & vector content
    """
    text = extract_text_from_pdf(file_path)
    parsed = call_openai_resume_parser(text)

    metadata = {
        "name": parsed.get("name"),
        "email": parsed.get("email"),
        "phone": parsed.get("phone"),
        "skills": parsed.get("skills"),
        "education": parsed.get("education"),
        "experience": parsed.get("experience"),
    }

    content_for_embedding = (
        f"Skills: {metadata['skills']}\n"
        f"Education: {metadata['education']}\n"
        f"Experience: {metadata['experience']}"
    )

    return metadata, content_for_embedding
