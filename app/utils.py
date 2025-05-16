import json
import re

import openai


def banded_score(similarity: float) -> float:
    if similarity > 0.63:
        return round(9.0 + (similarity - 0.63) * (10 - 9.0) / (1.0 - 0.63), 2)
    elif similarity > 0.5:
        return round(6.0 + (similarity - 0.5) * (9.0 - 6.0) / (0.63 - 0.5), 2)
    elif similarity > 0.3:
        return round(3.0 + (similarity - 0.3) * (6.0 - 3.0) / (0.5 - 0.3), 2)
    else:
        return round(similarity * 10, 2)

def get_jd_embedding_input(parsed_jd: dict) -> str:
    skills = parsed_jd.get("skills", [])
    skills_str = ", ".join(skills) if isinstance(skills, list) else str(skills)
    education = parsed_jd.get("education", "")
    experience = parsed_jd.get("experience", "")
    return f"Skills: {skills_str}\nEducation: {education}\nExperience: {experience}"


def ats_score(resume_text: str) -> dict:
    prompt = f"""
You are an ATS (Applicant Tracking System). Evaluate the resume below and score it out of 10, strictly based on structure, formatting consistency, and clarity of key sections like Experience, Education, and Skills. Be slightly critical and avoid being overly generous — only well-structured and cleanly formatted resumes should score 8 or above. Provide a short explanation with each score to justify the result.

Return:
{{
  "score": 8.0,
  "details": {{
    "summary": "...",
    "has_sections": {{
      "experience": true,
      "skills": true,
      ...
    }},
    "format_notes": "..."
  }}
}}
Resume:
\"\"\"{resume_text[:3500]}\"\"\"
"""
    ...


    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=600
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print("❌ ATS score GPT error:", e)
        return {
            "score": 0,
            "details": {
                "summary": "GPT error",
                "error": str(e)
            }
        }

