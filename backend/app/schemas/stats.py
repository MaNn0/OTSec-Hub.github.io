# schemas/stats.py

from pydantic import BaseModel


class ProgressPieChartOut(BaseModel):
    user_id: int
    name: str
    completed_videos: int
    remaining_videos: int
    completed_quizzes: int
    remaining_quizzes: int
    completed_labs: int
    remaining_labs: int
    completed_exercises: int = 0
    remaining_exercises: int = 0
    overall_percent: int = 0
    certificate_ready: bool = False

    class Config:
        from_attributes = True
