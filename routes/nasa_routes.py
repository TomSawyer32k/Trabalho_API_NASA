from fastapi import APIRouter, Query

from services.nasa_service import (
    buscar_apod,
    listar_categorias_marte,
    buscar_imagens_marte,
    buscar_asteroides,
    buscar_catalogo_asteroides,
    buscar_epic,
    buscar_imagens,
    buscar_eventos,
    buscar_clima_espacial
)

router = APIRouter(prefix="/api", tags=["NASA"])


@router.get("/apod")
async def rota_apod():
    return await buscar_apod()


@router.get("/mars/categories")
async def rota_categorias_marte():
    return await listar_categorias_marte()


@router.get("/mars/images")
async def rota_imagens_marte(
    categoria: str = Query("mars rover"),
    limite: int = Query(6, ge=1, le=12)
):
    return await buscar_imagens_marte(categoria, limite)


@router.get("/asteroids")
async def rota_asteroides(
    start_date: str = Query(...),
    end_date: str | None = Query(None)
):
    return await buscar_asteroides(start_date, end_date)


@router.get("/asteroids/catalog")
async def rota_catalogo_asteroides():
    return await buscar_catalogo_asteroides()


@router.get("/epic")
async def rota_epic(
    limite: int = Query(6, ge=1, le=12)
):
    return await buscar_epic(limite)


@router.get("/images/search")
async def rota_imagens(
    categoria: str = Query("moon"),
    limite: int = Query(6, ge=1, le=12)
):
    return await buscar_imagens(categoria, limite)


@router.get("/eonet/events")
async def rota_eventos(
    limite: int = Query(6, ge=1, le=12)
):
    return await buscar_eventos(limite)


@router.get("/space-weather")
async def rota_clima_espacial():
    return await buscar_clima_espacial()