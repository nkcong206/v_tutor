# V-Tutor

Platform for teachers to create AI-generated exams and students to take them.

## Structure

```
v_tutor/
├── client/     # React frontend
└── server/     # FastAPI backend
```

## Quick Start

### 1. Start Server
```bash
cd server
pip install -r requirements.txt
# Add your OPENAI_API_KEY to .env
uvicorn app.main:app --reload --port 8000
```

### 2. Start Client
```bash
cd client
npm install
npm run dev
```

Open http://localhost:3000
