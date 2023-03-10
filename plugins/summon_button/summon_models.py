import os
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine
from sqlalchemy import Integer, String, Column, ARRAY
from models.base_models import Base, TimestampMixin
from typing import List,Union
from pydantic import BaseModel
# from ...models.misc_models import Notifications
class DBSession:
    def __init__(self):
        engine = create_engine(
            os.path.join(os.getenv("FM_DATABASE_URI"), "plugin_summon_button")
        )
        session_maker = sessionmaker(autocommit=False, autoflush=True, bind=engine)
        self.session: Session = session_maker()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if exc_type or exc_value or traceback:
            self.close(commit=False)
        else:
            self.close()

    # def add_notification(
    #     self, entity_names, log, log_level, module, repetitive=False, repetition_freq=None
    # ):
    #     new_notification = Notifications(
    #         entity_names=entity_names,
    #         log=log,
    #         log_level=log_level,
    #         module=module,
    #         cleared_by=[],
    #         repetitive=repetitive,
    #         repetition_freq=repetition_freq,
    #     )
    #     self.add_to_session(new_notification)

    def close(self, commit=True):
        if commit:
            self.session.commit()
        self.session.close()


class SummonInfo(Base):
    __tablename__ = "summon_info"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    hashed_api_key = Column(String, unique=True)
    press = Column(String)
    route = Column(ARRAY(String))
    station = Column(String)
    booking_id = Column(Integer)
    trip_id = Column(Integer)

class ClientReq(BaseModel):
    source: Union[str, None] = None

class AddEditSummonReq(ClientReq):
    id: int
    api_key: str
    route: List[str]

class SummonActions(Base, TimestampMixin):
    __tablename__ = "summon_actions"
    __table_args__ = {"extend_existing": True}
    id = Column(Integer, primary_key=True, index=True)
    summon_id = Column(Integer)
    action = Column(String)
