"""Maps / routing provider abstraction."""
from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


@dataclass
class GeoPoint:
    lat: float
    lng: float


@dataclass
class RouteResult:
    distance_meters: float
    duration_seconds: float
    geometry: list[list[float]] | None = None  # [[lng, lat], ...]
    provider: str = "none"


class MapsProvider(ABC):
    @abstractmethod
    async def geocode(self, address: str) -> GeoPoint | None:
        ...

    @abstractmethod
    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteResult | None:
        ...

    @abstractmethod
    async def distance_matrix(
        self, origins: list[GeoPoint], destinations: list[GeoPoint]
    ) -> list[list[float]] | None:
        """Return matrix of distances in meters."""
        ...


class NoneMapsProvider(MapsProvider):
    async def geocode(self, address: str) -> GeoPoint | None:
        return None

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteResult | None:
        return None

    async def distance_matrix(
        self, origins: list[GeoPoint], destinations: list[GeoPoint]
    ) -> list[list[float]] | None:
        return None


class GoogleMapsProvider(MapsProvider):
    BASE = "https://maps.googleapis.com/maps/api"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def geocode(self, address: str) -> GeoPoint | None:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE}/geocode/json",
                params={"address": address, "key": self.api_key},
            )
            data = r.json()
            if data.get("status") != "OK" or not data.get("results"):
                return None
            loc = data["results"][0]["geometry"]["location"]
            return GeoPoint(lat=loc["lat"], lng=loc["lng"])

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteResult | None:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE}/directions/json",
                params={
                    "origin": f"{origin.lat},{origin.lng}",
                    "destination": f"{destination.lat},{destination.lng}",
                    "key": self.api_key,
                    "mode": "driving",
                },
            )
            data = r.json()
            if data.get("status") != "OK" or not data.get("routes"):
                return None
            leg = data["routes"][0]["legs"][0]
            return RouteResult(
                distance_meters=float(leg["distance"]["value"]),
                duration_seconds=float(leg["duration"]["value"]),
                provider="google",
            )

    async def distance_matrix(
        self, origins: list[GeoPoint], destinations: list[GeoPoint]
    ) -> list[list[float]] | None:
        o = "|".join(f"{p.lat},{p.lng}" for p in origins)
        d = "|".join(f"{p.lat},{p.lng}" for p in destinations)
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE}/distancematrix/json",
                params={
                    "origins": o,
                    "destinations": d,
                    "key": self.api_key,
                    "mode": "driving",
                },
            )
            data = r.json()
            if data.get("status") != "OK":
                return None
            matrix = []
            for row in data.get("rows", []):
                matrix.append(
                    [
                        float(el["distance"]["value"])
                        if el.get("status") == "OK"
                        else -1.0
                        for el in row.get("elements", [])
                    ]
                )
            return matrix


class MapboxProvider(MapsProvider):
    BASE = "https://api.mapbox.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def geocode(self, address: str) -> GeoPoint | None:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE}/geocoding/v5/mapbox.places/{httpx.URL(address)}.json",
                params={"access_token": self.api_key, "limit": 1},
            )
            data = r.json()
            features = data.get("features") or []
            if not features:
                return None
            lng, lat = features[0]["center"]
            return GeoPoint(lat=lat, lng=lng)

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteResult | None:
        coords = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE}/directions/v5/mapbox/driving/{coords}",
                params={"access_token": self.api_key, "geometries": "geojson"},
            )
            data = r.json()
            routes = data.get("routes") or []
            if not routes:
                return None
            route = routes[0]
            geometry = route.get("geometry", {}).get("coordinates")
            return RouteResult(
                distance_meters=float(route.get("distance", 0)),
                duration_seconds=float(route.get("duration", 0)),
                geometry=geometry,
                provider="mapbox",
            )

    async def distance_matrix(
        self, origins: list[GeoPoint], destinations: list[GeoPoint]
    ) -> list[list[float]] | None:
        # Simplified: pairwise via directions (Mapbox Matrix API needs different endpoint)
        matrix: list[list[float]] = []
        for o in origins:
            row = []
            for d in destinations:
                r = await self.route(o, d)
                row.append(r.distance_meters if r else -1.0)
            matrix.append(row)
        return matrix


class OSRMProvider(MapsProvider):
    """Free OpenStreetMap routing (public demo server — not for heavy production)."""

    BASE = "https://router.project-osrm.org"

    async def geocode(self, address: str) -> GeoPoint | None:
        # Use Nominatim
        async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "VELORA/1.0"}) as client:
            r = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": address, "format": "json", "limit": 1},
            )
            data = r.json()
            if not data:
                return None
            return GeoPoint(lat=float(data[0]["lat"]), lng=float(data[0]["lon"]))

    async def route(self, origin: GeoPoint, destination: GeoPoint) -> RouteResult | None:
        coords = f"{origin.lng},{origin.lat};{destination.lng},{destination.lat}"
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{self.BASE}/route/v1/driving/{coords}",
                params={"overview": "false"},
            )
            data = r.json()
            if data.get("code") != "Ok" or not data.get("routes"):
                return None
            route = data["routes"][0]
            return RouteResult(
                distance_meters=float(route.get("distance", 0)),
                duration_seconds=float(route.get("duration", 0)),
                provider="osm",
            )

    async def distance_matrix(
        self, origins: list[GeoPoint], destinations: list[GeoPoint]
    ) -> list[list[float]] | None:
        matrix = []
        for o in origins:
            row = []
            for d in destinations:
                r = await self.route(o, d)
                row.append(r.distance_meters if r else -1.0)
            matrix.append(row)
        return matrix


def get_maps_provider() -> MapsProvider:
    provider = (settings.maps_provider or "none").lower()
    key = settings.maps_api_key or ""
    if provider == "google" and key:
        return GoogleMapsProvider(key)
    if provider == "mapbox" and key:
        return MapboxProvider(key)
    if provider in ("osm", "osrm", "openstreetmap"):
        return OSRMProvider()
    return NoneMapsProvider()
