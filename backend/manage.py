import argparse
import asyncio

import uvicorn

from litesearch.commands import db_create_all
from litesearch.settings import settings


def main() -> None:
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("command", choices=["db_create_all", "run_server"])

    args = arg_parser.parse_args()

    match args.command:
        case "db_create_all":
            asyncio.run(db_create_all())
        case "run_server":
            uvicorn.run(
                "litesearch.main:app",
                host=settings.SERVER_HOST,
                port=settings.SERVER_PORT,
                reload=settings.DEBUG,
            )


if __name__ == "__main__":
    main()
