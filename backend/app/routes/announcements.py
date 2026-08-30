from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.announcement import AnnouncementCreate
from app.auth.auth import get_optional_user
from app.models.user import User

REVIEW_CONTENT_TYPES = (
    "exercise_submission",
    "community_lab",
    "community_video",
    "paper_submission",
)

router = APIRouter(tags=["announcements"])

LAB_LOGO_DATA_URI = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='320' height='180' viewBox='0 0 320 180'>"
    "<rect width='320' height='180' rx='20' fill='%23111827'/>"
    "<rect x='20' y='20' width='280' height='140' rx='16' fill='%230f766e' opacity='0.22'/>"
    "<text x='160' y='98' text-anchor='middle' fill='white' font-family='Arial, sans-serif' font-size='44' font-weight='700'>LAB</text>"
    "</svg>"
)

EXERCISE_LOGO_DATA_URI = (
    "data:image/svg+xml;utf8,"
    "<svg xmlns='http://www.w3.org/2000/svg' width='320' height='180' viewBox='0 0 320 180'>"
    "<rect width='320' height='180' rx='20' fill='%23111827'/>"
    "<rect x='20' y='20' width='280' height='140' rx='16' fill='%23b45309' opacity='0.24'/>"
    "<text x='160' y='92' text-anchor='middle' fill='white' font-family='Arial, sans-serif' font-size='34' font-weight='700'>EXERCISE</text>"
    "</svg>"
)


def _normalize_image(image):
    if image is None:
        return ""
    cleaned = image.strip()
    return cleaned or ""


def _normalize_text(value):
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _resolve_content_details(content_type, content_id, custom_image, custom_title, db):
    """
    Used ONLY by manual admin creation to fetch titles/images from the database 
    when they provide just an ID.
    """
    normalized_type = content_type.strip().lower()
    target_id = int(content_id or 0)

    if normalized_type == "general":
        return (custom_title.strip() if custom_title else "Notice"), _normalize_image(custom_image)

    if normalized_type == "lab":
        try:
            lookup = text("SELECT title FROM community_labs WHERE id = :id LIMIT 1;")
            db_title = db.execute(lookup, {"id": target_id}).scalar()
            if not db_title:
                raise ValueError(f"Lab ID {target_id} does not exist.")
            return db_title.strip(), LAB_LOGO_DATA_URI
        except Exception as err:
            print(f"Lab lookup failed for id {target_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automated verification failed: Lab ID {target_id} could not be resolved."
            )

    if normalized_type == "exercise":
        try:
            lookup = text("SELECT title FROM exercises WHERE id = :id LIMIT 1;")
            db_title = db.execute(lookup, {"id": target_id}).scalar()
            if not db_title:
                raise ValueError(f"Exercise ID {target_id} does not exist.")
            return db_title.strip(), EXERCISE_LOGO_DATA_URI
        except Exception as err:
            print(f"Exercise lookup failed for id {target_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automated verification failed: Exercise ID {target_id} could not be resolved."
            )

    if normalized_type == "video":
        try:
            lookup = text("SELECT title, url FROM community_videos WHERE id = :id LIMIT 1;")
            row = db.execute(lookup, {"id": target_id}).fetchone()
            if not row:
                raise ValueError(f"Video ID {target_id} does not exist.")
            
            resolved_title = row[0].strip()
            resolved_image = _normalize_image(custom_image) if custom_image else _normalize_image(row[1])
            return resolved_title, resolved_image
        except Exception as err:
            print(f"Video lookup failed for id {target_id}: {err}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Automated verification failed: Video ID {target_id} could not be resolved."
            )

    return (custom_title.strip() if custom_title else ""), _normalize_image(custom_image)


# Automatic announcement trigger
def create_automatic_announcement(
    content_type: str,
    content_id: int,
    title: str,
    image_url: str = None,
    db: Session = None,
    user_id: int = None,
):
    """
    Fast, zero-lookup hook called inside upload routers (video, lab, exercise).
    Uses the data already present in memory to immediately commit.
    Pass user_id for accept/reject notices so only that member sees them.
    """
    if db is None:
        print("Automatic announcement failed: No active database session provided.")
        return {"error": "No database session provided"}

    try:
        normalized_type = content_type.strip().lower()
        
        # Assign logos immediately without querying the database again
        if normalized_type == "lab":
            resolved_image = LAB_LOGO_DATA_URI
        elif normalized_type == "exercise":
            resolved_image = EXERCISE_LOGO_DATA_URI
        else:
            resolved_image = image_url.strip() if image_url else ""

        params = {
            "content_type": normalized_type,
            "content_id": int(content_id or 0),
            "title": title.strip(),
            "message": None, 
            "image": resolved_image,
            "user_id": int(user_id) if user_id else None,
        }

        query = text(
            """
            INSERT INTO announcements (content_type, content_id, title, message, image, user_id, created_at, updated_at)
            VALUES (:content_type, :content_id, :title, :message, :image, :user_id, NOW(), NOW())
            RETURNING id;
            """
        )
        db.execute(query, params)
        return {"status": "success"}

    except Exception as err:
        print(f"Error executing backend automated create_automatic_announcement: {err}")
        return {"error": str(err)}
    

