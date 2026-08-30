from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import desc, or_, func
from typing import List
from app.database import get_db
from app.models.paper import Paper
from app.models.user import User
from app.schemas.papers import PaperCreate, PaperOut, PaperUpdate
from app.auth.auth import get_current_user, admin_or_educator
from app.routes.announcements import create_automatic_announcement


router = APIRouter()

APPROVED_FILTER = or_(func.lower(Paper.status) == "approved", Paper.status.is_(None))


def _is_publisher(user: User) -> bool:
    return (user.role or "").lower() in ("admin", "educator")


def _announce_paper(paper: Paper, db: Session) -> None:
    create_automatic_announcement(
        content_type="paper",
        content_id=paper.id,
        title=paper.title,
        image_url=None,
        db=db,
    )


@router.post("/create_paper", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def create_paper(
    paper_data: PaperCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaperOut:
    paper_status = "approved" if _is_publisher(current_user) else "pending"

    new_paper = Paper(
        title=paper_data.title,
        journal=paper_data.journal,
        authors=paper_data.authors,
        date=paper_data.date,
        url=str(paper_data.url),
        abstract=paper_data.abstract,
        conference_place=paper_data.conference_place,
        doi=paper_data.doi,
        paper_type=paper_data.paper_type,
        keywords=paper_data.keywords,
        user_id=current_user.id,
        status=paper_status,
    )
    db.add(new_paper)
    db.flush()

    if paper_status == "approved":
        _announce_paper(new_paper, db)

    db.commit()
    db.refresh(new_paper)
    return new_paper


@router.get("/get_paper/{id}", response_model=PaperOut)
def get_paper(id: int, db: Session = Depends(get_db)) -> PaperOut:
    paper = db.query(Paper).options(selectinload(Paper.user)).filter(Paper.id == id).first()
    if not paper:
        raise HTTPException(status_code=404, detail="Research paper not found")
    if (paper.status or "approved").lower() != "approved":
        raise HTTPException(status_code=404, detail="Research paper not found")
    return paper


@router.get("/get_papers", response_model=List[PaperOut])
def get_papers(db: Session = Depends(get_db)) -> List[PaperOut]:
    papers = (
        db.query(Paper)
        .options(selectinload(Paper.user))
        .filter(APPROVED_FILTER)
        .order_by(desc(Paper.id))
        .all()
    )
    return papers


@router.get("/get_all_papers", response_model=List[PaperOut])
def get_all_papers(
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_educator),
) -> List[PaperOut]:
    return (
        db.query(Paper)
        .options(selectinload(Paper.user))
        .order_by(desc(Paper.id))
        .all()
    )


@router.get("/get_userPapers", response_model=List[PaperOut])
def get_user_papers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[PaperOut]:
    return (
        db.query(Paper)
        .options(selectinload(Paper.user))
        .filter(Paper.user_id == current_user.id)
        .order_by(desc(Paper.id))
        .all()
    )


@router.put("/update_paper/{paper_id}", response_model=PaperOut)
def update_paper(
    paper_id: int,
    paper_data: PaperUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_educator),
) -> PaperOut:
    db_paper = db.query(Paper).options(selectinload(Paper.user)).filter(Paper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Research paper not found")

    prev_status = (db_paper.status or "").strip().lower()
    was_approved = prev_status == "approved"
    role = (db_paper.user_role or "").lower()
    is_user_paper = bool(db_paper.user_id) and role not in ("admin", "educator")

    if paper_data.title is not None:
        db_paper.title = paper_data.title
    if paper_data.journal is not None:
        db_paper.journal = paper_data.journal
    if paper_data.authors is not None:
        db_paper.authors = paper_data.authors
    if paper_data.date is not None:
        db_paper.date = paper_data.date
    if paper_data.url is not None:
        db_paper.url = str(paper_data.url)
    if paper_data.abstract is not None:
        db_paper.abstract = paper_data.abstract
    if paper_data.conference_place is not None:
        db_paper.conference_place = paper_data.conference_place
    if paper_data.doi is not None:
        db_paper.doi = paper_data.doi
    if paper_data.paper_type is not None:
        db_paper.paper_type = paper_data.paper_type
    if paper_data.keywords is not None:
        db_paper.keywords = paper_data.keywords
    if paper_data.status is not None:
        db_paper.status = paper_data.status.strip().lower()
    if paper_data.message is not None:
        db_paper.message = paper_data.message

    now_status = (db_paper.status or "").strip().lower()
    now_approved = now_status == "approved"
    if is_user_paper and now_status != prev_status and now_status in ("approved", "rejected"):
        create_automatic_announcement(
            content_type="paper_submission",
            content_id=db_paper.id,
            title=now_status,
            image_url=None,
            db=db,
            user_id=db_paper.user_id,
        )
    if now_approved and not was_approved:
        _announce_paper(db_paper, db)

    db.commit()
    db.refresh(db_paper)
    return db_paper


@router.delete("/delete_paper/{paper_id}", status_code=200)
def delete_paper(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(admin_or_educator),
) -> JSONResponse:
    db_paper = db.query(Paper).filter(Paper.id == paper_id).first()
    if not db_paper:
        raise HTTPException(status_code=404, detail="Research paper not found")

    db.delete(db_paper)
    db.commit()
    return JSONResponse(content={"message": "Research paper deleted successfully"})
