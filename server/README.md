# V-Tutor Server

FastAPI backend for the V-Tutor exam management platform.

## Quick Start

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from example)
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The server will start at http://localhost:8000

API docs: http://localhost:8000/docs

## Environment Variables

Required in `.env`:
- `OPENAI_API_KEY` - Your OpenAI API key
- `SECRET_KEY` - JWT secret key
