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


def sincronizar_processo(db: Session, proc: Processo) -> dict:
    """
    Retorna um dict com:
      - status: "alterado" | "sem_alteracao" | "sem_hits" | "sem_mov"
      - ultimo: {data, titulo, desc} quando disponível
    """
    resp = buscar_processo_por_cnj(proc.tribunal_alias, proc.numero_cnj)
    hits = (resp.get("hits") or {}).get("hits") or []
    if not hits:
        return {"status": "sem_hits"}

    source = hits[0].get("_source") or {}
    movs = _extrair_movimentacoes(source)
    if not movs:
        return {"status": "sem_mov"}

    data_s, titulo, desc = movs[-1]
    novo_hash = _hash_mov(str(data_s), str(titulo), str(desc))

    if proc.ultimo_hash == novo_hash:
        # Sem alteração, mas retornamos o último andamento para constar no relatório diário
        return {
            "status": "sem_alteracao",
            "ultimo": {"data": data_s, "titulo": titulo, "desc": desc},
        }

    dt = None
    try:
        dt = datetime.fromisoformat(str(data_s).replace("Z", "+00:00"))
    except Exception:
        dt = None

    db.add(
        Movimentacao(
            processo_id=proc.id,
            data=dt,
            titulo=str(titulo)[:500],
            descricao=str(desc),
            origem_hash=novo_hash,
        )
    )
    proc.ultimo_hash = novo_hash
    db.commit()

    # Mantemos o e-mail individual de "NOVO ANDAMENTO" (opcional, mas útil)
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

    return {
        "status": "alterado",
        "ultimo": {"data": data_s, "titulo": titulo, "desc": desc},
    }


def sincronizar_todos(db: Session) -> int:
    procs = db.query(Processo).all()
    alterados = 0

    # Agrupa relatório por destinatário
    relatorios = {}  # email -> [linhas]

    for p in procs:
        try:
            r = sincronizar_processo(db, p)
            status = r.get("status")

            if status == "alterado":
                alterados += 1

            # Monta linha amigável para o relatório diário
            prefixo = {
                "alterado": "🟡 ALTERAÇÃO",
                "sem_alteracao": "✅ Sem alterações",
                "sem_hits": "⚪ Sem dados (DataJud)",
                "sem_mov": "⚪ Sem movimentações (DataJud)",
            }.get(status, "⚪ Status desconhecido")

            ultimo = r.get("ultimo") or {}
            data_s = ultimo.get("data")
            titulo = ultimo.get("titulo")
            desc = ultimo.get("desc")

            linha = f"{prefixo} — {p.tribunal_alias} {p.numero_cnj}"
            if data_s or titulo:
                linha += f"\n   Último: {data_s or '-'} | {titulo or '-'}"
            # (opcional) colocar um pedacinho da descrição sem ficar enorme
            if desc:
                desc_txt = str(desc).replace("\n", " ").strip()
                if len(desc_txt) > 200:
                    desc_txt = desc_txt[:200] + "..."
                linha += f"\n   {desc_txt}"

            relatorios.setdefault(p.email_destino, []).append(linha)

        except Exception:
            db.rollback()
            relatorios.setdefault(p.email_destino, []).append(
                f"🔴 ERRO — {p.tribunal_alias} {p.numero_cnj} (falha ao sincronizar)"
            )

    # Envia o e-mail diário (mesmo se alterados == 0)
    hoje = datetime.now().strftime("%d/%m/%Y")
    for email, linhas in relatorios.items():
        assunto = f"[RELATÓRIO DIÁRIO] Monitor de Processos — {hoje} (alterados: {alterados})"
        corpo = "Resumo da verificação de hoje:\n\n" + "\n\n".join(linhas)
        enviar_email(email, assunto, corpo)

    return alterados
