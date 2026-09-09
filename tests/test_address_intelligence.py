from cms_app.services.address_intelligence import classify_address


def test_structured_city_is_authoritative():
    result = classify_address("Some address", city="Kalsar", district="Bhavnagar")
    assert result.city == "Kalsar"
    assert result.taluka == "Mahuva"
    assert result.review_status == "approved"
    assert result.confidence == 100


def test_exact_place_in_address_is_auto_classified():
    result = classify_address("Near Bus Stand, Kalsar, Dist Bhavnagar")
    assert result.city == "Kalsar"
    assert result.taluka == "Mahuva"
    assert result.review_status == "auto_approved"
    assert result.confidence >= 90


def test_unknown_address_requires_review_instead_of_guessing():
    result = classify_address("Near Old Temple, Unknown Hamlet")
    assert not result.city
    assert result.review_status == "needs_review"


def test_blank_address_is_unresolved():
    result = classify_address("")
    assert result.review_status == "unresolved"
