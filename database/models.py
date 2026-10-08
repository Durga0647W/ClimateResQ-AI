from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    report_id = Column(String(20), unique=True, nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(255))
    timestamp = Column(DateTime, default=datetime.utcnow)
    source_type = Column(String(50), default="Citizen")
    people_affected = Column(Integer, nullable=True)
    image_path = Column(String(255), nullable=True)
    quality_status = Column(String(30), default="PENDING")
    quality_notes = Column(Text, nullable=True)
    status = Column(String(30), default="NEW")
    reporter_id = Column(String(100), nullable=True)
    cluster_id = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Incident(Base):
    __tablename__ = "incidents"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String(20), unique=True, nullable=False)
    report_id = Column(String(20))
    incident_type = Column(String(100))
    location = Column(String(255))
    event_time = Column(String(100))
    people_affected = Column(Integer, nullable=True)
    impact = Column(Text)
    description = Column(Text)
    severity_indicators = Column(Text)
    entities = Column(Text)
    missing_info = Column(Text)
    contradictions = Column(Text)
    completeness_score = Column(Float, default=0.0)
    completeness_status = Column(String(30))
    evidence_score = Column(Float, default=0.0)
    evidence_summary = Column(Text)
    confidence = Column(Float, default=0.0)
    confidence_breakdown = Column(Text)
    severity = Column(String(10))
    priority = Column(String(10))
    priority_reasons = Column(Text)
    verification_status = Column(String(30), default="PENDING")
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)
    cluster_id = Column(String(20), nullable=True)
    safety_recommendations = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

class IncidentCluster(Base):
    __tablename__ = "incident_clusters"
    id = Column(Integer, primary_key=True)
    cluster_id = Column(String(20), unique=True)
    canonical_location = Column(String(255))
    display_location = Column(String(255))
    disaster_type = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)
    latest_report_at = Column(DateTime, default=datetime.utcnow)
    report_count = Column(Integer, default=0)
    status = Column(String(30), default="PENDING")
    priority = Column(String(10))
    severity = Column(String(10))
    confidence = Column(Float, default=0.0)
    related_report_ids = Column(Text)
    clustering_reasons = Column(Text)
    verified_by = Column(String(100), nullable=True)
    verified_at = Column(DateTime, nullable=True)

class EvidenceSource(Base):
    __tablename__ = "evidence_sources"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String(20))
    source_name = Column(String(100))
    source_type = Column(String(50))
    content = Column(Text)
    agreement = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

class VerificationRecord(Base):
    __tablename__ = "verification_records"
    id = Column(Integer, primary_key=True)
    incident_id = Column(String(20))
    action = Column(String(30))
    notes = Column(Text)
    performed_by = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True)
    entity_type = Column(String(30))
    entity_id = Column(String(20))
    action = Column(String(50))
    detail = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
