from sqlalchemy.engine import URL, make_url


def normalize_database_url(raw_url: str) -> URL:
    try:
        url = make_url(raw_url)
        if url.drivername in {"postgres", "postgresql"}:
            url = url.set(drivername="postgresql+psycopg")
        return url
    except Exception:
        raise ValueError("DATABASE_URL inválida; confira a configuração privada") from None
