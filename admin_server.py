"""
Простой admin API для редактирования PostgreSQL-базы бота.

Запуск локально:
    uvicorn admin_server:app --host 0.0.0.0 --port 8000

Авторизация:
    ENV:
        ADMIN_LOGIN
        ADMIN_PASSWORD
    /api/login -> возвращает token, который нужно передавать в заголовке
    Authorization: Bearer <token>
"""

import os
import uuid
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_PRIVATE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL / DATABASE_PRIVATE_URL не заданы")

if "sslmode=" not in DATABASE_URL and ("rlwy.net" in DATABASE_URL or "railway" in DATABASE_URL.lower()):
    DATABASE_URL = DATABASE_URL + ("&" if "?" in DATABASE_URL else "?") + "sslmode=require"

ADMIN_LOGIN = os.environ.get("ADMIN_LOGIN", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD не задан в окружении")

ALLOWED_TABLES = ("exercises", "user_history", "user_completed")

ACTIVE_TOKENS: set[str] = set()


def get_db_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


class LoginRequest(BaseModel):
    login: str
    password: str


class LoginResponse(BaseModel):
    token: str


class UpdateRowRequest(BaseModel):
    values: Dict[str, Any]


app = FastAPI(title="Fitness Bot Admin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_token(authorization: str = Header("")):
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        raise HTTPException(status_code=401, detail="Missing Bearer token")
    token = authorization[len(prefix) :].strip()
    if token not in ACTIVE_TOKENS:
        raise HTTPException(status_code=401, detail="Invalid token")
    return token


@app.post("/api/login", response_model=LoginResponse)
def login(data: LoginRequest):
    if data.login != ADMIN_LOGIN or data.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = uuid.uuid4().hex
    ACTIVE_TOKENS.add(token)
    return LoginResponse(token=token)


@app.get("/api/tables", response_model=List[str])
def list_tables(token: str = Depends(require_token)):
    return list(ALLOWED_TABLES)


@app.get("/api/table/{table_name}")
def get_table_rows(
    table_name: str,
    limit: int = 100,
    offset: int = 0,
    token: str = Depends(require_token),
):
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Table not allowed")

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"SELECT * FROM {table_name} ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
        rows = cur.fetchall()
        return {"rows": rows}
    finally:
        conn.close()


@app.put("/api/table/{table_name}/{row_id}")
def update_row(
    table_name: str,
    row_id: int,
    body: UpdateRowRequest,
    token: str = Depends(require_token),
):
    if table_name not in ALLOWED_TABLES:
        raise HTTPException(status_code=400, detail="Table not allowed")

    values = body.values or {}
    if not values:
        raise HTTPException(status_code=400, detail="No fields to update")

    # Не даём менять id
    values.pop("id", None)

    columns = list(values.keys())
    set_clause = ", ".join(f"{col} = %s" for col in columns)
    params = [values[col] for col in columns]
    params.append(row_id)

    conn = get_db_connection()
    cur = conn.cursor()
    try:
        cur.execute(f"UPDATE {table_name} SET {set_clause} WHERE id = %s", params)
        if cur.rowcount == 0:
            conn.rollback()
            raise HTTPException(status_code=404, detail="Row not found")
        conn.commit()
        return {"status": "ok"}
    finally:
        conn.close()

