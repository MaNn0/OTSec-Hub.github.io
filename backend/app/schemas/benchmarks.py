from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class BenchmarkBase(BaseModel):
    name: str
    description: str
    contributor_name: Optional[str] = None
    contributor_institution: Optional[str] = None
    tags: Optional[List[str]] = None
    bibtex_citation: Optional[str] = None

# Schema returned when querying data from the API
class BenchmarkResponse(BenchmarkBase):
    id: int
    file_path: str
    created_at: datetime

    class Config:
        from_attributes = True  # Allows Pydantic to read SQLAlchemy models