# 🍹 MixBot — AI Cocktail Mixologist

MixBot is an AI-powered cocktail chatbot that uses the Gemini model (via OpenRouter) to craft personalized cocktail recipes and hold conversations about mixology.

## 🚀 Tech Stack

- **Backend**: FastAPI + SQLite + Python
- **Frontend**: Vanilla HTML, CSS, JavaScript
- **AI**: Google Gemini 2.0 Flash via OpenRouter API
- **Auth**: JWT-based authentication with bcrypt password hashing

---

## 📁 Project Structure

```
cocktail/
├── backend/
│   ├── main.py            # FastAPI app & all API routes
│   ├── gemini_client.py   # OpenRouter/Gemini API integration
│   ├── auth_utils.py      # JWT + bcrypt auth helpers
│   ├── history.py         # SQLAlchemy DB models & helpers
│   ├── models.py          # Pydantic request/response models
│   ├── prompts.py         # AI system prompts
│   ├── requirements.txt   # Python dependencies
│   ├── Procfile           # Render.com deployment config
│   └── .env.example       # Environment variable template
└── frontend/
    ├── index.html         # Main chat interface
    ├── admin.html         # Admin panel
    ├── app.js             # Frontend logic
    ├── style.css          # Styles
    └── particles.js       # Background particle animation
```

---

## 🛠️ Local Development

### 1. Clone the repo

```bash
git clone https://github.com/Mani-4114/mix-bot.git
cd mix-bot
```

### 2. Set up the backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate      # Windows
# or: source venv/bin/activate  (Mac/Linux)

pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
# Edit .env and fill in your API keys
```

Required keys:
| Variable | Description |
|---|---|
| `OPENROUTER_API_KEY` | Get from [openrouter.ai](https://openrouter.ai) |
| `SECRET_KEY` | Any long random string for JWT signing |

### 4. Run the backend

```bash
uvicorn main:app --reload
```

Backend runs at: `http://127.0.0.1:8000`

### 5. Open the frontend

Open `frontend/index.html` in your browser (or use Live Server in VS Code).

---

## 🌐 Deployment

### Backend → Render.com

1. Connect your GitHub repo to [Render](https://render.com)
2. Create a new **Web Service**, set root directory to `backend/`
3. Set **Build Command**: `pip install -r requirements.txt`
4. Set **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables: `OPENROUTER_API_KEY`, `SECRET_KEY`

### Frontend → Netlify / Vercel

1. Connect your GitHub repo
2. Set publish directory to `frontend/`
3. Update `API_URL` in `frontend/app.js` with your Render backend URL

---

## ✨ Features

- 💬 Conversational AI cocktail chat
- 🍸 Personalized recipe generation
- 📜 Chat history with session persistence
- 🔐 User authentication (register/login/Google OAuth)
- 👑 Admin panel for user and history management
- 🎨 Dark glassmorphism UI with particle animations
