from pydantic import BaseModel, Field
from typing import List, Optional

class IngredientInput(BaseModel):
    ingredients: List[str]
    mood: Optional[str] = "Relaxing"
    style: Optional[str] = "Classic"
    flavor_sweetness: Optional[int] = 50
    flavor_lightness: Optional[int] = 50
    flavor_fruitiness: Optional[int] = 50

class MixBotMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    conversation_history: List[MixBotMessage]

class IngredientScanRequest(BaseModel):
    description: str

class PartyPlannerRequest(BaseModel):
    guest_count: int
    vibe: str
    budget: str

class NameQuery(BaseModel):
    name: str

class RecipeResponse(BaseModel):
    name: str
    ingredients: List[str]
    measurements: List[str]
    instructions: List[str]
    glassware: str
    garnish: str
    difficulty: str
    flavor_profile: str
    fun_fact: str

class SubstitutionRequest(BaseModel):
    missing_ingredient: str
    cocktail_name: Optional[str] = None

class UserRegister(BaseModel):
    name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    is_admin: bool
    name: str

class ChatSessionSyncRequest(BaseModel):
    session_id: str
    title: str
    history_json: str

class GoogleLoginRequest(BaseModel):
    token: str
