import re
from dataclasses import dataclass

from weather.countries import country_code

_US_ZIP = re.compile(r"^\d{5}(?:-\d{4})?$")
_UK_POST = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE)
_CA_POST = re.compile(
    r"^[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z]\s?\d[ABCEGHJ-NPRSTV-Z]\d$",
    re.IGNORECASE,
)
_DIGIT_RUN = re.compile(r"^\d{4,10}$")


@dataclass(frozen=True)
class Lookup:
    kind: str
    text: str
    country_code: str = ""


def classify_query(raw: str) -> Lookup | None:
    text = " ".join((raw or "").split())
    if not text:
        return None
    place, explicit = _split_country(text)
    if explicit and _is_postal(place):
        return Lookup("postal", _normalize_postal(place, explicit), explicit)
    inferred = _infer_country(text)
    if inferred:
        return Lookup("postal", _normalize_postal(text, inferred), inferred)
    if _is_postal(text):
        return Lookup("postal", text, "")
    return Lookup("city", text)


def _split_country(text: str) -> tuple[str, str]:
    if "," in text:
        left, right = text.rsplit(",", 1)
        code = country_code(right)
        if code and _is_postal(left):
            return " ".join(left.split()), code
    parts = text.split()
    if len(parts) >= 2:
        code = country_code(parts[-1])
        place = " ".join(parts[:-1])
        if code and _is_postal(place):
            return place, code
    return text, ""


def _is_postal(value: str) -> bool:
    compact = re.sub(r"\s+", "", value)
    if _DIGIT_RUN.fullmatch(compact):
        return True
    if _UK_POST.fullmatch(value.strip()):
        return True
    return _CA_POST.fullmatch(value.strip()) is not None


def _infer_country(value: str) -> str:
    stripped = value.strip()
    if _US_ZIP.fullmatch(stripped):
        return "US"
    if _UK_POST.fullmatch(stripped):
        return "GB"
    if _CA_POST.fullmatch(stripped):
        return "CA"
    return ""


def _normalize_postal(postal: str, country: str) -> str:
    stripped = " ".join(postal.split())
    if country == "US" and _US_ZIP.fullmatch(stripped):
        return stripped[:5]
    if country in {"GB", "CA"}:
        return stripped.upper()
    return stripped
