from contextlib import asynccontextmanager
from time import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.nasa_routes import router as nasa_router
from services.nasa_service import fechar_cliente


REQUESTS = {}
RATE_LIMIT = 40
WINDOW = 60


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await fechar_cliente()


app = FastAPI(
    title="NASA Explorer API",
    description="API intermediária desenvolvida com FastAPI para consultar dados públicos da NASA.",
    version="2.2.0",
    lifespan=lifespan
)


@app.middleware("http")
async def limitar_requisicoes(request: Request, call_next):
    if request.url.path.startswith(("/docs", "/openapi", "/static")):
        return await call_next(request)

    ip = request.client.host
    agora = time()

    historico = REQUESTS.get(ip, [])
    historico = [t for t in historico if agora - t < WINDOW]

    if len(historico) >= RATE_LIMIT:
        return JSONResponse(
            status_code=429,
            content={"detail": "Muitas requisições. Aguarde alguns segundos e tente novamente."}
        )

    historico.append(agora)
    REQUESTS[ip] = historico

    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000"
    ],
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(nasa_router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")