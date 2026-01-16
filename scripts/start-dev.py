import argparse
import subprocess
from dataclasses import dataclass

import uvicorn
from uvicorn import config

logging_config = config.LOGGING_CONFIG

@dataclass
class ArgsModel:
    port: int
    reload: bool


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--port', type=int, default=8000)
    parser.add_argument('-r', '--reload', action=argparse.BooleanOptionalAction, default=True)
    
    args = ArgsModel(**vars(parser.parse_args()))
    
    uvicorn.run(
        'app.app:fastapi_app',
        host='0.0.0.0',
        port=args.port,
        reload=args.reload,
        reload_dirs=['./app'],
    )

## prisma

# def db_push():
#     subprocess.run(["prisma","db","push"])

# def migration_create():
#     subprocess.run("poetry", "migrate", "dev", "--create-only")

# def migrate():
#     subprocess.run(["prisma", "migrate", "dev"])


def db_upgrade_head():
    subprocess.run(["poetry", "run", "alembic", "upgrade", "head"])

def db_downgrade_base():
    subprocess.run(["poetry", "run", "alembic", "downgrade", "base"])

def run_nginx():
    """
    Docstring for run_nginx
    Make sure you have podman installed.
    """
    subprocess.run(["podman", "run", "-d", "--name", "my-nginx", "-p", "80:80", "-v", "$(pwd)/nginx/nginx.conf:/etc/nginx/nginx.conf:ro", "-v", "$(pwd)/nginx/conf.d:/etc/nginx/conf.d:ro", "nginx:stable"])

def test():
    subprocess.run(["pytest", "-vv", "-s", "tests"])

if __name__ == '__main__':
    main()
