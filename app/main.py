import os
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .db import Base, engine, get_db
from .models import Processo
from .sync import sincronizar_todos

API_ADMIN_TOKEN = os.getenv("API_ADMIN_TOKEN", "troque-isto")

app = FastAPI(title="Monitor de Processos (DataJud)")

Base.metadata.create_all(bind=engine)

class ProcessoIn(BaseModel):
    numero_cnj: str
    tribunal_alias: str
    email_destino: str

@app.post("/v1/processos")
def criar_processo(payload: ProcessoIn, db: Session = Depends(get_db)):
    p = Processo(
        numero_cnj=payload.numero_cnj.strip(),
        tribunal_alias=payload.tribunal_alias.strip(),
        email_destino=payload.email_destino.strip()
    )
    db.add(p)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(400, "Processo já cadastrado ou erro de validação.")
    db.refresh(p)
    return {"id": p.id, "numero_cnj": p.numero_cnj, "tribunal_alias": p.tribunal_alias, "email_destino": p.email_destino}

@app.get("/v1/processos")
def listar(db: Session = Depends(get_db)):
    procs = db.query(Processo).all()
    return [{"id": p.id, "numero_cnj": p.numero_cnj, "tribunal_alias": p.tribunal_alias, "email_destino": p.email_destino} for p in procs]

@app.post("/v1/sync")
def sync(admin_token: str, db: Session = Depends(get_db)):
    if admin_token != API_ADMIN_TOKEN:
        raise HTTPException(401, "Token inválido.")
    alterados = sincronizar_todos(db)
    return {"ok": True, "alterados": alterados}
