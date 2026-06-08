import json
import os
import requests
from datetime import datetime, timezone, timedelta
from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

API_BASE     = "https://sas.anac.gov.br/sas/siros_api"
airports_env = os.environ.get("AIRPORTS", "SBCA")
AIRPORTS     = [a.strip().upper() for a in airports_env.split(",") if a.strip()]

# Horario de Brasilia: UTC-3
BRT  = timezone(timedelta(hours=-3))
hoje = datetime.now(BRT)

# Formato exigido pela API: DDMMYYYY
data_ref = hoje.strftime("%d%m%Y")
data_iso = hoje.strftime("%Y-%m-%d")

print(f"SIROS/ANAC — Data: {hoje.strftime('%d/%m/%Y')} | Aeroportos: {', '.join(AIRPORTS)}")

# ── Mapeamentos ───────────────────────────────────────────────────────────────

# icao -> (nome, cidade, estado)
AIRPORT_INFO = {
    "SBRB": ("Aeroporto Internacional Plácido de Castro",    "Rio Branco",              "AC"),
    "SBMO": ("Aeroporto Internacional Zumbi dos Palmares",   "Maceió",                  "AL"),
    "SBMQ": ("Aeroporto Internacional Alberto Alcolumbre",   "Macapá",                  "AP"),
    "SBEG": ("Aeroporto Internacional Eduardo Gomes",        "Manaus",                  "AM"),
    "SBSV": ("Aeroporto Internacional Dep. L. E. Magalhães", "Salvador",                "BA"),
    "SBIL": ("Aeroporto Jorge Amado",                        "Ilhéus",                  "BA"),
    "SBPS": ("Aeroporto de Porto Seguro",                    "Porto Seguro",            "BA"),
    "SBFZ": ("Aeroporto Internacional Pinto Martins",        "Fortaleza",               "CE"),
    "SBJU": ("Aeroporto Regional Cariri",                    "Juazeiro do Norte",       "CE"),
    "SBBR": ("Aeroporto Internacional de Brasília",          "Brasília",                "DF"),
    "SBVT": ("Aeroporto de Vitória",                         "Vitória",                 "ES"),
    "SBGO": ("Aeroporto Santa Genoveva",                     "Goiânia",                 "GO"),
    "SBSL": ("Aeroporto Internacional Marechal Cunha Machado","São Luís",               "MA"),
    "SBCY": ("Aeroporto Internacional Marechal Rondon",      "Cuiabá",                  "MT"),
    "SBCG": ("Aeroporto Internacional A. J. Palhano",        "Campo Grande",            "MS"),
    "SBCF": ("Aeroporto Internacional Tancredo Neves",       "Belo Horizonte",          "MG"),
    "SBBH": ("Aeroporto da Pampulha",                        "Belo Horizonte",          "MG"),
    "SBUL": ("Aeroporto Ten. Cel. Av. César Bombonato",      "Uberlândia",              "MG"),
    "SBBE": ("Aeroporto Internacional Val de Cans",          "Belém",                   "PA"),
    "SBSN": ("Aeroporto de Santarém",                        "Santarém",                "PA"),
    "SBJP": ("Aeroporto Internacional Presidente Castro Pinto","João Pessoa",           "PB"),
    "SBCT": ("Aeroporto Internacional Afonso Pena",          "Curitiba",                "PR"),
    "SBFI": ("Aeroporto Internacional Foz do Iguaçu",        "Foz do Iguaçu",           "PR"),
    "SBCA": ("Aeroporto Municipal de Cascavel",              "Cascavel",                "PR"),
    "SBLO": ("Aeroporto Governador José Richa",              "Londrina",                "PR"),
    "SBMG": ("Aeroporto Regional de Maringá",                "Maringá",                 "PR"),
    "SBRF": ("Aeroporto Internacional do Recife",            "Recife",                  "PE"),
    "SBTE": ("Aeroporto Senador Petrônio Portela",           "Teresina",                "PI"),
    "SBGL": ("Aeroporto Internacional do Galeão",            "Rio de Janeiro",          "RJ"),
    "SBRJ": ("Aeroporto Santos Dumont",                      "Rio de Janeiro",          "RJ"),
    "SBSG": ("Aeroporto Internacional Governador Aluízio Alves","Natal",                "RN"),
    "SBPA": ("Aeroporto Internacional Salgado Filho",        "Porto Alegre",            "RS"),
    "SBCX": ("Aeroporto Internacional Hugo Cantergiani",     "Caxias do Sul",           "RS"),
    "SBPV": ("Aeroporto Internacional Gov. Jorge Teixeira",  "Porto Velho",             "RO"),
    "SBBV": ("Aeroporto Internacional Atlas Brasil Cantanhede","Boa Vista",             "RR"),
    "SBFL": ("Aeroporto Internacional Hercílio Luz",         "Florianópolis",           "SC"),
    "SBJV": ("Aeroporto Lauro Carneiro de Loyola",           "Joinville",               "SC"),
    "SBNF": ("Aeroporto Internacional Ministro Victor Konder","Navegantes",             "SC"),
    "SBGR": ("Aeroporto Internacional de Guarulhos",         "São Paulo",               "SP"),
    "SBSP": ("Aeroporto de Congonhas",                       "São Paulo",               "SP"),
    "SBKP": ("Aeroporto Internacional de Viracopos",         "Campinas",                "SP"),
    "SBRP": ("Aeroporto Leite Lopes",                        "Ribeirão Preto",          "SP"),
    "SBSE": ("Aeroporto Santa Maria",                        "Aracaju",                 "SE"),
    "SBPJ": ("Aeroporto de Palmas",                          "Palmas",                  "TO"),
}

