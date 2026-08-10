from sqlalchemy import MetaData, create_engine, inspect
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import sessionmaker

from .config import settings
from .models import (
    AnalisesOcr,
    DocumentosEnviados,
    DocumentosSolicitados,
    Inscricoes,
    Instituicoes,
    MembrosFamilia,
    ProcessosBolsa,
    Usuarios,
)

engine = create_engine(
    settings.database_url,
    future=True,
    pool_pre_ping=True,
)

reflection_metadata = MetaData()
Base = automap_base(metadata=reflection_metadata)
automap_initialized = False


def _classname_for_table(base, tablename, table):
    return tablename


def init_automap():
    global automap_initialized
    if automap_initialized:
        return

    reflection_metadata.clear()
    try:
        Base.prepare(
            engine,
            reflect=True,
            classname_for_table=_classname_for_table,
        )
    except InvalidRequestError as exc:
        if "already defined" not in str(exc):
            raise
    automap_initialized = True

SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
init_automap()

MODEL_CLASSES = {
    cls.__tablename__: cls
    for cls in (
        Instituicoes,
        ProcessosBolsa,
        Usuarios,
        DocumentosSolicitados,
        Inscricoes,
        MembrosFamilia,
        DocumentosEnviados,
        AnalisesOcr,
    )
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_table_names():
    return inspect(engine).get_table_names()


def get_reflected_class(table_name: str):
    return getattr(Base.classes, table_name, None)


def serialize(instance):
    return {column.name: getattr(instance, column.name) for column in instance.__table__.columns}


def compare_models_to_db():
    inspector = inspect(engine)
    db_tables = set(inspector.get_table_names())
    model_tables = set(MODEL_CLASSES)

    result = {
        "model_tables": sorted(model_tables),
        "db_tables": sorted(db_tables),
        "missing_tables": sorted(model_tables - db_tables),
        "extra_tables": sorted(db_tables - model_tables),
        "table_diffs": {},
    }

    for table_name in sorted(model_tables & db_tables):
        model_cls = MODEL_CLASSES[table_name]
        db_columns = {col["name"]: col for col in inspector.get_columns(table_name)}
        model_columns = {column.name: column for column in model_cls.__table__.columns}

        column_diff = {}
        missing_cols = sorted(set(model_columns) - set(db_columns))
        extra_cols = sorted(set(db_columns) - set(model_columns))
        if missing_cols:
            column_diff["missing_columns"] = missing_cols
        if extra_cols:
            column_diff["extra_columns"] = extra_cols

        field_mismatches = []
        for column_name in sorted(set(model_columns) & set(db_columns)):
            model_column = model_columns[column_name]
            db_column = db_columns[column_name]
            model_type = str(model_column.type).lower()
            db_type = str(db_column["type"]).lower()
            if model_type != db_type:
                field_mismatches.append(
                    {
                        "column": column_name,
                        "model_type": model_type,
                        "db_type": db_type,
                    }
                )
            if model_column.nullable != db_column["nullable"]:
                field_mismatches.append(
                    {
                        "column": column_name,
                        "model_nullable": model_column.nullable,
                        "db_nullable": db_column["nullable"],
                    }
                )

        if field_mismatches:
            column_diff["field_mismatches"] = field_mismatches

        if column_diff:
            result["table_diffs"][table_name] = column_diff

    return result
