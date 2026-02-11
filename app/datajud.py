import os, requests

DATAJUD_APIKEY = os.getenv("DATAJUD_APIKEY")

def buscar_processo_por_cnj(tribunal_alias: str, numero_cnj_sem_mascara: str) -> dict:
    url = f"https://api-publica.datajud.cnj.jus.br/{tribunal_alias}/_search"
    headers = {
        "Authorization": f"APIKey {DATAJUD_APIKEY}",
        "Content-Type": "application/json",
    }
    body = {
        "query": {"match": {"numeroProcesso": numero_cnj_sem_mascara}},
        "size": 1
    }
    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return r.json()
