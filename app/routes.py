from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse
from app.parser import extract_resume_data_via_ai
from app.metadata_db_sqlite import add_resume_metadata, get_resume_metadata, get_resume_by_fingerprint
from app.jd_parser import extract_text_from_pdf, parse_job_description
from app.embeddings import add_resume_vector, search_similar_resumes, get_embedding
from app.utils import banded_score, get_jd_embedding_input, ats_score
import hashlib
import numpy as np
import uuid
import os
from datetime import datetime
from io import BytesIO
# real deal, everything happens here
router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


def hash_text(text: str):
    return hashlib.md5(text.encode()).hexdigest()


def is_valid_resume(metadata, resume_text):
    return resume_text and len(resume_text.strip()) > 50 and metadata.get("name") and metadata.get("email")


#download resumes happens here, 

@router.get("/view-resume/{resume_id}")
async def view_resume(resume_id: str):
    metadata = get_resume_metadata(resume_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="Resume not found")

    file_path = metadata.get("resume_path")
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Resume file missing")

    candidate_name = metadata.get("name")
    if candidate_name and candidate_name.strip():
        # Clean up name (remove invalid characters from filename)
        safe_name = "".join(c for c in candidate_name if c.isalnum() or c in (' ', '-', '_')).strip()
        download_filename = f"{safe_name}.pdf"
    else:
        download_filename = os.path.basename(file_path)

    return FileResponse(
        path=file_path,
        filename=download_filename,
        media_type="application/pdf"
    )   


# you can upload resumes to the db here, why you ask well you need to upload somehow 
@router.post("/upload/")
async def upload_resumes(files: list[UploadFile] = File(...)):
    results = []
    for file in files:
        content = await file.read()
        metadata, resume_text = extract_resume_data_via_ai(BytesIO(content))

        if not is_valid_resume(metadata, resume_text):
            results.append({"filename": file.filename, "status": "invalid", "message": "Not a valid resume"})
            continue

        fingerprint = hash_text(resume_text)
        existing = get_resume_by_fingerprint(fingerprint)

        if existing:
            results.append({
                "resume_id": existing["id"],
                "name": existing["name"],
                "email": existing["email"],
                "resume_path": existing["resume_path"],
                "view_url": f"/view-resume/{existing['id']}",
                "fingerprint": fingerprint,
                "status": "duplicate"
            })
            continue

        resume_id = str(uuid.uuid4())
        save_path = os.path.join(UPLOAD_DIR, f"{resume_id}_{file.filename}")
        with open(save_path, "wb") as f:
            f.write(content)

        metadata.update({
            "resume_path": save_path,
            "uploaded_at": datetime.now().isoformat(),
            "fingerprint": fingerprint
        })

        add_resume_metadata(resume_id, metadata)
        add_resume_vector(resume_id, resume_text)

        results.append({
            "resume_id": resume_id,
            "name": metadata["name"],
            "email": metadata["email"],
            "resume_path": save_path,
            "view_url": f"/view-resume/{resume_id}",
            "status": "stored",
            "fingerprint": fingerprint
        })

    return {"status": "success", "matches": results}

#finds resumes in the entire db with respect to jd
@router.post("/match/")
async def match_resumes_with_jd(mode: str = Form(...), text: str = Form(None), file: UploadFile = File(None), top_k: int = Form(5)):
    try:
        if mode == "text":
            if not text:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing JD text."})
            jd_text = text
        elif mode == "pdf":
            if not file:
                return JSONResponse(status_code=400, content={"status": "error", "message": "Missing JD PDF."})
            jd_text = extract_text_from_pdf(BytesIO(await file.read()))
        else:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid mode."})

        parsed_jd = parse_job_description(jd_text)
        jd_embedding_input = (
            f"Skills: {parsed_jd['skills']}\n"
            f"Education: {parsed_jd['education']}\n"
            f"Experience: {parsed_jd['experience']}"
        )

        matches = search_similar_resumes(jd_embedding_input, top_k=top_k)

        seen = set()
        matched_resumes = []
        for match in matches:
            resume_id = match["resume_id"]
            if resume_id in seen:
                continue
            seen.add(resume_id)

            metadata = get_resume_metadata(resume_id)
            if metadata:
                raw_score = float(match["score"])
                metadata["score"] = banded_score(raw_score)
                metadata["view_url"] = f"/view-resume/{resume_id}"
                matched_resumes.append(metadata)

        unique = {}
        for r in matched_resumes:
            fp = r.get("fingerprint")
            if not fp:
                continue
            if fp not in unique or r["score"] > unique[fp]["score"]:
                unique[fp] = r

        final_results = list(unique.values())
        final_results.sort(key=lambda x: x["score"], reverse=True)

        return {"status": "success", "matches": final_results}

    except Exception as e:
        print("❌ Match error:", e)
        return {"status": "error", "message": str(e)}

