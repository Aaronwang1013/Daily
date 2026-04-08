from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from ..database import get_db
from ..models import AWSProgress

router = APIRouter(prefix="/api/aws", tags=["AWS"])


class LessonItem(BaseModel):
    name: str
    time: str
    status: str  # done / progress / todo


class AWSUpdate(BaseModel):
    done: Optional[int] = None
    total: Optional[int] = None
    current_lesson: Optional[str] = None
    resume_url: Optional[str] = None
    lessons: Optional[List[LessonItem]] = None


DEFAULT_LESSONS = [
    {"name": "Exam Prep Plan Overview",          "time": "15m",     "status": "done"},
    {"name": "Official Practice Question Set",    "time": "40m",     "status": "done"},
    {"name": "Exam Prep Overview",               "time": "15m",     "status": "done"},
    {"name": "Domain 1 Review",                  "time": "1h 20m",  "status": "done"},
    {"name": "Domain 1 Practice",                "time": "30m",     "status": "progress"},
    {"name": "Domain 1 SimuLearn",               "time": "1h",      "status": "todo"},
    {"name": "Domain 2 Review",                  "time": "1h 20m",  "status": "todo"},
    {"name": "Domain 2 Practice",                "time": "20m",     "status": "todo"},
    {"name": "Domain 2 SimuLearn",               "time": "1h",      "status": "todo"},
    {"name": "Domain 3 Review",                  "time": "1h 20m",  "status": "todo"},
    {"name": "Domain 3 Practice",                "time": "30m",     "status": "todo"},
    {"name": "Domain 3 SimuLearn",               "time": "1h",      "status": "todo"},
    {"name": "Domain 4 Review",                  "time": "1h 20m",  "status": "todo"},
    {"name": "Domain 4 Practice",                "time": "20m",     "status": "todo"},
    {"name": "Domain 4 SimuLearn",               "time": "1h",      "status": "todo"},
    {"name": "Official Pretest",                 "time": "2h 30m",  "status": "todo"},
    {"name": "Official Practice Exam",           "time": "2h 30m",  "status": "todo"},
    {"name": "Exam Prep Summary",                "time": "5m",      "status": "todo"},
]


def get_or_create(db: Session) -> AWSProgress:
    record = db.query(AWSProgress).first()
    if not record:
        record = AWSProgress(
            done=4, total=18,
            current_lesson="Domain 1 Practice",
            resume_url="https://skillbuilder.aws/learn/V6PVTJAUB5/domain-1-practice-aws-certified-data-engineer--associate-deac01--english/MKW13TA5XE?parentId=YTMBK7R698",
            lessons=DEFAULT_LESSONS,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


@router.get("")
def get_aws(db: Session = Depends(get_db)):
    return get_or_create(db)


@router.patch("")
def update_aws(body: AWSUpdate, db: Session = Depends(get_db)):
    record = get_or_create(db)
    if body.done is not None:
        record.done = body.done
    if body.total is not None:
        record.total = body.total
    if body.current_lesson is not None:
        record.current_lesson = body.current_lesson
    if body.resume_url is not None:
        record.resume_url = body.resume_url
    if body.lessons is not None:
        record.lessons = [l.dict() for l in body.lessons]
    db.commit()
    db.refresh(record)
    return record