# Atalho só com nomes (usado internamente para rota_nome)
AIRPORT_NAMES = {icao: info[0] for icao, info in AIRPORT_INFO.items()}

AIRLINES = {
    "GLO":"GOL","TAM":"LATAM","AZU":"Azul","ONE":"VOEPASS",
    "PTB":"Passaredo","TAP":"TAP Portugal","DAL":"Delta","UAL":"United",
    "AFR":"Air France","DLH":"Lufthansa","IBE":"Iberia","AAL":"American Airlines",
    "LAN":"LATAM Internacional","AVA":"Avianca","BAW":"British Airways",
    "UAE":"Emirates","THY":"Turkish Airlines","ETH":"Ethiopian Airlines",
    "SWR":"Swiss","ACA":"Air Canada","AMX":"Aeromexico","SAA":"South African",
    "SKU":"Sky Airline","CMP":"Copa Airlines","TSC":"Air Transat",
}

EQUIPAMENTOS = {
    "A20N":"Airbus A320neo","A21N":"Airbus A321neo","A319":"Airbus A319",
    "A320":"Airbus A320","A321":"Airbus A321","A332":"Airbus A330-200",
    "A333":"Airbus A330-300","A339":"Airbus A330-900neo","A35K":"Airbus A350-900",
    "A359":"Airbus A350-900","A388":"Airbus A380","B737":"Boeing 737",
    "B738":"Boeing 737-800","B739":"Boeing 737-900","B38M":"Boeing 737 MAX 8",
    "B748":"Boeing 747-8","B763":"Boeing 767-300","B764":"Boeing 767-400",
    "B772":"Boeing 777-200","B773":"Boeing 777-300","B77W":"Boeing 777-300ER",
    "B788":"Boeing 787-8","B789":"Boeing 787-9","E190":"Embraer E190",
    "E195":"Embraer E195","E295":"Embraer E195-E2","AT76":"ATR 72",
}


def get_airline(icao: str) -> str:
    return AIRLINES.get((icao or "").strip().upper(), icao or "?")


def get_equip(icao: str) -> str:
    return EQUIPAMENTOS.get((icao or "").strip().upper(), icao or "?")


