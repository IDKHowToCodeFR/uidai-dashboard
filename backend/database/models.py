from sqlalchemy import Column, Integer, String, ForeignKey, JSON, DateTime, Float, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from backend.database.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    companies = Column(JSON, default=[])
    login_count = Column(Integer, default=0)
    last_login = Column(String, nullable=True)

    permissions = relationship("UserPermission", back_populates="user", cascade="all, delete-orphan")


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    permission_name = Column(String, nullable=False)

    user = relationship("User", back_populates="permissions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String, default=lambda: datetime.now().isoformat())
    action = Column(String, nullable=False)
    username = Column(String, nullable=False)
    details = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    endpoint = Column(String, nullable=True)


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(JSON, nullable=False)


class FileMetadata(Base):
    __tablename__ = "file_metadata"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, index=True, nullable=False)
    upload_directory = Column(String, index=True, nullable=False, default="unknown")
    data_type = Column(String, default="CCF Data")
    uploaded_at = Column(String, default=lambda: datetime.now().isoformat())
    uploader = Column(String, nullable=True)
    size_bytes = Column(Integer, default=0)
    
    __table_args__ = (UniqueConstraint('filename', 'upload_directory', name='uq_file_metadata'),)
    
    metrics = relationship("CCFData", back_populates="file", cascade="all, delete-orphan")
    unimate_metrics = relationship("UniMateData", back_populates="file", cascade="all, delete-orphan")
    cdr_metrics = relationship("CDRData", back_populates="file", cascade="all, delete-orphan")
    apr_metrics = relationship("APRData", back_populates="file", cascade="all, delete-orphan")


class CCFData(Base):
    __tablename__ = "ccf_data"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_metadata.id"), nullable=False)
    
    __table_args__ = (UniqueConstraint('company', 'language', 'call_timestamp', name='uq_ccf_data'),)
    
    company = Column(String, index=True)
    language = Column(String, index=True)
    date_logged = Column(String, index=True)
    call_timestamp = Column(String, index=True)
    day = Column(String)
    
    call_offered = Column(Float)
    aban_calls_10_sec = Column(Float)
    acd_calls_10_sec = Column(Float)
    acd_calls_20_sec = Column(Float)
    aban_calls = Column(Float)
    held_calls = Column(Float)
    
    service_level_pct = Column(Float)
    service_level_status = Column(String)
    
    acd_calls = Column(Float)
    hold_time = Column(Float)
    avg_hold_time = Column(Float)
    hold_time_status = Column(String)
    
    acd_time = Column(Float)
    acw_time = Column(Float)
    avg_handle_time = Column(Float)
    aht_status = Column(String)
    
    file = relationship("FileMetadata", back_populates="metrics")


class UniMateData(Base):
    __tablename__ = "unimate_data"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_metadata.id"), nullable=False)
    
    __table_args__ = (UniqueConstraint('ucid', name='uq_unimate_data'),)
    
    ucid = Column(String, index=True)
    session_id = Column(String, index=True)
    company = Column(String, index=True) # Derived from DNIS
    day_of_week = Column(String)
    call_start_time = Column(String, index=True)
    call_end_time = Column(String)
    call_duration = Column(Integer)
    ani = Column(String)
    dnis = Column(String)
    language = Column(String, index=True)
    authentication = Column(String)
    auth_mechanism = Column(String)
    termination_type = Column(String)
    termination_reason = Column(String)
    description = Column(String)
    region = Column(String)
    
    is_fcr = Column(Integer, default=1) # 1 for True, 0 for False (using Int for SQLite compatibility if needed, though Boolean is fine in sqlalchemy)
    
    file = relationship("FileMetadata", back_populates="unimate_metrics")


class CDRData(Base):
    __tablename__ = "cdr_data"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_metadata.id"), nullable=False)
    
    __table_args__ = (UniqueConstraint('call_id', name='uq_cdr_data'),)
    
    call_id = Column(String, index=True)
    acwtime = Column(Integer)
    ansholdtime = Column(Integer)
    duration = Column(Integer)
    segstart = Column(String, index=True)
    segstartutc = Column(String)
    segstop = Column(String)
    segstoputc = Column(String)
    talktime = Column(Integer)
    split1 = Column(String)
    transferred = Column(Integer)
    agt_released = Column(Integer)
    origlogin = Column(String)
    anslogin = Column(String)
    
    company = Column(String, index=True)
    language = Column(String, index=True)
    
    file = relationship("FileMetadata", back_populates="cdr_metrics")


class APRData(Base):
    __tablename__ = "apr_data"
    __table_args__ = (UniqueConstraint('date_logged', 'login_id', name='uq_apr_date_login'),)

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("file_metadata.id"), nullable=False)
    
    date_logged = Column(String, index=True)
    agent_name = Column(String)
    login_id = Column(String, index=True)
    acd_calls = Column(Integer)
    avg_acd_time = Column(Integer)
    avg_acw_time = Column(Integer)
    occupancy_with_acw = Column(Float)
    occupancy_without_acw = Column(Float)
    acd_time = Column(String)
    acw_time = Column(String)
    agent_ring_time = Column(String)
    other_time = Column(String)
    aux_time = Column(String)
    avail_time = Column(String)
    staffed_time = Column(String)
    held_calls = Column(String)
    tea_break = Column(String)
    lunch_dinner = Column(String)
    quality_feedback = Column(String)
    email_support = Column(String)
    briefing = Column(String)
    system_down = Column(String)
    meeting = Column(String)
    trans_out = Column(Integer)
    split_skill = Column(String)
    conf = Column(Integer)
    
    company = Column(String, index=True)
    language = Column(String, index=True)
    
    file = relationship("FileMetadata", back_populates="apr_metrics")


class AgentMetadata(Base):
    __tablename__ = "agent_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    anslogin = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    tenure_months = Column(Integer)
    team = Column(String)
    location = Column(String)


