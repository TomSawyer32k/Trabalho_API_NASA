import os
import asyncio
from datetime import datetime, date

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from cachetools import TTLCache

load_dotenv()

NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
NASA_TIMEOUT = int(os.getenv("NASA_TIMEOUT", 5))
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))
CACHE_MAX_SIZE = int(os.getenv("CACHE_MAX_SIZE", 1000))

cache = TTLCache(maxsize=CACHE_MAX_SIZE, ttl=CACHE_TTL)
stale_cache = {}

client = httpx.AsyncClient(
    timeout=httpx.Timeout(NASA_TIMEOUT, connect=3),
    follow_redirects=True,
    limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
    headers={
        "User-Agent": "NASA-Explorer-FastAPI/3.0",
        "Accept": "application/json"
    }
)

semaforo = asyncio.Semaphore(8)


def limitar(valor, minimo=1, maximo=12):
    return min(max(int(valor), minimo), maximo)


def chave_cache(url, params=None):
    params = params or {}
    return f"{url}-{tuple(sorted(params.items()))}"


def validar_data(data):
    try:
        datetime.strptime(data, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(status_code=400, detail="Data inválida. Use YYYY-MM-DD.")


async def consultar_nasa(url, params=None):
    params = params or {}
    key = chave_cache(url, params)

    if key in cache:
        return cache[key]

    async with semaforo:
        try:
            resposta = await client.get(url, params=params)

            if resposta.status_code == 429 and key in stale_cache:
                return stale_cache[key]

            if resposta.status_code == 404:
                return {}

            resposta.raise_for_status()

            dados = resposta.json()
            cache[key] = dados
            stale_cache[key] = dados

            return dados

        except httpx.TimeoutException:
            if key in stale_cache:
                return stale_cache[key]
            raise HTTPException(status_code=504, detail="A NASA demorou muito para responder.")

        except httpx.HTTPStatusError:
            if key in stale_cache:
                return stale_cache[key]
            raise HTTPException(status_code=resposta.status_code, detail="Erro retornado pela NASA.")

        except httpx.RequestError:
            if key in stale_cache:
                return stale_cache[key]
            raise HTTPException(status_code=503, detail="Falha de conexão com a NASA.")


def extrair_imagens(dados, limite):
    itens = dados.get("collection", {}).get("items", [])
    imagens = []

    for item in itens:
        data_item = item.get("data", [{}])[0]
        links = item.get("links", [])

        if not links:
            continue

        href = links[0].get("href")

        if not href:
            continue

        imagens.append({
            "titulo": data_item.get("title", "Imagem NASA"),
            "descricao": data_item.get("description", "Sem descrição disponível."),
            "imagem": href
        })

        if len(imagens) >= limite:
            break

    return imagens


async def buscar_apod():
    try:
        dados = await consultar_nasa(
            "https://api.nasa.gov/planetary/apod",
            {
                "api_key": NASA_API_KEY,
                "thumbs": True
            }
        )

        return {
            "title": dados.get("title") or "Imagem astronômica do dia",
            "date": dados.get("date") or "Data não informada",
            "explanation": dados.get("explanation") or "A NASA não retornou uma descrição no momento.",
            "url": dados.get("url"),
            "media_type": dados.get("media_type") or "image"
        }

    except HTTPException:
        return {
            "title": "Imagem astronômica indisponível no momento",
            "date": "Tente novamente mais tarde",
            "explanation": "A consulta à NASA demorou mais do que o esperado. As outras seções continuam funcionando normalmente.",
            "url": "",
            "media_type": "text"
        }


async def listar_categorias_marte():
    return {
        "categorias": [
            {"valor": "mars rover", "nome": "Rovers em Marte"},
            {"valor": "perseverance mars", "nome": "Perseverance"},
            {"valor": "curiosity mars", "nome": "Curiosity"},
            {"valor": "mars surface", "nome": "Superfície de Marte"},
            {"valor": "mars landscape", "nome": "Paisagens de Marte"},
            {"valor": "mars", "nome": "Marte"}
        ]
    }


async def buscar_imagens_marte(categoria="mars rover", limite=6):
    limite = limitar(limite)

    permitidas = {
        "mars",
        "mars rover",
        "curiosity mars",
        "perseverance mars",
        "mars surface",
        "mars landscape"
    }

    termo = categoria if categoria in permitidas else "mars rover"

    dados = await consultar_nasa(
        "https://images-api.nasa.gov/search",
        {
            "q": termo,
            "media_type": "image"
        }
    )

    imagens = extrair_imagens(dados, limite)

    return {
        "fonte": "NASA Image and Video Library",
        "categoria": termo,
        "quantidade": len(imagens),
        "imagens": imagens
    }


async def buscar_asteroides(start_date, end_date=None):
    validar_data(start_date)

    params = {
        "api_key": NASA_API_KEY,
        "start_date": start_date
    }

    if end_date:
        validar_data(end_date)
        params["end_date"] = end_date

    dados = await consultar_nasa(
        "https://api.nasa.gov/neo/rest/v1/feed",
        params
    )

    objetos = dados.get("near_earth_objects", {})
    lista = []

    for data_atual, itens in objetos.items():
        for ast in itens:
            lista.append({
                "name": ast.get("name"),
                "date": data_atual,
                "dangerous": ast.get("is_potentially_hazardous_asteroid"),
                "magnitude": ast.get("absolute_magnitude_h"),
                "diameter": ast.get("estimated_diameter", {})
                    .get("meters", {})
                    .get("estimated_diameter_max")
            })

    return {
        "quantidade": len(lista[:12]),
        "asteroides": lista[:12]
    }


async def buscar_catalogo_asteroides():
    dados = await consultar_nasa(
        "https://api.nasa.gov/neo/rest/v1/neo/browse",
        {
            "api_key": NASA_API_KEY
        }
    )

    objetos = dados.get("near_earth_objects", [])

    return [
        {
            "id": obj.get("id"),
            "nome": obj.get("name"),
            "magnitude": obj.get("absolute_magnitude_h"),
            "perigoso": obj.get("is_potentially_hazardous_asteroid")
        }
        for obj in objetos[:20]
    ]


async def buscar_epic(limite=6):
    limite = limitar(limite)

    dados = await consultar_nasa(
        "https://api.nasa.gov/EPIC/api/natural",
        {"api_key": NASA_API_KEY}
    )

    if not isinstance(dados, list):
        return []

    return [
        {
            "image": item.get("image"),
            "caption": item.get("caption"),
            "date": item.get("date")
        }
        for item in dados[:limite]
    ]


async def buscar_imagens(categoria="moon", limite=6):
    limite = limitar(limite)

    categorias = {
        "moon": "moon nasa",
        "mars": "mars rover",
        "earth": "earth planet",
        "galaxy": "galaxy nasa",
        "nebula": "nebula nasa",
        "apollo": "apollo mission",
        "jupiter": "jupiter planet",
        "saturn": "saturn planet"
    }

    termo = categorias.get(categoria, "moon nasa")

    dados = await consultar_nasa(
        "https://images-api.nasa.gov/search",
        {
            "q": termo,
            "media_type": "image"
        }
    )

    imagens = extrair_imagens(dados, limite)

    return {
        "fonte": "NASA Image and Video Library",
        "categoria": categoria,
        "quantidade": len(imagens),
        "imagens": imagens
    }


async def buscar_eventos(limite=6):
    limite = limitar(limite)

    dados = await consultar_nasa(
        "https://eonet.gsfc.nasa.gov/api/v3/events",
        {
            "limit": limite,
            "status": "open"
        }
    )

    eventos = dados.get("events", [])

    return {
        "events": [
            {
                "id": evento.get("id"),
                "title": evento.get("title"),
                "categories": evento.get("categories", [])
            }
            for evento in eventos[:limite]
        ]
    }


async def buscar_clima_espacial():
    try:
        ano_atual = date.today().year

        dados = await consultar_nasa(
            "https://api.nasa.gov/DONKI/FLR",
            {
                "api_key": NASA_API_KEY,
                "startDate": f"{ano_atual}-01-01"
            }
        )

        if not isinstance(dados, list):
            return []

        return [
            {
                "flrID": evento.get("flrID"),
                "classType": evento.get("classType"),
                "beginTime": evento.get("beginTime"),
                "peakTime": evento.get("peakTime"),
                "sourceLocation": evento.get("sourceLocation")
            }
            for evento in dados[:6]
        ]

    except HTTPException:
        return []


async def fechar_cliente():
    await client.aclose()