#here you can directly upload your resumes and get result in air, new resumes will be saved insisde the db and the duplicates will be thrown out, this is done through hasing
@router.post("/instant-upload-match/")
async def instant_upload_match(
    mode: str = Form(...),
    text: str = Form(None),
    file: UploadFile = File(None),
    files: list[UploadFile] = File(...)
):
    results = []
    try:
        if mode == "text":
            jd_text = text
        elif mode == "pdf":
            jd_text = extract_text_from_pdf(BytesIO(await file.read()))
        else:
            return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid JD mode."})

        parsed_jd = parse_job_description(jd_text)
        jd_input = get_jd_embedding_input(parsed_jd)
        jd_vector = get_embedding(jd_input)

        for f in files:
            content = await f.read()
            metadata, resume_text = extract_resume_data_via_ai(BytesIO(content))

            if not is_valid_resume(metadata, resume_text):
                results.append({
                    "filename": f.filename,
                    "status": "invalid",
                    "message": "Not a valid resume"
                })
                continue

            fingerprint = hash_text(resume_text)
            existing = get_resume_by_fingerprint(fingerprint)

            resume_vector = get_embedding(resume_text)
            similarity = float(np.dot(jd_vector, resume_vector))
            score = banded_score(round(min(similarity, 1.0), 3))

            if existing:
                results.append({
                    "resume_id": existing["id"],
                    "name": existing["name"],
                    "email": existing["email"],
                    "score": score,
                    "resume_path": existing["resume_path"],
                    "view_url": f"/view-resume/{existing['id']}",
                    "status": "duplicate",
                    "fingerprint": fingerprint
                })
                continue

            resume_id = str(uuid.uuid4())
            save_path = os.path.join(UPLOAD_DIR, f"{resume_id}_{f.filename}")
            with open(save_path, "wb") as out:
                out.write(content)

            metadata.update({
                "resume_path": save_path,
                "uploaded_at": datetime.now().isoformat(),
                "fingerprint": fingerprint
            })

            add_resume_metadata(resume_id, metadata)
            add_resume_vector(resume_id, resume_text)

            results.append({
                "resume_id": resume_id,
                "name": metadata["name"],
                "email": metadata["email"],
                "score": score,
                "resume_path": save_path,
                "view_url": f"/view-resume/{resume_id}",
                "status": "stored",
                "fingerprint": fingerprint
            })

        return {"status": "success", "matches": results}
    except Exception as e:
        print("❌ Instant match error:", e)
        return {"status": "error", "message": str(e)}

