from sqlalchemy import Column, Integer, String, Text, DateTime, ARRAY
from sqlalchemy.sql import func
from app.database import Base  

class Benchmark(Base):
    __tablename__ = "benchmarks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=False)
    contributor_name = Column(String(255), nullable=True)
    contributor_institution = Column(String(255), nullable=True)
    tags = Column(ARRAY(String), nullable=True)  
    file_path = Column(String(512), nullable=False)  
    bibtex_citation = Column(Text, nullable=True) 
    created_at = Column(DateTime(timezone=True), server_default=func.now())