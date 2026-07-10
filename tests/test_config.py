from src.core.config import Settings


def test_default_embedding_model_uses_openai() -> None:
    settings = Settings()

    assert settings.embedding_model == "text-embedding-3-small"


def test_default_embedding_device_is_cpu_for_openai() -> None:
    settings = Settings()

    assert settings.embedding_device == "cpu"
