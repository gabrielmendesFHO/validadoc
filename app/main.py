from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session
from .routes import documentos, inscricoes


from .config import settings
from .db import (
    compare_models_to_db,
    get_db,
    get_reflected_class,
    get_table_names,
    serialize,
)

app = FastAPI(title=settings.app_name)
app.include_router(documentos.router)
app.include_router(inscricoes.router)


@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.app_name}"}


@app.get("/tables")
def list_tables():
    return {"tables": get_table_names()}


@app.get("/tables/{table_name}/sample")
def table_sample(table_name: str, db: Session = Depends(get_db)):
    model = get_reflected_class(table_name)
    if model is None:
        raise HTTPException(status_code=404, detail="Table not found")

    sample = db.query(model).limit(10).all()
    return {"table": table_name, "rows": [serialize(row) for row in sample]}


@app.get("/schema/verify")
def verify_schema():
    return compare_models_to_db()