def parse_siros_dt(dt_str: str) -> str:
    if not dt_str or len(dt_str) < 16:
        return ""
    try:
        # Formato da API: "31/12/2026 23:45"
        dt_utc = datetime.strptime(dt_str.strip(), "%d/%m/%Y %H:%M")
        dt_utc = dt_utc.replace(tzinfo=timezone.utc)
        dt_brt = dt_utc.astimezone(BRT)
        return dt_brt.isoformat()
    except Exception:
        return dt_str


def fmt_hora(dt_str: str) -> str:
    """Extrai apenas HH:MM de uma string ISO com timezone."""
    if not dt_str:
        return "?"
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime("%H:%M")
    except Exception:
        return dt_str


def get_tipo_operacao(ds_tipo_servico: str) -> str:
    s = (ds_tipo_servico or "").upper()
    if "INTERNAC" in s:
        return "Internacional"
    return "Domestico"


# ── Airports.json (para o frontend) ──────────────────────────────────────────

def gerar_airports_json() -> None:
    """Gera data/airports.json com a lista de aeroportos para os selects do painel."""
    lista = [
        {"icao": icao, "name": info[0], "city": info[1], "state": info[2]}
        for icao, info in sorted(AIRPORT_INFO.items())
    ]
    os.makedirs("data", exist_ok=True)
    with open("data/airports.json", "w", encoding="utf-8") as fh:
        json.dump(lista, fh, ensure_ascii=False, indent=2)
    print(f"  Gerado: data/airports.json ({len(lista)} aeroportos)")


# ── Busca principal ───────────────────────────────────────────────────────────

def buscar_todos_voos() -> list:
    url = f"{API_BASE}/voos"
    params = {"dataReferencia": data_ref}

    print(f"\nGET {url}?dataReferencia={data_ref}")

    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()

        # A API pode retornar uma lista diretamente ou uma string JSON escapada
        decoded = r.json()

        if isinstance(decoded, list):
            voos = decoded
        elif isinstance(decoded, str):
            voos = json.loads(decoded)
        else:
            print(f"  [AVISO] Tipo inesperado na resposta: {type(decoded)}")
            return []

        print(f"  Total de voos retornados: {len(voos)}")
        return voos

    except Exception:
        import traceback
        traceback.print_exc()
        return []


def filtrar_aeroporto(todos_voos: list, icao: str):
    """Separa chegadas e partidas para um aeroporto específico."""
    chegadas = []
    partidas = []

    for f in todos_voos:
        origem  = (f.get("sg_icao_origem")  or "").strip().upper()
        destino = (f.get("sg_icao_destino") or "").strip().upper()

        if origem != icao and destino != icao:
            continue

        empresa  = (f.get("sg_empresa_icao")        or "").strip()
        nr_voo   = (f.get("nr_voo")                 or "").strip().lstrip("0") or "?"
        equip    = (f.get("sg_equipamento_icao")     or "").strip()
        assentos = (f.get("qt_assentos_previstos")   or "").strip()
        partida  = (f.get("dt_partida_prevista_utc") or "").strip()
        chegada  = (f.get("dt_chegada_prevista_utc") or "").strip()
        tipo_srv = (f.get("ds_tipo_servico")         or "").strip()

        partida_iso = parse_siros_dt(partida)
        chegada_iso = parse_siros_dt(chegada)

        # ── Nomes de campo alinhados com a tabela voos do Supabase ──
        registro = {
            "data_referencia":  data_iso,
            "airport_icao":     icao,
            "callsign":         f"{empresa}{nr_voo}",
            "numero_voo":       nr_voo,
            "airline_icao":     empresa,
            "airline":          get_airline(empresa),
            "equipamento_icao": equip,
            "equipamento":      get_equip(equip),
            "assentos":         assentos,
            "etapa":            str(f.get("nr_etapa") or ""),
            "tipo_operacao":    get_tipo_operacao(tipo_srv),
            "tipo_servico":     tipo_srv,
            "origem_icao":      origem,
            "destino_icao":     destino,
            "partida_iso":      partida_iso,
            "chegada_iso":      chegada_iso,
            "partida_brt":      fmt_hora(partida_iso),
            "chegada_brt":      fmt_hora(chegada_iso),
            "status":           "programado",
            "fonte":            "SIROS/ANAC",
        }

        if destino == icao:
            registro["rota"]      = origem
            registro["rota_nome"] = AIRPORT_NAMES.get(origem, origem)
            chegadas.append(registro)

        if origem == icao:
            registro["rota"]      = destino
            registro["rota_nome"] = AIRPORT_NAMES.get(destino, destino)
            partidas.append(registro)

    chegadas.sort(key=lambda x: x.get("chegada_iso") or "")
    partidas.sort(key=lambda x: x.get("partida_iso") or "")
    return chegadas, partidas