#Checks for ats score through openAI
@router.post("/ats-score/")
async def ats_only_scoring(files: list[UploadFile] = File(...)):
    results = []
    for f in files:
        content = await f.read()
        metadata, resume_text = extract_resume_data_via_ai(BytesIO(content))

        if not is_valid_resume(metadata, resume_text):
            results.append({
                "filename": f.filename,
                "status": "invalid",
                "message": "Not a valid resume"
            })
            continue

        fingerprint = hash_text(resume_text)
        existing = get_resume_by_fingerprint(fingerprint)

        ats_result = ats_score(resume_text)
        score = ats_result.get("score", 0)
        details = ats_result.get("details", {})

        result = {
            "score": score,
            "details": details,
            "fingerprint": fingerprint
        }

        if existing:
            result.update({
                "resume_id": existing["id"],
                "name": existing["name"],
                "email": existing["email"],
                "resume_path": existing["resume_path"],
                "view_url": f"/view-resume/{existing['id']}",
                "status": "duplicate"
            })
        else:
            resume_id = str(uuid.uuid4())
            save_path = os.path.join(UPLOAD_DIR, f"{resume_id}_{f.filename}")
            with open(save_path, "wb") as out:
                out.write(content)

            metadata.update({
                "resume_path": save_path,
                "uploaded_at": datetime.now().isoformat(),
                "fingerprint": fingerprint
            })

            add_resume_metadata(resume_id, metadata)
            add_resume_vector(resume_id, resume_text)

            result.update({
                "resume_id": resume_id,
                "name": metadata["name"],
                "email": metadata["email"],
                "resume_path": save_path,
                "view_url": f"/view-resume/{resume_id}",
                "status": "stored"
            })

        results.append(result)
    return {"status": "success", "matches": results}

#checks for ATS/JD score with openAI for ats, and my cool db for jd, now I have given 50/50 weightage for both, but if you want you can change to you preference,
#see you can y should i come here in backend for that dont you think its cool to have this feature in the frontend. yes it is cool and i taught about that while writting 
#this comment so next commit will have that hopefully
@router.post("/ats-jd-score/")
async def ats_with_jd_scoring(
    mode: str = Form(...),
    text: str = Form(None),
    file: UploadFile = File(None),
    resumes: list[UploadFile] = File(...)
):
    results = []
    if mode == "text":
        jd_text = text
    elif mode == "pdf":
        jd_text = extract_text_from_pdf(BytesIO(await file.read()))
    else:
        return JSONResponse(status_code=400, content={"status": "error", "message": "Invalid JD mode."})

    parsed_jd = parse_job_description(jd_text)
    jd_input = get_jd_embedding_input(parsed_jd)
    jd_vector = get_embedding(jd_input)

    for f in resumes:
        content = await f.read()
        metadata, resume_text = extract_resume_data_via_ai(BytesIO(content))

        if not is_valid_resume(metadata, resume_text):
            results.append({
                "filename": f.filename,
                "status": "invalid",
                "message": "Not a valid resume"
            })
            continue

        fingerprint = hash_text(resume_text)
        existing = get_resume_by_fingerprint(fingerprint)

        resume_vector = get_embedding(resume_text)
        similarity = float(np.dot(jd_vector, resume_vector))
        jd_score_value = banded_score(round(min(similarity, 1.0), 3))


        ats_result = ats_score(resume_text)
        ats_score_value = ats_result.get("score", 0)
        final_score = round((ats_score_value + jd_score_value) / 2, 2)

        base = {
            "score": final_score,
            "ats_score": ats_score_value,
            "jd_score": jd_score_value,
            "details": ats_result.get("details", {}),
            "fingerprint": fingerprint
        }

        if existing:
            base.update({
                "resume_id": existing["id"],
                "name": existing["name"],
                "email": existing["email"],
                "resume_path": existing["resume_path"],
                "view_url": f"/view-resume/{existing['id']}",
                "status": "duplicate"
            })
        else:
            resume_id = str(uuid.uuid4())
            save_path = os.path.join(UPLOAD_DIR, f"{resume_id}_{f.filename}")
            with open(save_path, "wb") as out:
                out.write(content)

            metadata.update({
                "resume_path": save_path,
                "uploaded_at": datetime.now().isoformat(),
                "fingerprint": fingerprint
            })

            add_resume_metadata(resume_id, metadata)
            add_resume_vector(resume_id, resume_text)

            base.update({
                "resume_id": resume_id,
                "name": metadata["name"],
                "email": metadata["email"],
                "resume_path": save_path,
                "view_url": f"/view-resume/{resume_id}",
                "status": "stored"
            })

        results.append(base)
    return {"status": "success", "matches": results}
