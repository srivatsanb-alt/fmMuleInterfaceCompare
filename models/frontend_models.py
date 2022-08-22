from sqlalchemy import String, Column
from typing import Union
from models.base_models import Base, TimestampMixin

class FrontendUser(Base):
    __tablename__ = "frontenduser"
    name = Column(String, primary_key=True, index=True)
    hashed_password = Column(String)