@router.post("/create_announcement", status_code=status.HTTP_201_CREATED)
def create_announcement(payload: AnnouncementCreate, db: Session = Depends(get_db)):
    """
    Used exclusively by Admins via the front-end dashboard to manually post news.
    """
    try:
        content_type = "general"
        content_id = 0
        message = _normalize_text(payload.message)

        if not payload.title or not message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Both title and message are required for general announcements.",
            )

        resolved_title, resolved_image = _resolve_content_details(
            content_type, content_id, payload.image, payload.title, db
        )

        query = text(
            """
            INSERT INTO announcements (content_type, content_id, title, message, image, created_at, updated_at)
            VALUES (:content_type, :content_id, :title, :message, :image, NOW(), NOW())
            RETURNING id, content_type, content_id, title, message, image, created_at, updated_at;
            """
        )

        params = {
            "content_type": content_type,
            "content_id": content_id,
            "title": resolved_title,
            "message": message,
            "image": resolved_image,
        }

        result = db.execute(query, params)
        new_row = result.fetchone()
        db.commit()

        if not new_row:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Announcement could not be created.",
            )

        return {
            "id": new_row[0],
            "content_type": new_row[1],
            "content_id": new_row[2],
            "title": new_row[3],
            "message": new_row[4],
            "image": new_row[5],
            "created_at": new_row[6].isoformat() if new_row[6] else None,
            "updated_at": new_row[7].isoformat() if new_row[7] else None,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as err:
        db.rollback()
        print(f"Database error writing log entry: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database operation failure writing entry logs.",
        )


@router.get("/get_announcements")
def get_announcements(
    page: int = Query(1, ge=1),
    limit: int = Query(6, ge=1),
    personal: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    offset = (page - 1) * limit
    review_list = ", ".join(f"'{t}'" for t in REVIEW_CONTENT_TYPES)
    public_clause = f"(user_id IS NULL AND content_type NOT IN ({review_list}))"
    if personal:
        if not current_user:
            return {"total": 0, "page": page, "limit": limit, "items": []}
        visibility = "user_id = :uid"
        params = {"limit": limit, "offset": offset, "uid": current_user.id}
        count_params = {"uid": current_user.id}
    elif current_user:
        visibility = f"({public_clause} OR user_id = :uid)"
        params = {"limit": limit, "offset": offset, "uid": current_user.id}
        count_params = {"uid": current_user.id}
    else:
        visibility = public_clause
        params = {"limit": limit, "offset": offset}
        count_params = {}

    try:
        count_query = text(f"SELECT COUNT(*) FROM announcements WHERE {visibility};")
        total_count = int(db.execute(count_query, count_params).scalar() or 0)

        items_query = text(
            f"""
            SELECT id, content_type, content_id, title, message, image, created_at, updated_at
            FROM announcements
            WHERE {visibility}
            ORDER BY created_at DESC, id DESC
            LIMIT :limit OFFSET :offset;
            """
        )
        result = db.execute(items_query, params).fetchall()

        items = [
            {
                "id": row[0],
                "content_type": row[1],
                "content_id": row[2],
                "title": row[3],
                "message": row[4],
                "image": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            }
            for row in result
        ]
        return {"total": total_count, "page": page, "limit": limit, "items": items}
    except Exception as err:
        print(f"Database error: {err}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.delete("/delete_announcement/{announcement_id}")
def delete_announcement(announcement_id: int, db: Session = Depends(get_db)):
    try:
        query = text("DELETE FROM announcements WHERE id = :id RETURNING id;")
        result = db.execute(query, {"id": announcement_id})
        deleted_row = result.fetchone()

        if not deleted_row:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Announcement record not found.",
            )

        db.commit()
        return {"message": "Successfully deleted record row connection reference."}
    except HTTPException:
        raise
    except Exception as err:
        db.rollback()
        print(f"Database error deleting log entry: {err}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to erase line row data from Database.",
        )