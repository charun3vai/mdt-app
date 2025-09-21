from __future__ import annotations
from datetime import date, datetime
from typing import Optional, List, Literal
from sqlmodel import SQLModel, Field, Relationship

# --- Auth / Users ---
class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: Literal["user","admin"] = "admin"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    active: bool = True

# --- Core Entities ---
class Patient(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    hospital_number: str = Field(index=True, unique=True)
    dob: date
    phone_primary: str
    address: str
    pin_code: Optional[str] = None
    digi_pin: Optional[str] = Field(default=None, index=True, unique=False)
    additional_phones_json: Optional[str] = None  # JSON list

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    cases: List["MDTCase"] = Relationship(back_populates="patient")

class MDTCase(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    patient_id: int = Field(foreign_key="patient.id")
    clinical_history: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    discussion_for: Optional[str] = None
    scheduled_reason: Optional[str] = None
    scheduled_date: Optional[date] = None
    status: Literal["Pending","Done"] = "Pending"

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    patient: Patient = Relationship(back_populates="cases")
    pathology_reports: List["PathologyReport"] = Relationship(back_populates="mdt_case")
    imaging_reports: List["ImagingReport"] = Relationship(back_populates="mdt_case")
    treatments: List["TreatmentHistory"] = Relationship(back_populates="mdt_case")
    consensus: Optional["Consensus"] = Relationship(back_populates="mdt_case")

class ReportBase(SQLModel):
    date_of_report: date
    report_type: str
    investigation_details: Optional[str] = None

class PathologyReport(ReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mdt_case_id: int = Field(foreign_key="mdtcase.id")
    mdt_case: MDTCase = Relationship(back_populates="pathology_reports")

class ImagingReport(ReportBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mdt_case_id: int = Field(foreign_key="mdtcase.id")
    mdt_case: MDTCase = Relationship(back_populates="imaging_reports")

class TreatmentHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mdt_case_id: int = Field(foreign_key="mdtcase.id")
    treatment_type: str
    # Chemo
    chemo_date_from: Optional[date] = None
    chemo_date_to: Optional[date] = None
    chemo_protocol: Optional[str] = None
    chemo_notes: Optional[str] = None
    # Radiotherapy
    rtx_date_from: Optional[date] = None
    rtx_date_to: Optional[date] = None
    radiation_dose: Optional[str] = None
    fractions: Optional[str] = None
    rtx_notes: Optional[str] = None
    # Chemo-Radiotherapy
    crt_chemo_drug: Optional[str] = None
    crt_dose: Optional[str] = None
    crt_schedule: Optional[str] = None
    crt_notes: Optional[str] = None
    # Surgery
    surgery_date: Optional[date] = None
    surgery_done: Optional[str] = None
    operative_notes: Optional[str] = None
    other_notes: Optional[str] = None

    mdt_case: MDTCase = Relationship(back_populates="treatments")

class Consensus(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mdt_case_id: int = Field(foreign_key="mdtcase.id", unique=True)
    consensus_text: Optional[str] = None
    followups_json: Optional[str] = None  # JSON list of strings
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    mdt_case: MDTCase = Relationship(back_populates="consensus")

# --- Admin Config ---
class ReportType(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    kind: str  # "pathology" or "imaging"
    name: str

class TreatmentConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    allowed_type: str  # e.g., "Chemo", "Radiotherapy", etc.

class ChemoSchedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # e.g., Daily, Weekly, 2-weekly, 3-weekly
