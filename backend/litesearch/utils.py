import uuid
from collections import defaultdict
from typing import Any

from .schemas import DocumentFields, DocumentSource


def flatten_json(data: DocumentSource, separator: str = ".") -> DocumentFields:
    out = defaultdict(list)

    def _flatten(item: Any, path: list[str]):
        if isinstance(item, dict):
            for k, v in item.items():
                _flatten(v, path + [k])
        elif isinstance(item, list):
            for i in item:
                _flatten(i, path)
        else:
            out[separator.join(path)].append(item)

    _flatten(data, [])

    return out


def random_id() -> str:
    return str(uuid.uuid4()).replace("-", "")
