"""Request-Validierung fuer die Inventory-API (pydantic v2)."""

from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# Einzige Quelle fuer die erlaubten Zustaende - db.py baut daraus den
# CHECK-Constraint, damit DB und Validierung nicht auseinanderlaufen.
CONDITIONS = ("new", "used", "damaged")
Condition = Literal["new", "used", "damaged"]

MAX_TITLE_LENGTH = 120
MAX_CATEGORY_LENGTH = 60
MAX_IMAGE_LENGTH = 255
MAX_COUNT = 1_000_000
MAX_LOCATION_NAME_LENGTH = 80

DEFAULT_CATEGORY = "general"
DEFAULT_CONDITION = "new"


def _normalise_token(value, fallback):
    """Trimmt und kleinschreibt; leere Angaben fallen auf den Default zurueck."""
    if not isinstance(value, str):
        return fallback if value is None else value
    return value.strip().lower() or fallback


class _ItemBase(BaseModel):
    # str_strip_whitespace faengt "   " als Titel ab; extra="forbid" meldet
    # Tippfehler in Feldnamen, statt sie stillschweigend zu verwerfen.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    @field_validator("category", mode="before", check_fields=False)
    @classmethod
    def _normalise_category(cls, value):
        return _normalise_token(value, DEFAULT_CATEGORY)

    @field_validator("image", mode="before", check_fields=False)
    @classmethod
    def _normalise_image(cls, value):
        if not isinstance(value, str):
            return value
        return value.strip() or None

    @field_validator("image", mode="after", check_fields=False)
    @classmethod
    def _validate_image(cls, value):
        """Nur relative, projektinterne Pfade - kein http(s)://, kein ../, kein fuehrender /."""
        if value is None:
            return value
        if "://" in value or value.startswith(("/", "\\")) or ".." in value:
            raise ValueError("image must be a relative path without scheme or '..'")
        return value


class ItemCreate(_ItemBase):
    item: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    # Beim Anlegen ist eine Menge von 0 nicht sinnvoll (Verhalten der Altversion).
    count: int = Field(ge=1, le=MAX_COUNT)
    condition: Condition = DEFAULT_CONDITION
    category: str = Field(default=DEFAULT_CATEGORY, min_length=1, max_length=MAX_CATEGORY_LENGTH)
    image: Optional[str] = Field(default=None, max_length=MAX_IMAGE_LENGTH)
    # None = keinem Lagerort zugeordnet.
    location_id: Optional[int] = Field(default=None, ge=1)

    @field_validator("condition", mode="before")
    @classmethod
    def _normalise_condition(cls, value):
        return _normalise_token(value, DEFAULT_CONDITION)


class ItemUpdate(_ItemBase):
    title: str = Field(min_length=1, max_length=MAX_TITLE_LENGTH)
    # Bestand darf auf 0 fallen (ausverkauft), negativ bleibt ungueltig.
    count: int = Field(ge=0, le=MAX_COUNT)
    category: str = Field(default=DEFAULT_CATEGORY, min_length=1, max_length=MAX_CATEGORY_LENGTH)
    # None = Feld nicht mitgeschickt -> bestehender Wert bleibt erhalten.
    condition: Optional[Condition] = None
    image: Optional[str] = Field(default=None, max_length=MAX_IMAGE_LENGTH)
    # Wie bei LocationUpdate: weggelassen = unveraendert, null = Ort entfernen.
    # Die Unterscheidung laeuft ueber model_fields_set.
    location_id: Optional[int] = Field(default=None, ge=1)

    @field_validator("condition", mode="before")
    @classmethod
    def _normalise_condition(cls, value):
        return _normalise_token(value, None)


class LocationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    name: str = Field(min_length=1, max_length=MAX_LOCATION_NAME_LENGTH)
    # None = Ort liegt auf oberster Ebene.
    parent_id: Optional[int] = Field(default=None, ge=1)


class LocationUpdate(LocationCreate):
    """Wie LocationCreate, aber parent_id unterscheidet drei Faelle.

    Feld weggelassen  -> bisheriges Elternteil bleibt
    parent_id: null   -> Ort wandert auf die oberste Ebene
    parent_id: <id>   -> Ort wandert unter diesen Ort

    Die Unterscheidung zwischen "weggelassen" und "null" laeuft ueber
    model_fields_set, weil beide sonst als None ankaemen.
    """


def format_validation_errors(exc):
    """pydantic-Fehler in eine schlanke, JSON-taugliche Liste uebersetzen."""
    details = []
    for error in exc.errors():
        field = ".".join(str(part) for part in error["loc"]) or "body"
        details.append({"field": field, "message": error["msg"]})
    return details
