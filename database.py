from sqlalchemy import create_engine, Column, Integer, String, MetaData, ForeignKey, func, distinct
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "mysql+pymysql://ccgnimex:aaaaaaac@188.166.231.207/ccgnimex"
engine = create_engine(DATABASE_URL)
Base = declarative_base()

class Jadwal(Base):
    __tablename__ = 'jadwal'
    id = Column(Integer, primary_key=True, index=True)
    hari = Column(String, index=True)
    anime_id = Column(Integer, ForeignKey("anilist_data.anime_id"))

class AnilistData(Base):
    __tablename__ = 'anilist_data'
    anime_id = Column(Integer, primary_key=True, index=True)
    judul = Column(String)
    image = Column(String)

class Nonton(Base):
    __tablename__ = "nonton"

    id = Column(Integer, primary_key=True, index=True)
    anime_id = Column(Integer)
    episode_number = Column(Integer)
    title = Column(String)  # Add this line for the title field
    video_url = Column(String)
    resolusi = Column(String)

class UsersWeb(Base):
    __tablename__ = 'users_web'

    id = Column(Integer, primary_key=True, index=True)
    fcm_token = Column(String, unique=True, index=True)

Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
