# Quick Implementation Guide

**For Critical Features Needed in 1 Month**

This guide provides ready-to-implement code for the essential features needed for client delivery.

---

## 1. User Authentication (Week 2, Day 8-10)

### Database Schema

**SQLite:**
```sql
-- Add to existing database or create new users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT,
    role TEXT DEFAULT 'user',  -- 'admin' or 'user'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

CREATE TABLE login_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT,
    user_agent TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### Backend Implementation

**File: `server/auth.py`**
```python
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
import sqlite3

# Configuration
SECRET_KEY = "your-secret-key-here-change-in-production"  # Store in .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Database connection
def get_db():
    conn = sqlite3.connect("data/bird_data_complete.db")
    conn.row_factory = sqlite3.Row
    return conn

# Models
class User(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"

class Token(BaseModel):
    access_token: str
    token_type: str

class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    role: str = "user"

# Helper functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_user(username: str) -> Optional[User]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    db.close()

    if row:
        return User(
            id=row["id"],
            username=row["username"],
            full_name=row["full_name"],
            email=row["email"],
            role=row["role"]
        )
    return None

def authenticate_user(username: str, password: str) -> Optional[User]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    row = cursor.fetchone()
    db.close()

    if not row:
        return None
    if not verify_password(password, row["password_hash"]):
        return None

    return User(
        id=row["id"],
        username=row["username"],
        full_name=row["full_name"],
        email=row["email"],
        role=row["role"]
    )

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = get_user(username)
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def log_login(user_id: int, ip_address: str, user_agent: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO login_history (user_id, ip_address, user_agent) VALUES (?, ?, ?)",
        (user_id, ip_address, user_agent)
    )
    cursor.execute(
        "UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
        (user_id,)
    )
    db.commit()
    db.close()

def create_user(user_create: UserCreate) -> User:
    db = get_db()
    cursor = db.cursor()

    # Check if username exists
    cursor.execute("SELECT id FROM users WHERE username = ?", (user_create.username,))
    if cursor.fetchone():
        db.close()
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create user
    password_hash = get_password_hash(user_create.password)
    cursor.execute(
        "INSERT INTO users (username, password_hash, full_name, email, role) VALUES (?, ?, ?, ?, ?)",
        (user_create.username, password_hash, user_create.full_name, user_create.email, user_create.role)
    )
    db.commit()
    user_id = cursor.lastrowid
    db.close()

    return User(
        id=user_id,
        username=user_create.username,
        full_name=user_create.full_name,
        email=user_create.email,
        role=user_create.role
    )
```

### Add Auth Endpoints to FastAPI

**File: `server/main.py` (add these endpoints)**
```python
from auth import (
    Token, UserCreate, User, OAuth2PasswordRequestForm,
    authenticate_user, create_access_token, get_current_user,
    require_admin, log_login, create_user, ACCESS_TOKEN_EXPIRE_MINUTES
)
from datetime import timedelta
from fastapi import Request

@app.post("/token", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends()
):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Log login
    ip = request.client.host
    user_agent = request.headers.get("user-agent", "")
    log_login(user.id, ip, user_agent)

    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.post("/users", response_model=User)
async def create_new_user(
    user_create: UserCreate,
    current_user: User = Depends(require_admin)
):
    return create_user(user_create)

@app.get("/users", response_model=list[User])
async def list_users(current_user: User = Depends(require_admin)):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, full_name, email, role FROM users")
    rows = cursor.fetchall()
    db.close()

    return [User(
        id=row["id"],
        username=row["username"],
        full_name=row["full_name"],
        email=row["email"],
        role=row["role"]
    ) for row in rows]

# Protect existing endpoints
@app.post("/ask")
async def ask_question(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    # existing code...
    pass

@app.post("/cv/inference")
async def inference(
    file: UploadFile = File(...),
    conf_threshold: float = Form(0.25),
    fast_mode: bool = Form(True),
    current_user: User = Depends(get_current_user)
):
    # existing code...
    pass
```

### Create Initial Admin User

**File: `scripts/create_admin.py`**
```python
import sqlite3
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_admin():
    username = input("Admin username: ")
    password = input("Admin password: ")
    full_name = input("Full name: ")
    email = input("Email: ")

    password_hash = pwd_context.hash(password)

    conn = sqlite3.connect("data/bird_data_complete.db")
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO users (username, password_hash, full_name, email, role)
        VALUES (?, ?, ?, ?, 'admin')
    """, (username, password_hash, full_name, email))

    conn.commit()
    conn.close()

    print(f"Admin user '{username}' created successfully!")

if __name__ == "__main__":
    create_admin()
```

**Run:** `python scripts/create_admin.py`

### Frontend Integration (Streamlit)

**File: `frontend/components/auth.py`**
```python
import streamlit as st
import requests
from services.api_client import API_BASE_URL

def check_auth():
    """Check if user is authenticated, redirect to login if not"""
    if "access_token" not in st.session_state:
        show_login()
        st.stop()

def show_login():
    st.title("🦅 NestScope Login")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")

        if submit:
            try:
                response = requests.post(
                    f"{API_BASE_URL}/token",
                    data={"username": username, "password": password}
                )

                if response.status_code == 200:
                    data = response.json()
                    st.session_state.access_token = data["access_token"]
                    st.session_state.username = username
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password")
            except Exception as e:
                st.error(f"Login failed: {e}")

def logout():
    """Logout user"""
    if "access_token" in st.session_state:
        del st.session_state.access_token
    if "username" in st.session_state:
        del st.session_state.username
    st.rerun()

def get_headers():
    """Get authorization headers for API requests"""
    if "access_token" in st.session_state:
        return {"Authorization": f"Bearer {st.session_state.access_token}"}
    return {}
```

**Update page files:**
```python
# At top of each page (01_nest_chat.py, 02_nest_vision.py)
from components.auth import check_auth, logout, get_headers

# After page config
check_auth()

# Add logout button to sidebar
with st.sidebar:
    if st.button("Logout"):
        logout()
```

---

## 2. Data Export (Week 2, Day 11-12)

### Backend Implementation

**File: `server/main.py` (add these imports and endpoints)**
```python
import pandas as pd
import io
from fastapi.responses import StreamingResponse
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

@app.post("/export/csv")
async def export_csv(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Export query results as CSV"""
    # Execute query
    sql_query = generate_sql(request.question)
    df = pd.read_sql_query(sql_query, conn)

    # Convert to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nestscope_export_{timestamp}.csv"

    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/export/excel")
async def export_excel(
    request: QueryRequest,
    current_user: User = Depends(get_current_user)
):
    """Export query results as Excel with formatting"""
    # Execute query
    sql_query = generate_sql(request.question)
    df = pd.read_sql_query(sql_query, conn)

    # Create Excel file
    excel_buffer = io.BytesIO()

    with pd.ExcelWriter(excel_buffer, engine='xlsxwriter') as writer:
        df.to_excel(writer, sheet_name='Results', index=False)

        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['Results']

        # Add formatting
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D97757',
            'font_color': 'white',
            'border': 1
        })

        # Write headers with formatting
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)

        # Auto-fit columns
        for i, col in enumerate(df.columns):
            max_len = max(
                df[col].astype(str).str.len().max(),
                len(str(col))
            ) + 2
            worksheet.set_column(i, i, max_len)

    excel_buffer.seek(0)

    # Create filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"nestscope_export_{timestamp}.xlsx"

    return StreamingResponse(
        iter([excel_buffer.getvalue()]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/cv/export/detections")
async def export_detections(
    results: list,
    current_user: User = Depends(get_current_user)
):
    """Export detection results as CSV"""
    # Format results
    data = []
    for result in results:
        data.append({
            "image_name": result["filename"],
            "bird_count": result["count"],
            "confidence_avg": sum(d["confidence"] for d in result["detections"]) / len(result["detections"]) if result["detections"] else 0,
            "inference_time_ms": result["inference_time"] * 1000
        })

    df = pd.DataFrame(data)

    # Convert to CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"detection_results_{timestamp}.csv"

    return StreamingResponse(
        iter([csv_buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
```

### Frontend Integration

**File: `frontend/pages/01_nest_chat.py` (add export buttons)**
```python
# After displaying dataframe
if "dataframe" in message and message["dataframe"] is not None:
    df = message["dataframe"]
    st.dataframe(df)

    # Export buttons
    col1, col2 = st.columns(2)

    with col1:
        if st.button("📥 Export CSV", key=f"csv_{idx}"):
            # Convert df to CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name=f"nestscope_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )

    with col2:
        if st.button("📊 Export Excel", key=f"excel_{idx}"):
            # Convert df to Excel
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Results')

            st.download_button(
                label="Download Excel",
                data=buffer.getvalue(),
                file_name=f"nestscope_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
```

---

## 3. Session History (Week 2, Day 13-14)

### Database Schema

```sql
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    title TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER,
    role TEXT,  -- 'user' or 'assistant'
    content TEXT,
    data JSON,  -- Store dataframe, chart info, etc.
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);
```

### Backend Implementation

**File: `server/conversation.py`**
```python
import sqlite3
import json
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

class Message(BaseModel):
    id: Optional[int] = None
    role: str
    content: str
    data: Optional[dict] = None
    created_at: Optional[datetime] = None

class Conversation(BaseModel):
    id: Optional[int] = None
    user_id: int
    title: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: Optional[List[Message]] = []

def get_db():
    conn = sqlite3.connect("data/bird_data_complete.db")
    conn.row_factory = sqlite3.Row
    return conn

def create_conversation(user_id: int, title: str) -> Conversation:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO conversations (user_id, title) VALUES (?, ?)",
        (user_id, title)
    )
    db.commit()
    conversation_id = cursor.lastrowid
    db.close()

    return Conversation(id=conversation_id, user_id=user_id, title=title)

def add_message(conversation_id: int, role: str, content: str, data: Optional[dict] = None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "INSERT INTO messages (conversation_id, role, content, data) VALUES (?, ?, ?, ?)",
        (conversation_id, role, content, json.dumps(data) if data else None)
    )
    cursor.execute(
        "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (conversation_id,)
    )
    db.commit()
    db.close()

def get_conversations(user_id: int) -> List[Conversation]:
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC",
        (user_id,)
    )
    rows = cursor.fetchall()
    db.close()

    return [Conversation(
        id=row["id"],
        user_id=row["user_id"],
        title=row["title"],
        created_at=row["created_at"],
        updated_at=row["updated_at"]
    ) for row in rows]

def get_conversation(conversation_id: int) -> Optional[Conversation]:
    db = get_db()
    cursor = db.cursor()

    # Get conversation
    cursor.execute("SELECT * FROM conversations WHERE id = ?", (conversation_id,))
    conv_row = cursor.fetchone()

    if not conv_row:
        db.close()
        return None

    # Get messages
    cursor.execute(
        "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at",
        (conversation_id,)
    )
    message_rows = cursor.fetchall()
    db.close()

    messages = [Message(
        id=row["id"],
        role=row["role"],
        content=row["content"],
        data=json.loads(row["data"]) if row["data"] else None,
        created_at=row["created_at"]
    ) for row in message_rows]

    return Conversation(
        id=conv_row["id"],
        user_id=conv_row["user_id"],
        title=conv_row["title"],
        created_at=conv_row["created_at"],
        updated_at=conv_row["updated_at"],
        messages=messages
    )

def delete_conversation(conversation_id: int):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
    cursor.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
    db.commit()
    db.close()

def rename_conversation(conversation_id: int, new_title: str):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "UPDATE conversations SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (new_title, conversation_id)
    )
    db.commit()
    db.close()
```

### Frontend Integration

**File: `frontend/pages/01_nest_chat.py` (add to sidebar)**
```python
with st.sidebar:
    # ... existing code ...

    st.markdown("---")
    st.markdown("#### Conversations")

    # New conversation button
    if st.button("➕ New Chat", use_container_width=True):
        st.session_state.current_conversation_id = None
        st.session_state.messages = []
        st.rerun()

    # List conversations
    if "username" in st.session_state:
        try:
            response = requests.get(
                f"{API_BASE_URL}/conversations",
                headers=get_headers()
            )
            if response.status_code == 200:
                conversations = response.json()

                for conv in conversations[:10]:  # Show last 10
                    col1, col2 = st.columns([4, 1])

                    with col1:
                        if st.button(
                            conv["title"][:30] + "..." if len(conv["title"]) > 30 else conv["title"],
                            key=f"conv_{conv['id']}",
                            use_container_width=True
                        ):
                            # Load conversation
                            st.session_state.current_conversation_id = conv["id"]
                            # Load messages...
                            st.rerun()

                    with col2:
                        if st.button("🗑️", key=f"delete_{conv['id']}"):
                            # Delete conversation
                            requests.delete(
                                f"{API_BASE_URL}/conversations/{conv['id']}",
                                headers=get_headers()
                            )
                            st.rerun()
        except:
            pass
```

---

## 4. Docker Deployment (Week 3, Day 15-16)

### Dockerfile for Backend

**File: `server/Dockerfile`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create data directory
RUN mkdir -p /data /app/models

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Dockerfile for Frontend

**File: `frontend/Dockerfile`**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### Docker Compose

**File: `docker-compose.yml`**
```yaml
version: '3.8'

services:
  backend:
    build: ./server
    ports:
      - "8000:8000"
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - DB_PATH=/data/bird_data_complete.db
    volumes:
      - ./data:/data
      - ./models:/app/models
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "8501:8501"
    environment:
      - API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    restart: unless-stopped

  labeller:
    build: ./labeller
    ports:
      - "5000:5000"
    volumes:
      - ./labeller/nestvision:/app/nestvision
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - frontend
      - backend
      - labeller
    restart: unless-stopped
```

### Nginx Configuration

**File: `nginx.conf`**
```nginx
events {
    worker_connections 1024;
}

http {
    upstream frontend {
        server frontend:8501;
    }

    upstream backend {
        server backend:8000;
    }

    upstream labeller {
        server labeller:5000;
    }

    server {
        listen 80;
        server_name _;

        # Frontend
        location / {
            proxy_pass http://frontend;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Backend API
        location /api {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        # Labeller
        location /labeller {
            proxy_pass http://labeller;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }
    }
}
```

### Environment Variables

**File: `.env.example`**
```bash
# OpenRouter API Key (required)
OPENROUTER_API_KEY=your_key_here

# Database
DB_PATH=data/bird_data_complete.db
DB_TYPE=sqlite

# API Configuration
API_BASE_URL=http://localhost:8000

# Authentication
SECRET_KEY=change_this_in_production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Optional: Email notifications
# SMTP_SERVER=smtp.gmail.com
# SMTP_PORT=587
# SMTP_USERNAME=your_email@gmail.com
# SMTP_PASSWORD=your_password
```

---

## 5. Quick Deployment Scripts

### Startup Script

**File: `start.sh`**
```bash
#!/bin/bash

echo "🚀 Starting NestScope..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found!"
    echo "📝 Copy .env.example to .env and configure it"
    exit 1
fi

# Build and start
docker-compose build
docker-compose up -d

echo "✅ NestScope started!"
echo "📊 Frontend: http://localhost:8501"
echo "🔧 Backend API: http://localhost:8000"
echo "🏷️ Labeller: http://localhost:5000"
echo ""
echo "📋 View logs: docker-compose logs -f"
echo "🛑 Stop: ./stop.sh"
```

### Stop Script

**File: `stop.sh`**
```bash
#!/bin/bash

echo "🛑 Stopping NestScope..."
docker-compose down
echo "✅ NestScope stopped!"
```

### Make scripts executable
```bash
chmod +x start.sh stop.sh
```

---

## Testing Checklist

### After Implementation

- [ ] Test authentication (login, logout, protected routes)
- [ ] Test data export (CSV, Excel)
- [ ] Test session history (create, load, delete)
- [ ] Test Docker build (all services start)
- [ ] Test from fresh clone (simulate deployment)
- [ ] Test with non-technical user
- [ ] Document any issues found

---

## Next Steps

1. **Week 1:** Focus on stability and bug fixes
2. **Week 2:** Implement these features in order (auth → export → history)
3. **Week 3:** Deploy using Docker
4. **Week 4:** Document and train client

**Remember:** Test after each feature! Don't accumulate bugs.
