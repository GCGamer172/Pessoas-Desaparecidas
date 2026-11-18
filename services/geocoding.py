import json
import os
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen


STATE_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AP": "Amapá",
    "AM": "Amazonas",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MG": "Minas Gerais",
    "PA": "Pará",
    "PB": "Paraíba",
    "PR": "Paraná",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RS": "Rio Grande do Sul",
    "RO": "Rondônia",
    "RR": "Roraima",
    "SC": "Santa Catarina",
    "SP": "São Paulo",
    "SE": "Sergipe",
    "TO": "Tocantins",
}

_REQUEST_LOCK = threading.Lock()
_LAST_REQUEST_AT = 0.0
_MIN_REQUEST_INTERVAL = 1.1
GEOCODER_SEARCH_URL = os.getenv(
    "MISSING_PERSONS_GEOCODER_URL",
    "https://nominatim.openstreetmap.org/search",
)


class GeocodingError(RuntimeError):
    """Raised when the city lookup service cannot provide a reliable result."""


def geocode_city(city: str, state: str) -> tuple[float, float] | None:
    state_name = STATE_NAMES.get(state.upper())
    if not city.strip() or state_name is None:
        raise ValueError("Informe uma cidade e uma sigla válida de estado.")

    query = urlencode(
        {
            "city": city.strip(),
            "state": state_name,
            "country": "Brasil",
            "format": "jsonv2",
            "limit": 1,
        }
    )
    service_url = urlparse(GEOCODER_SEARCH_URL)
    if service_url.scheme != "https" or not service_url.netloc:
        raise GeocodingError("Configure um serviço de localização seguro (HTTPS).")
    request = Request(
        f"{GEOCODER_SEARCH_URL}?{query}",
        headers={
            "User-Agent": "MissingPersonsPrototype/1.0 (city-level map lookup)"
        },
    )
    global _LAST_REQUEST_AT
    try:
        with _REQUEST_LOCK:
            wait = _MIN_REQUEST_INTERVAL - (time.monotonic() - _LAST_REQUEST_AT)
            if wait > 0:
                time.sleep(wait)
            with urlopen(request, timeout=10) as response:
                result = json.loads(response.read().decode("utf-8"))
            _LAST_REQUEST_AT = time.monotonic()
    except (HTTPError, URLError, TimeoutError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GeocodingError("Não foi possível consultar a localização da cidade.") from exc

    if not result:
        return None

    try:
        latitude = float(result[0]["lat"])
        longitude = float(result[0]["lon"])
    except (KeyError, TypeError, ValueError, IndexError) as exc:
        raise GeocodingError("O serviço retornou coordenadas inválidas.") from exc
    if not -35 <= latitude <= 6 or not -75 <= longitude <= -34:
        return None
    return latitude, longitude
