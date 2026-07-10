def test_app_imports() -> None:
    from src.main import app

    assert app is not None
