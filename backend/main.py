from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from models import (ChatRequest, UserRegister, UserLogin, Token,
                    ChatSessionSyncRequest, GoogleLoginRequest)
from gemini_client import chat_with_mixbot
from history import (init_db, get_history, clear_history, 
                     get_user_by_email, create_user, get_all_users, RecipeHistory,
                     save_chat_session, ChatSession, delete_chat_session)
from auth_utils import verify_password, get_password_hash, create_access_token, verify_token
import json
import traceback
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="MixBot API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Auth Dependencies ---
def get_current_user(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    payload = verify_token(token)
    if not payload:
        return None
    return payload

def require_admin(user = Depends(get_current_user)):
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return user

# --- Auth Endpoints ---
@app.post("/api/auth/register", response_model=Token)
async def api_register(req: UserRegister):
    existing = get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = create_user(req.name, req.email, get_password_hash(req.password))
    token = create_access_token({"sub": user.email, "user_id": user.id, "name": user.name, "is_admin": user.is_admin})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "is_admin": user.is_admin, "name": user.name}

@app.post("/api/auth/login", response_model=Token)
async def api_login(req: UserLogin):
    user = get_user_by_email(req.email)
    if not user or not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.email, "user_id": user.id, "name": user.name, "is_admin": user.is_admin})
    return {"access_token": token, "token_type": "bearer", "user_id": user.id, "is_admin": user.is_admin, "name": user.name}

@app.post("/api/auth/google", response_model=Token)
async def api_google_login(req: GoogleLoginRequest):
    import jwt
    try:
        # Decode the Google ID token (skipping signature verification for the demo)
        payload = jwt.decode(req.token, options={"verify_signature": False})
        email = payload.get("email")
        name = payload.get("name")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid Google token payload")
        
        user = get_user_by_email(email)
        if not user:
            # Auto-register google user
            user = create_user(name, email, get_password_hash("google_oauth_" + email))
            
        token = create_access_token({"sub": user.email, "user_id": user.id, "name": user.name, "is_admin": user.is_admin})
        return {"access_token": token, "token_type": "bearer", "user_id": user.id, "is_admin": user.is_admin, "name": user.name}
    except Exception:
        raise HTTPException(status_code=400, detail="Failed to parse Google token")

# --- Core feature Endpoints ---
@app.post("/api/chat")
async def api_chat(req: ChatRequest):
    try:
        response_text = chat_with_mixbot(req.conversation_history, req.message)
        return {"role": "model", "text": response_text}
    except Exception as e:
        print("ERROR IN CHAT:")
        traceback.print_exc()
        error_msg = str(e)
        if "429" in error_msg or "Quota" in error_msg or "ResourceExhausted" in error_msg:
            friendly_msg = "MixBot is currently taking a quick break due to high demand. Please try again in a minute!"
        else:
            friendly_msg = "MixBot encountered an error. Please try again later."
        return JSONResponse(status_code=500, content={"detail": friendly_msg})

@app.get("/api/history")
async def api_get_history(user = Depends(get_current_user)):
    # If not logged in, return anonymous history
    uid = user["user_id"] if user else None
    records = get_history(uid)
    return [{"id": r.id, "recipe": json.loads(r.recipe_json), "created_at": r.created_at} for r in records]

@app.post("/api/history/clear")
async def api_clear_history(user = Depends(get_current_user)):
    uid = user["user_id"] if user else None
    clear_history(uid)
    return {"success": True}

@app.post("/api/chat_sessions")
async def sync_chat_session(req: ChatSessionSyncRequest, user = Depends(get_current_user)):
    uid = user["user_id"] if user else None
    save_chat_session(req.session_id, req.title, req.history_json, uid)
    return {"success": True}

# --- Admin Endpoints ---
@app.get("/api/admin/users")
async def admin_get_users(admin_user = Depends(require_admin)):
    users = get_all_users()
    return [{"id": u.id, "name": u.name, "email": u.email, "is_admin": u.is_admin} for u in users]

@app.get("/api/admin/history")
async def admin_get_all_history(admin_user = Depends(require_admin)):
    from history import SessionLocal, User
    db = SessionLocal()
    records = db.query(RecipeHistory).order_by(RecipeHistory.created_at.desc()).all()
    users = {u.id: u.email for u in db.query(User).all()}
    db.close()
    return [{"id": r.id, "user_email": users.get(r.user_id, "Anonymous"), "recipe": json.loads(r.recipe_json), "created_at": r.created_at} for r in records]

@app.get("/api/admin/chat_sessions")
async def admin_get_all_chat_sessions(admin_user = Depends(require_admin)):
    from history import SessionLocal, User
    db = SessionLocal()
    records = db.query(ChatSession).order_by(ChatSession.updated_at.desc()).all()
    users = {u.id: u.email for u in db.query(User).all()}
    db.close()
    return [{"id": r.id, "session_id": r.session_id, "title": r.title, "user_email": users.get(r.user_id, "Anonymous"), "history_json": json.loads(r.history_json) if r.history_json else [], "updated_at": r.updated_at} for r in records]

@app.delete("/api/admin/chat_sessions/{session_id}")
async def admin_delete_chat_session(session_id: str, admin_user = Depends(require_admin)):
    delete_chat_session(session_id)
    return {"success": True}

@app.delete("/api/admin/history/{history_id}")
async def admin_delete_history(history_id: int, admin_user = Depends(require_admin)):
    from history import SessionLocal
    db = SessionLocal()
    db.query(RecipeHistory).filter(RecipeHistory.id == history_id).delete()
    db.commit()
    db.close()
    return {"success": True}

@app.delete("/api/admin/users/{user_id}")
async def admin_delete_user(user_id: int, admin_user = Depends(require_admin)):
    from history import SessionLocal, User
    db = SessionLocal()
    if user_id == admin_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    db.query(User).filter(User.id == user_id).delete()
    db.commit()
    db.close()
    return {"success": True}

@app.patch("/api/admin/users/{user_id}/role")
async def admin_update_role(user_id: int, admin_user = Depends(require_admin)):
    from history import SessionLocal, User
    db = SessionLocal()
    if user_id == admin_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot change your own role")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_admin = not user.is_admin
    db.commit()
    db.close()
    return {"success": True, "new_role": user.is_admin}