def buscar_aerodromo(icao: str) -> dict:
    try:
        r = requests.get(
            f"{API_BASE}/aerodromo",
            params={"sg_aerodromo_icao_ou_iata": icao},
            timeout=30
        )
        r.raise_for_status()
        data = r.json()
        if isinstance(data, str):
            data = json.loads(data)
        if isinstance(data, list) and data:
            return data[0]
        if isinstance(data, dict):
            return data
        return {}
    except Exception as e:
        print(f"  [AVISO] Aerodromo {icao}: {e}")
        return {}


def enviar_supabase(icao: str, chegadas: list, partidas: list) -> None:
    """Upsert de chegadas e partidas no Supabase (evita duplicatas ao reprocessar)."""
    voos = chegadas + partidas
    if not voos:
        return
    try:
        supabase.table("voos").upsert(
            voos,
            on_conflict="data_referencia,airport_icao,numero_voo,origem_icao,destino_icao"
        ).execute()
        print(f"  {len(voos)} voos enviados ao Supabase")
    except Exception as e:
        print("  Erro ao enviar para o Supabase:", e)


# ── Execucao ──────────────────────────────────────────────────────────────────

os.makedirs("data", exist_ok=True)
gerar_airports_json()

todos_voos = buscar_todos_voos()

if not todos_voos:
    print("\n[AVISO] Nenhum voo retornado. Verifique a URL e o formato da data.")
else:
    for icao in AIRPORTS:
        info = AIRPORT_INFO.get(icao, (icao, icao, "?"))
        print(f"\nProcessando {icao} — {info[0]}...")

        chegadas, partidas = filtrar_aeroporto(todos_voos, icao)
        print(f"  {len(chegadas)} chegadas, {len(partidas)} partidas")

        aerodromo = buscar_aerodromo(icao)
        nome_oficial = (
            aerodromo.get("nm_aerodromo") or
            aerodromo.get("nome") or
            info[0]
        )

        output = {
            "updated_at":      datetime.now(timezone.utc).isoformat(),
            "data_referencia": data_iso,
            "airport_icao":    icao,
            "airport_name":    nome_oficial,
            "airport_info":    aerodromo,
            "source":          "SIROS/ANAC",
            "source_url":      "https://sas.anac.gov.br/sas/siros_api/",
            "arrivals":        chegadas,
            "departures":      partidas,
        }

        with open(f"data/{icao}.json", "w", encoding="utf-8") as fh:
            json.dump(output, fh, ensure_ascii=False, indent=2)

        print(f"  Salvo: data/{icao}.json")

        enviar_supabase(icao, chegadas, partidas)

print("\nConcluido.")

# Registra execução na tabela opcional (para o card "Último pipeline" no painel)
try:
    total_voos = sum(
        len(filtrar_aeroporto(todos_voos, icao)[0]) +
        len(filtrar_aeroporto(todos_voos, icao)[1])
        for icao in AIRPORTS
    ) if todos_voos else 0
    supabase.table("execucoes").insert({
        "aeroportos": AIRPORTS,
        "total_voos": total_voos,
    }).execute()
except Exception:
    pass  # tabela execucoes e opcional