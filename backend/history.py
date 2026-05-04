from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from auth_utils import get_password_hash

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False)

class RecipeHistory(Base):
    __tablename__ = 'recipe_history'
    id = Column(Integer, primary_key=True)
    recipe_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True) # Link history to user

class ChatSession(Base):
    __tablename__ = 'chat_sessions'
    id = Column(Integer, primary_key=True)
    session_id = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    history_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

from sqlalchemy.pool import NullPool
import os
db_path = os.path.join(os.path.expanduser('~'), 'mixbot_history.db')
engine = create_engine(f'sqlite:///{db_path}', connect_args={"check_same_thread": False}, poolclass=NullPool)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    
    # Create default admin if missing
    db = SessionLocal()
    admin = db.query(User).filter_by(email='admin@mixbot.com').first()
    if not admin:
        new_admin = User(
            name="Admin",
            email="admin@mixbot.com",
            hashed_password=get_password_hash("admin"),
            is_admin=True
        )
        db.add(new_admin)
        db.commit()
    db.close()

def add_recipe(recipe_data: str, user_id: int = None):
    db = SessionLocal()
    new_recipe = RecipeHistory(recipe_json=recipe_data, user_id=user_id)
    db.add(new_recipe)
    db.commit()
    db.refresh(new_recipe)
    db.close()
    return new_recipe

def get_history(user_id: int = None):
    db = SessionLocal()
    if user_id:
        records = db.query(RecipeHistory).filter_by(user_id=user_id).order_by(RecipeHistory.created_at.desc()).all()
    else:
        records = [] # Empty if not logged in
    db.close()
    return records

def clear_history(user_id: int = None):
    db = SessionLocal()
    if user_id:
        db.query(RecipeHistory).filter_by(user_id=user_id).delete()
    else:
        # Warning: Only admin should call without user_id to clear all
        db.query(RecipeHistory).delete()
    db.commit()
    db.close()

def save_chat_session(session_id: str, title: str, history_json: str, user_id: int = None):
    db = SessionLocal()
    session = db.query(ChatSession).filter_by(session_id=session_id).first()
    if session:
        session.history_json = history_json
        session.updated_at = datetime.utcnow()
    else:
        session = ChatSession(session_id=session_id, title=title, history_json=history_json, user_id=user_id)
        db.add(session)
    db.commit()
    db.close()

def get_chat_sessions(user_id: int = None):
    db = SessionLocal()
    if user_id:
        records = db.query(ChatSession).filter_by(user_id=user_id).order_by(ChatSession.updated_at.desc()).all()
    else:
        records = []
    db.close()
    return records
    
def get_all_chat_sessions():
    db = SessionLocal()
    records = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    db.close()
    return records
    
def delete_chat_session(session_id: str):
    db = SessionLocal()
    db.query(ChatSession).filter_by(session_id=session_id).delete()
    db.commit()
    db.close()

# User functions
def get_user_by_email(email: str):
    db = SessionLocal()
    user = db.query(User).filter_by(email=email).first()
    db.close()
    return user

def create_user(name: str, email: str, password_hash: str):
    db = SessionLocal()
    new_user = User(name=name, email=email, hashed_password=password_hash)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.close()
    return new_user

def get_all_users():
    db = SessionLocal()
    users = db.query(User).all()
    db.close()
    return users
