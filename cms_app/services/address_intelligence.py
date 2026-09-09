"""Conservative, explainable student-address classification.

This module deliberately prefers an unresolved result to an incorrect location.
It does not call an external AI service and never mutates student records itself.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from difflib import get_close_matches


_KNOWN_PLACES = {
    "mahuva": ("Mahuva", "Mahuva", "Bhavnagar", "Gujarat"),
    "kalsar": ("Kalsar", "Mahuva", "Bhavnagar", "Gujarat"),
    "rupavati": ("Rupavati", "Mahuva", "Bhavnagar", "Gujarat"),
    "mota asrana": ("Mota Asrana", "Mahuva", "Bhavnagar", "Gujarat"),
    "konjali": ("Konjali", "Mahuva", "Bhavnagar", "Gujarat"),
    "mota jadra": ("Mota Jadra", "Mahuva", "Bhavnagar", "Gujarat"),
}
_PIN_DIRECTORY = {
    "364290": ("Mahuva", "Mahuva", "Bhavnagar", "Gujarat"),
}


def _clean(value) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" ,.-")


@dataclass(frozen=True)
class AddressClassification:
    city: str = ""
    taluka: str = ""
    district: str = ""
    state: str = ""
    pincode: str = ""
    confidence: int = 0
    source: str = "unresolved"
    review_status: str = "unresolved"
    explanation: str = "No reliable structured location could be found."

    def as_dict(self):
        return asdict(self)


def classify_address(address="", city="", taluka="", district="", state="", pincode="") -> AddressClassification:
    address, city, taluka, district, state, pincode = map(
        _clean, (address, city, taluka, district, state, pincode)
    )
    pin_match = re.search(r"(?<!\d)([1-9]\d{5})(?!\d)", pincode or address)
    pin = pin_match.group(1) if pin_match else ""

    # Spreadsheet columns are explicit user-supplied facts, not an inference.
    if city:
        known = _KNOWN_PLACES.get(city.casefold())
        return AddressClassification(
            city=known[0] if known else city,
            taluka=taluka or (known[1] if known else ""),
            district=district or (known[2] if known else ""),
            state=state or (known[3] if known else ""),
            pincode=pin,
            confidence=100,
            source="spreadsheet",
            review_status="approved",
            explanation="Location was supplied in a structured spreadsheet column.",
        )

    normalized = re.sub(r"[^a-z0-9]+", " ", address.casefold()).strip()
    words = set(normalized.split())
    for key, known in sorted(_KNOWN_PLACES.items(), key=lambda item: -len(item[0])):
        if re.search(rf"\b{re.escape(key)}\b", normalized):
            return AddressClassification(
                city=known[0], taluka=taluka or known[1], district=district or known[2],
                state=state or known[3], pincode=pin, confidence=92,
                source="local_place_directory", review_status="auto_approved",
                explanation=f"Exact known place name '{known[0]}' was found in the address.",
            )

    if pin in _PIN_DIRECTORY:
        known = _PIN_DIRECTORY[pin]
        return AddressClassification(
            city=known[0], taluka=taluka or known[1], district=district or known[2],
            state=state or known[3], pincode=pin, confidence=95,
            source="pincode_directory", review_status="auto_approved",
            explanation=f"PIN code {pin} matched the local location directory.",
        )

    # Conservative fuzzy suggestion: visible to a reviewer, never auto-applied.
    for token in words:
        match = get_close_matches(token, _KNOWN_PLACES.keys(), n=1, cutoff=0.9)
        if match:
            known = _KNOWN_PLACES[match[0]]
            return AddressClassification(
                city=known[0], taluka=taluka or known[1], district=district or known[2],
                state=state or known[3], pincode=pin, confidence=78,
                source="fuzzy_place_match", review_status="needs_review",
                explanation=f"'{token}' resembles known place '{known[0]}'; user confirmation is required.",
            )

    return AddressClassification(
        taluka=taluka, district=district, state=state, pincode=pin,
        confidence=35 if any((taluka, district, state, pin)) else 0,
        source="partial_address" if any((taluka, district, state, pin)) else "unresolved",
        review_status="needs_review" if any((address, taluka, district, state, pin)) else "unresolved",
        explanation="The address needs a city/town/village to be confirmed by a user." if address else "No address was supplied.",
    )
