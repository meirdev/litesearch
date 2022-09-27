from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from . import crud, schemas
from .auth import authenticate_user, create_access_token, validate_access_token
from .database import get_db
from .schemas import DocumentLimitOffset
from .utils import random_id

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def check_token(token: str = Depends(oauth2_scheme)):
    if not validate_access_token(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


router_index = APIRouter(dependencies=[Depends(check_token)])
router_token = APIRouter()


@router_index.get("", response_model=list[schemas.IndexInDB])
async def get_indexes(
    query_index_id: str | None = None, db: AsyncSession = Depends(get_db)
):
    return await crud.index_get_all(db, query_index_id)


@router_index.post("/{index_id}", status_code=status.HTTP_201_CREATED)
async def create_index(index_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await crud.index_create(db, index_id)
    except crud.ObjectExistsError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"index {index_id} already exists"
        )


@router_index.delete("/{index_id}")
async def delete_index(index_id: str, db: AsyncSession = Depends(get_db)):
    try:
        await crud.index_delete(db, index_id)
    except crud.ObjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"no such index {index_id}")


@router_index.post(
    "/{index_id}/documents",
    response_model=schemas.DocumentInDB,
    response_model_include={"id"},
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    index_id: str,
    body: schemas.DocumentCreateOrUpdate,
    db: AsyncSession = Depends(get_db),
):
    document_id = random_id()

    try:
        _, document = await crud.document_upsert(
            db, index_id, document_id, body.source, force_create=True
        )
    except crud.ObjectExistsError:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"document {index_id}/{document_id} already exists",
        )

    return document


@router_index.post(
    "/{index_id}/documents/{document_id}",
    response_model=schemas.DocumentInDB,
    response_model_include={"id"},
)
async def update_or_create_document(
    index_id: str,
    document_id: str,
    body: schemas.DocumentCreateOrUpdate,
    db: AsyncSession = Depends(get_db),
):
    created, document = await crud.document_upsert(
        db, index_id, document_id, body.source
    )

    status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK

    return JSONResponse(
        status_code=status_code, content=jsonable_encoder(document, include={"id"})
    )


@router_index.get("/{index_id}/documents", response_model=DocumentLimitOffset)
async def get_documents(
    index_id: str,
    query: str = "",
    offset: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    try:
        total, documents = await crud.document_query(db, index_id, query, offset, limit)
    except Exception as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, f"Query [{type(error)}]: {error}"
        )

    return DocumentLimitOffset(
        total=total, limit=limit, offset=offset, documents=documents
    )


@router_index.get(
    "/{index_id}/documents/{document_id}", response_model=schemas.DocumentInDB
)
async def get_document(
    index_id: str, document_id: str, db: AsyncSession = Depends(get_db)
):
    try:
        document = await crud.document_get(db, index_id, document_id)
    except crud.ObjectNotFoundError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no such document {index_id}/{document_id}"
        )

    return document


@router_index.delete("/{index_id}/documents/{document_id}")
async def delete_document(
    index_id: str, document_id: str, db: AsyncSession = Depends(get_db)
):
    try:
        await crud.document_delete(db, index_id, document_id)
    except crud.ObjectNotFoundError:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, f"no such document {index_id}/{document_id}"
        )


@router_token.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": user})
    return {"access_token": access_token, "token_type": "bearer"}
