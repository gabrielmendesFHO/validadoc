"""CLI de homologação. Carrega o arquivo privado antes de importar a aplicação."""
import argparse
import getpass
import sys
from pathlib import Path
from dotenv import load_dotenv


def main(argv=None):
    parser = argparse.ArgumentParser(description='Provisionamento da homologação ValidaDoc')
    parser.add_argument('--env-file', type=Path)
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('init-db')
    commands.add_parser('check-db')
    user = commands.add_parser('create-user')
    user.add_argument('--email', required=True)
    user.add_argument('--perfil', required=True, choices=['ADMIN', 'ANALISTA', 'CANDIDATO'])
    args = parser.parse_args(argv)
    if args.env_file:
        if not args.env_file.is_file():
            parser.error('Arquivo de configuração não encontrado')
        load_dotenv(args.env_file, override=True)
    try:
        from .config import settings
        from .db import engine
        from .services.provisionamento import criar_esquema, criar_usuario, divergencias_esquema, preparar_processo_teste
        from sqlalchemy import text
        from sqlalchemy.orm import Session
        if settings.app_env != 'homologation' or engine.dialect.name != 'postgresql':
            raise ValueError('Este comando exige APP_ENV=homologation e banco PostgreSQL')
        if args.command == 'check-db':
            with engine.connect() as conn:
                conn.execute(text('SELECT 1'))
            issues = divergencias_esquema(engine)
            if issues:
                raise ValueError('Esquema requer migração: ' + '; '.join(issues))
            print('Banco conectado; esquema compatível.')
        elif args.command == 'init-db':
            criar_esquema(engine)
            with Session(engine) as db:
                preparar_processo_teste(db)
                db.commit()
            print('Esquema e processo de homologação preparados; dados existentes preservados.')
        else:
            senha = getpass.getpass('Senha própria (12+ caracteres, letras e números): ')
            if senha != getpass.getpass('Confirme a senha: '):
                raise ValueError('Senhas não coincidem')
            with Session(engine) as db:
                novo = criar_usuario(db, args.email, senha, args.perfil)
                if args.perfil == 'CANDIDATO':
                    from .models import Inscricoes
                    processo = preparar_processo_teste(db)
                    db.add(Inscricoes(processo_id=processo.id, candidato_id=novo.id))
                db.commit()
            print('Conta criada sem envio de e-mail.')
        return 0
    except ValueError as exc:
        # Somente ValueError sanitizados da aplicação; não imprimir exceções do driver.
        print(str(exc), file=sys.stderr)
        return 1
    except Exception:
        print('Falha na configuração ou conexão. Confira o ambiente privado e a disponibilidade do banco.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
