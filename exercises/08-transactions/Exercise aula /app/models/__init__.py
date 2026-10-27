"""Modelos SQLAlchemy das duas bases: um ficheiro por base (pg1.py e pg2.py)."""

from app.models.pg1 import Participant, Pg1Base, TasksReq
from app.models.pg2 import InsightReport, Pg2Base, ReportContent

__all__ = [
    "InsightReport",
    "Participant",
    "Pg1Base",
    "Pg2Base",
    "ReportContent",
    "TasksReq",
]
