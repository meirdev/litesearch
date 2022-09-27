from collections import defaultdict
from copy import deepcopy
from typing import NewType

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer, joinedload

from .models import Document, Index
from .query_parser import query_to_sql
from .schemas import DocumentFields, DocumentSource, IndexFields
from .utils import flatten_json

Total = NewType("Total", int)


class ObjectExistsError(Exception):
    pass


class ObjectNotFoundError(Exception):
    pass


def index_merge_fields(current: IndexFields, update: IndexFields) -> IndexFields:
    fields = deepcopy(current)
    for field in update:
        fields[field] = current.get(field, 0) + update[field]
    return {field: ref for field, ref in fields.items() if ref > 0}


async def index_update_fields(
    db: AsyncSession, index: Index, fields: IndexFields
) -> None:
    fields = index_merge_fields(index.fields, fields)

    if fields != index.fields:
        await db.execute(
            update(Index).where(Index.id == index.id).values(fields=fields)
        )


async def index_get(db: AsyncSession, index_id: str) -> Index:
    index = await db.get(Index, index_id)
    if index is None:
        raise ObjectNotFoundError

    return index


async def index_get_all(
    db: AsyncSession, query_index_id: str | None = None
) -> list[Index]:
    query = select(Index)

    if query_index_id:
        query = query.where(Index.id.like(f"%{query_index_id}%"))

    result = await db.execute(query)
    return result.scalars().all()


async def index_create(db: AsyncSession, index_id: str) -> None:
    index = await db.get(Index, index_id)
    if index is not None:
        raise ObjectExistsError

    index = Index(id=index_id)
    db.add(index)
    await db.commit()


async def index_delete(db: AsyncSession, index_id: str) -> None:
    index = await db.get(Index, index_id)
    if index is None:
        raise ObjectNotFoundError

    await db.delete(index)
    await db.commit()


def document_merge_fields(old: DocumentFields, new: DocumentFields) -> IndexFields:
    fields: IndexFields = defaultdict(lambda: 0)
    for field in old:
        fields[field] -= 1
    for field in new:
        fields[field] += 1
    return fields


async def document_get_all(db: AsyncSession, index_id: str) -> list[Document]:
    query = (
        select(Document)
        .options(defer(Document.source))
        .where(Document.index_id == index_id)
    )
    result = await db.execute(query)
    return result.scalars().all()


async def document_query(
    db: AsyncSession,
    index_id: str,
    query: str = "",
    offset: int = 0,
    limit: int = 100,
) -> tuple[Total, list[Document]]:
    query_ = (
        select(Document)
        .options(defer(Document.source))
        .where((Document.index_id == index_id))
        .group_by(Document.id, Document.index_id)
    )

    if query:
        query_ = query_.where(query_to_sql(query))

    total = await db.scalar(select(func.count()).select_from(query_.subquery()))

    query_ = query_.offset(offset).limit(limit)

    result = await db.execute(query_)
    return total, result.scalars().all()


async def document_get(db: AsyncSession, index_id: str, document_id: str) -> Document:
    document = await db.get(
        Document,
        {"id": document_id, "index_id": index_id},
        [joinedload(Document.index)],
    )
    if document is None:
        raise ObjectNotFoundError

    return document


async def document_delete(db: AsyncSession, index_id: str, document_id: str) -> None:
    document = await document_get(db, index_id, document_id)

    await db.delete(document)
    await index_update_fields(
        db, document.index, document_merge_fields(document.fields, {})
    )
    await db.commit()


async def document_upsert(
    db: AsyncSession,
    index_id: str,
    document_id: str,
    source: DocumentSource,
    force_create: bool = False,
) -> tuple[bool, Document]:
    created = False

    new_fields = flatten_json(source)

    try:
        document = await document_get(db, index_id, document_id)

        if force_create:
            raise ObjectExistsError

    except ObjectNotFoundError:
        document = Document(id=document_id, fields={})

        created = True

    old_fields = document.fields

    try:
        index = document.index or await index_get(db, index_id)
    except ObjectNotFoundError:
        index = Index(id=index_id, fields={})

    document.index = index
    document.source = source
    document.fields = new_fields

    db.add(document)
    await index_update_fields(db, index, document_merge_fields(old_fields, new_fields))
    await db.commit()

    return created, document
