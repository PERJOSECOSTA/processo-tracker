import hashlib
from datetime import datetime
from sqlalchemy.orm import Session
from .datajud import buscar_processo_por_cnj
from .models import Processo, Movimentacao
from .emailer import enviar_email

def _hash_mov(data: str, titulo: str, desc: str) -> str:
    raw = f"{data}|{titulo}|{desc}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()

def _extrair_movimentacoes(hit_source: dict):
    movs = []
    candidatos = [
        hit_source.get("movimentos"),
        hit_source.get("movimentacoes"),
        hit_source.get("movimento"),
    ]
    arr = next((c for c in candidatos if isinstance(c, list)), [])
    for m in arr:
        data = m.get("dataHora") or m.get("data") or m.get("dataMovimento")
        titulo = m.get("nome") or m.get("titulo") or m.get("descricao") or ""
        desc = m.get("complemento") or m.get("texto") or ""
        movs.append((data, titulo, desc))
    return movs

def sincronizar_processo(db: Session, proc: Processo) -> bool:
    resp = buscar_processo_por_cnj(proc.tribunal_alias, proc.numero_cnj)
    hits = (resp.get("hits") or {}).get("hits") or []
    if not hits:
        return False

    source = hits[0].get("_source") or {}
    movs = _extrair_movimentacoes(source)
    if not movs:
        return False

    data_s, titulo, desc = movs[-1]
    novo_hash = _hash_mov(str(data_s), str(titulo), str(desc))

    if proc.ultimo_hash == novo_hash:
        return False

    dt = None
    try:
        dt = datetime.fromisoformat(str(data_s).replace("Z", "+00:00"))
    except Exception:
        dt = None

    db.add(Movimentacao(
        processo_id=proc.id,
        data=dt,
        titulo=str(titulo)[:500],
        descricao=str(desc),
        origem_hash=novo_hash
    ))
    proc.ultimo_hash = novo_hash
    db.commit()

    assunto = f"[NOVO ANDAMENTO] {proc.numero_cnj} ({proc.tribunal_alias})"
    corpo = (
        f"Processo: {proc.numero_cnj}\n"
        f"Tribunal: {proc.tribunal_alias}\n\n"
        f"Último andamento:\n"
        f"Data: {data_s}\n"
        f"Título: {titulo}\n"
        f"Descrição: {desc}\n"
    )
    enviar_email(proc.email_destino, assunto, corpo)
    return True

def sincronizar_todos(db: Session) -> int:
    procs = db.query(Processo).all()
    alterados = 0
    for p in procs:
        try:
            if sincronizar_processo(db, p):
                alterados += 1
        except Exception:
            db.rollback()
    return alterados
