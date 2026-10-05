"""Provisionamento explícito e conservador; nunca remove ou altera tabelas."""
from datetime import date
from sqlalchemy import Integer, func, inspect, select, text
from sqlalchemy.orm import Session
from ..models import Base, DocumentosSolicitados, Inscricoes, ProcessosBolsa, Usuarios
from ..security import hash_senha


def tipos_equivalentes(expected, actual):
    # PostgreSQL reflete DECIMAL como NUMERIC e FLOAT como DOUBLE PRECISION.
    if hasattr(expected, 'enums'):
        return expected.enums == getattr(actual, 'enums', None) and expected.name == getattr(actual, 'name', None)
    if expected._type_affinity is not actual._type_affinity:
        return False
    for attr in ('length', 'precision', 'scale', 'timezone'):
        want, found = getattr(expected, attr, None), getattr(actual, attr, None)
        if attr == 'precision' and expected._type_affinity.__name__ == 'Float' and want is None:
            want = 53 if found == 53 else None
        if want != found:
            return False
    return not hasattr(expected, 'enums') or expected.enums == getattr(actual, 'enums', None)


def _normalizar_default(value):
    # Defaults destes modelos são literais simples e CURRENT_TIMESTAMP.
    # PostgreSQL inclui casts para varchar/enum na reflexão dos literais.
    expr = str(value if value is not None else '').split('::')[0].strip()
    while expr.startswith('(') and expr.endswith(')'):
        expr = expr[1:-1].strip()
    if expr.lower() in {'now()', 'transaction_timestamp()'}:
        return 'CURRENT_TIMESTAMP'
    return expr


def divergencias_esquema(engine):
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    issues = []
    for table in Base.metadata.sorted_tables:
        if table.name not in tables:
            issues.append(f"{table.name}: tabela ausente")
            continue
        actual = {c['name']: c for c in inspector.get_columns(table.name)}
        expected = {c.name: c for c in table.columns}
        if set(actual) != set(expected):
            issues.append(f"{table.name}: colunas divergentes")
            continue
        for name, column in expected.items():
            found = actual[name]
            if not tipos_equivalentes(column.type, found['type']) or column.nullable != found['nullable']:
                issues.append(f"{table.name}.{name}: tipo ou nulabilidade divergente")
            if column.server_default is not None and _normalizar_default(column.server_default.arg) != _normalizar_default(found.get('default')):
                issues.append(f"{table.name}.{name}: default necessário divergente")
            if engine.dialect.name == 'postgresql' and column.primary_key and isinstance(column.type, Integer) and column.autoincrement is not False:
                generated = found.get('identity') or str(found.get('default') or '').lower().startswith('nextval(')
                if not generated:
                    issues.append(f"{table.name}.{name}: geração de ID ausente")
        pk = inspector.get_pk_constraint(table.name)['constrained_columns']
        if set(pk) != {c.name for c in table.primary_key.columns}:
            issues.append(f"{table.name}: chave primária divergente")
        fks = {(tuple(f['constrained_columns']), f['referred_table'], tuple(f['referred_columns']))
               for f in inspector.get_foreign_keys(table.name)}
        expected_fks = {(tuple(e.parent.name for e in f.elements), f.referred_table.name,
                         tuple(e.column.name for e in f.elements)) for f in table.foreign_key_constraints}
        if fks != expected_fks:
            issues.append(f"{table.name}: vínculos divergentes")
        uniques = {tuple(u['column_names']) for u in inspector.get_unique_constraints(table.name)}
        if any((c.name,) not in uniques for c in table.columns if c.unique):
            issues.append(f"{table.name}: unicidade divergente")
    return issues


def criar_esquema(engine):
    existing = set(inspect(engine).get_table_names())
    divergences = [i for i in divergencias_esquema(engine) if i.split(':')[0].split('.')[0] in existing]
    if divergences:
        raise ValueError("Esquema requer migração explícita: " + "; ".join(divergences))
    Base.metadata.create_all(engine)


def preparar_processo_teste(session):
    # Serializa as duas operações de provisionamento; não afeta requisições normais.
    _lock(session)
    name = "Homologação TCC 2026"
    process = session.scalar(select(ProcessosBolsa).where(ProcessosBolsa.nome == name))
    if process is None:
        process = ProcessosBolsa(nome=name, data_inicio=date(2026, 1, 1), data_fim=date(2026, 12, 31))
        session.add(process)
        session.flush()
    requested = {d.nome_documento for d in session.scalars(
        select(DocumentosSolicitados).where(DocumentosSolicitados.processo_id == process.id))}
    for category in ['CNH', 'RG', 'RG_VERSO', 'RESIDENCIA', 'HOLERITE']:
        if category not in requested:
            session.add(DocumentosSolicitados(processo_id=process.id, nome_documento=category,
                                             obrigatorio=int(category == 'CNH')))
    session.flush()
    return process


def criar_usuario(session, email, senha, perfil):
    if len(senha) < 12 or not any(c.isalpha() for c in senha) or not any(c.isdigit() for c in senha):
        raise ValueError("Senha deve ter 12 caracteres ou mais, letras e números")
    if perfil not in {'ADMIN', 'ANALISTA', 'CANDIDATO'}:
        raise ValueError("Perfil inválido")
    email = email.strip().lower()
    if '@' not in email or len(email) > 255:
        raise ValueError("E-mail inválido")
    _lock(session)
    if session.scalar(select(Usuarios).where(func.lower(Usuarios.email) == email)):
        raise ValueError("Usuário existente; senha e perfil preservados")
    nome = "Candidato (Homologação)" if perfil == 'CANDIDATO' else "Conta de homologação"
    user = Usuarios(email=email, nome_completo=nome, perfil=perfil, senha_hash=hash_senha(senha))
    session.add(user)
    session.flush()
    return user


def _lock(session: Session):
    if session.bind.dialect.name == 'postgresql':
        session.execute(text('SELECT pg_advisory_xact_lock(20261005)'))
