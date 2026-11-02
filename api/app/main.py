import os 
import time
from contextlib import asynccontextmanager
import psycopg
from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

#configuration du compose, secret etc...
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", 5432),
    "dbname": os.getenv("DB_NAME", "todos"),
    "user": os.getenv("DB_USER", "todos"),
    "password": os.getenv("DB_PASSWORD", "t"),
}

def get_conn():
    """
    Ouvrir une connexion et renvoie des lignes en dict
    """
    return psycopg.connect(**DB_CONFIG, row_factory=psycopg.rows.dict_row)

def init_db(retries=5):
    """
    Créer la table en reesayant
    """
    for attempr in range(1, retries +1):
        try:
            with get_conn() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS todos(
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT false,
                    created_at TIMESTAMP NOT NULL DEFAULT now()
                    )
                    """
                )
                return 
        except psycopg.OperationalError as exc:
            print(f"Base pas disponible (tentative {attempr}/{retries}): {exc}", flush = True)
            time.sleep(3)
    raise RuntimeError(f"Impossible de se connecter à la base de données")

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield 

app = FastAPI(Title="API to do list", lifespan=lifespan)

class ToDo(BaseModel):
    title: str

@app.get("/api/health")
def health():
        """
        Verification de la santé de l'API
        """
        return {"status": "ok"}

@app.get("api/ready")
def ready(response: Response):
        """"
        Verification de si la base répond
        """
        try:
            with get_conn() as conn:
                conn.execute("SELECT 1")
                return {"status": "prêt"}
        except psycopg.OperationalError:
            response.status_code = 503
            return {"status": "bdd non disponible"}

@app.get("/api/todos")
def list_todos():
        """
        récupérer la liste des todos
        """
        with get_conn() as conn:
            return  conn.execute("SELECT * FROM todos ORDER BY id").fetchall()

@app.post("/api/todos", status_code=201)
def create_todo(todo: ToDo):
        """
        Créer un todo
        """
        if not todo.title.strip():
            raise HTTPException(status_code=400, detail="il faut un titre")
        with get_conn() as conn:
            return conn.execute(
                "INSERT INTO todos (title) VALUES (%s) RETURNING *",
                (todo.title.strip(),),
            ).fetchdone()
        
@app.put("/api/todos/{todo_id}")
def update_todo(todo_id: int):
        with get_conn() as conn:
            result = conn.execute(
                "UPDATE todos SET title = %s WHERE id = %s RETURNING *",
                (todo_id),
            ).fetchone()
            if result is None:
                raise HTTPException(status_code=404, detail="todo non trouvé")
            return result

@app.delete("/api/todos/{todo_id}", status_code=204)
def delete_todo(todo_id: int):
        with get_conn() as conn:
            conn.execute(
                "DELETE FROM todos WHERE id = %s RETURNING *",
                (todo_id,),
            )
        return Response(status_code=204)
