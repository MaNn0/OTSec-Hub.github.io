from fastapi import FastAPI
from app.auth import bcrypt_compat  # noqa: F401  — must load before passlib bcrypt
from app.routes import user, auth, educators, video, userProgress, pieProgress, lab, exercise, exerciseSubmission, communityLab, communityVideo, analytics, announcements, papers, benchmarks, community_interaction, news
from app import models

from app.database import engine, Base
from sqlalchemy import text
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv
import os
from fastapi.staticfiles import StaticFiles

# --- Rate Limiter Exception Handling ---
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

load_dotenv()

app = FastAPI()

# Attach Limiter from auth route to App State
app.state.limiter = auth.limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# Compress response bodies. Transparent to clients, which decompress automatically.
app.add_middleware(GZipMiddleware, minimum_size=1000)

#origins = [os.getenv("REACT_DOT_SERVER").strip(),
  #"http://localhost:3000"] #Allow Localhost for development
  
origins = [
    "https://otsec-hub.com",          #  actual live domain
    "https://www.otsec-hub.com",      #  live domain with www
    "http://localhost:3000"           # Keep this for local testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include routers
app.include_router(user.router, tags=["users"])
app.include_router(auth.router, prefix="/api/auth", tags=["authentication"])
app.include_router(educators.router, prefix="/api", tags=["educators"])
app.include_router(video.router, prefix="/api", tags=["videos"])
app.include_router(userProgress.router, prefix="/api", tags=["video_views"])
app.include_router(lab.router, prefix="/api", tags=["labs"])
app.include_router(announcements.router, prefix="/api", tags=["announcements"])
app.include_router(communityLab.router, prefix="/api", tags=["communityLab"])
app.include_router(communityVideo.router, prefix="/api", tags=["communityVideo"])
app.include_router(exercise.router, prefix="/api", tags=["exercises"])
app.include_router(pieProgress.router, prefix="/api/progress", tags=["pieProgress"])
app.include_router(exerciseSubmission.router, prefix="/api", tags=["exerciseSubmission"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(papers.router, prefix="/api", tags=["papers"])
app.include_router(benchmarks.router, prefix="/api")
app.include_router(community_interaction.router, prefix="/api", tags=["Community Interactions"])
app.include_router(news.router, prefix="/api", tags=["news"])

app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Initialize database
# Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

def _ensure_paper_review_columns():
    statements = [
        "ALTER TABLE papers ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
        "ALTER TABLE papers ADD COLUMN IF NOT EXISTS status VARCHAR DEFAULT 'approved'",
        "ALTER TABLE papers ADD COLUMN IF NOT EXISTS message VARCHAR",
        "ALTER TABLE papers ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT NOW()",
        "UPDATE papers SET status = 'approved' WHERE status IS NULL",
    ]
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except Exception as exc:
        print(f"Paper review column ensure skipped: {exc}")

_ensure_paper_review_columns()

def _ensure_site_stats_row():
    statements = [
        """
        CREATE TABLE IF NOT EXISTS site_stats (
            id INTEGER PRIMARY KEY,
            homepage_visits BIGINT NOT NULL DEFAULT 0
        )
        """,
        "INSERT INTO site_stats (id, homepage_visits) VALUES (1, 0) ON CONFLICT (id) DO NOTHING",
    ]
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except Exception as exc:
        print(f"Site stats ensure skipped: {exc}")

_ensure_site_stats_row()

def _ensure_announcement_defaults():
    statements = [
        "ALTER TABLE announcements ALTER COLUMN content_type SET DEFAULT 'general'",
        "ALTER TABLE announcements ALTER COLUMN content_id SET DEFAULT 0",
        "ALTER TABLE announcements ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id)",
        """
        UPDATE announcements a
        SET user_id = es.user_id
        FROM exercise_submissions es
        WHERE a.content_type = 'exercise_submission'
          AND a.content_id = es.id
          AND a.user_id IS NULL
        """,
        """
        UPDATE announcements a
        SET user_id = cl.user_id
        FROM community_labs cl
        WHERE a.content_type = 'community_lab'
          AND a.content_id = cl.id
          AND a.user_id IS NULL
        """,
        """
        UPDATE announcements a
        SET user_id = cv.user_id
        FROM community_videos cv
        WHERE a.content_type = 'community_video'
          AND a.content_id = cv.id
          AND a.user_id IS NULL
        """,
        """
        UPDATE announcements a
        SET user_id = p.user_id
        FROM papers p
        WHERE a.content_type = 'paper_submission'
          AND a.content_id = p.id
          AND a.user_id IS NULL
        """,
    ]
    try:
        with engine.begin() as conn:
            for stmt in statements:
                conn.execute(text(stmt))
    except Exception as exc:
        print(f"Announcement default ensure skipped: {exc}")

_ensure_announcement_defaults()