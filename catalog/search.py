from difflib import SequenceMatcher
from .models import normalize


def search(items, query):
    if query and items.filter(barcode=query).exists():
        return items.filter(barcode=query), False
    words = normalize(query).split()
    if not words:
        return items, False
    exact, suggestions = [], []
    for medicine in items:
        text = normalize(f'{medicine.name} {medicine.active_ingredients} {medicine.alternative_names}')
        if all(word in text for word in words):
            exact.append(medicine)
        elif all(any(SequenceMatcher(None, word, candidate).ratio() >= .78
                     for candidate in text.split()) for word in words):
            suggestions.append(medicine)
    return (exact, False) if exact else (suggestions, bool(suggestions))
