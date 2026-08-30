import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.models.benchmarks import Benchmark
from app.schemas.benchmarks import BenchmarkResponse
from app.database import get_db  
from app.auth.auth import get_current_user

# For triggering automatic announcements & notification alerts
from app.routes.announcements import create_automatic_announcement 

router = APIRouter(
    tags=["Benchmarks"]
)

UPLOAD_DIR = "uploads" 

@router.post("/create_benchmark", response_model=BenchmarkResponse)
def create_benchmark(
    name: str = Form(...),
    description: str = Form(...),
    contributor_name: Optional[str] = Form(None),
    contributor_institution: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # Sent as a comma-separated string from frontend form data
    bibtex_citation: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
    # current_user: dict = Depends(get_current_user) # Uncomment to enforce admin-only auth later
):
    # Check if name already exists
    existing = db.query(Benchmark).filter(Benchmark.name == name).first()
    if existing:
        raise HTTPException(status_code=400, detail="A benchmark with this name already exists.")

    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    file_extension = os.path.splitext(file.filename)[1]
    if file_extension.lower() != '.zip':
        raise HTTPException(status_code=400, detail="Only compressed .zip file uploads are accepted.")
        
    safe_filename = f"{name.replace(' ', '_').lower()}{file_extension}"
    target_path = os.path.join(UPLOAD_DIR, safe_filename)

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file locally: {str(e)}")

    parsed_tags = [t.strip().lower() for t in tags.split(",")] if tags else []

    new_benchmark = Benchmark(
        name=name,
        description=description,
        contributor_name=contributor_name,
        contributor_institution=contributor_institution,
        tags=parsed_tags,
        file_path=target_path,
        bibtex_citation=bibtex_citation
    )
    
    db.add(new_benchmark)
    db.flush() 

    try:
        create_automatic_announcement(
            content_type="benchmark",
            content_id=new_benchmark.id,
            title=new_benchmark.name,
            image_url=None,
            db=db
        )
    except Exception as err:
        print(f"Non-blocking log warning: Failed to broadcast automatic alert triggers: {str(err)}")

    db.commit()
    db.refresh(new_benchmark)
    return new_benchmark


@router.get("/get_benchmarks", response_model=List[BenchmarkResponse])
def get_benchmarks(db: Session = Depends(get_db)):
    return db.query(Benchmark).order_by(Benchmark.created_at.desc()).all()


@router.get("/download_benchmark/{benchmark_id}")
def download_benchmark(benchmark_id: int, db: Session = Depends(get_db)):
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()
    if not benchmark or not os.path.exists(benchmark.file_path):
        raise HTTPException(status_code=404, detail="Requested benchmark file archive not found on server storage.")
    
    return FileResponse(
        path=benchmark.file_path,
        media_type="application/zip",
        filename=f"{benchmark.name.lower()}.zip"
    )


@router.delete("/delete_benchmark/{benchmark_id}", status_code=status.HTTP_200_OK)
def delete_benchmark(
    benchmark_id: int, 
    db: Session = Depends(get_db)
    # current_user: dict = Depends(get_current_user) # Uncomment to enforce admin-only auth later
):
    benchmark = db.query(Benchmark).filter(Benchmark.id == benchmark_id).first()
    if not benchmark:
        raise HTTPException(status_code=404, detail="Target benchmark record does not exist.")

    if os.path.exists(benchmark.file_path):
        try:
            os.remove(benchmark.file_path)
        except Exception as e:
            print(f"Non-blocking log warning: Failed to remove disk asset: {str(e)}")

    db.delete(benchmark)
    db.commit()
    return {"detail": "Benchmark asset and record clean dropped successfully."}