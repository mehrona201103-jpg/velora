"""Maps API — geocode and route (requires MAPS_PROVIDER + key)."""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.integrations.maps import get_maps_provider, GeoPoint
from app.core.exceptions import ValidationError

router = APIRouter()


class GeocodeRequest(BaseModel):
    address: str = Field(..., min_length=3)


class Point(BaseModel):
    lat: float
    lng: float


class RouteRequest(BaseModel):
    origin: Point
    destination: Point


@router.post("/geocode")
async def geocode(data: GeocodeRequest):
    provider = get_maps_provider()
    point = await provider.geocode(data.address)
    if not point:
        raise ValidationError("Адрес не найден или Maps не настроен")
    return {"lat": point.lat, "lng": point.lng}


@router.post("/route")
async def route(data: RouteRequest):
    provider = get_maps_provider()
    result = await provider.route(
        GeoPoint(lat=data.origin.lat, lng=data.origin.lng),
        GeoPoint(lat=data.destination.lat, lng=data.destination.lng),
    )
    if not result:
        raise ValidationError("Маршрут не найден или Maps не настроен")
    return {
        "distance_meters": result.distance_meters,
        "duration_seconds": result.duration_seconds,
        "provider": result.provider,
        "geometry": result.geometry,
    }
