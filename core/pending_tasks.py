"""
Pending Video Tasks - Track async video generation
"""

from sqlalchemy import Column, String, Text, DateTime, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class PendingVideoTask(Base):
    """Track video generation tasks that are in progress"""
    __tablename__ = 'pending_video_tasks'
    
    task_id = Column(String(64), primary_key=True)  # Kie.ai task ID
    workflow_name = Column(String(50), nullable=False)  # e.g., 'animal_facts'
    animal_name = Column(String(100), nullable=False)
    fact_text = Column(Text, nullable=False)
    sora_prompt = Column(Text, nullable=False)
    caption = Column(Text, nullable=False)
    duration = Column(Integer, default=10)
    status = Column(String(20), default='pending')  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    video_url = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
