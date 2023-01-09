from sqlalchemy import String, Column
from models.base_models import Base


class FrontendUser(Base):
    __tablename__ = "frontenduser"
    name = Column(String, primary_key=True, index=True)
    hashed_password = Column(String)
    role = Column(String)
    email = Column(String)
    mobile_number = Column(String)
