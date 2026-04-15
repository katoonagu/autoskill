from automation.modules.company_contacts_enrichment.text_utils import repair_loaded_data


def test_repair_loaded_data_preserves_nested_values() -> None:
    payload = {
        "name": "Тест",
        "items": [{"title": "Привет"}],
    }

    assert repair_loaded_data(payload) == payload
