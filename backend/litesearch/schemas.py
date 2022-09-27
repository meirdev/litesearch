from typing import Any

from pydantic import BaseModel, validator

IndexFields = dict[str, int]


class IndexBase(BaseModel):
    pass


class IndexInDB(IndexBase):
    id: str
    fields: IndexFields

    class Config:
        orm_mode = True


DocumentPrimitiveValue = None | bool | int | float | str

DocumentContainerValue = list[DocumentPrimitiveValue]

# TODO: 'Any' need to be 'DocumentSource'
DocumentSource = dict[str, DocumentPrimitiveValue | DocumentContainerValue | Any]

DocumentFields = dict[str, list[DocumentPrimitiveValue]]


class DocumentBase(BaseModel):
    pass


class DocumentCreateOrUpdate(DocumentBase):
    source: DocumentSource

    @validator("source")
    def check_value(cls, value):
        def _check_nested(nested_value):
            if isinstance(nested_value, dict):
                assert all(
                    isinstance(k, str) for k in nested_value
                ), f"dict: {nested_value}"
                _check_nested(list(nested_value.values()))

            elif isinstance(nested_value, list):
                assert all(
                    _check_nested(v) for v in nested_value
                ), f"list: {nested_value}"

            else:
                assert isinstance(
                    nested_value, DocumentPrimitiveValue
                ), f"value: {nested_value}"

            return True

        _check_nested(value)

        return value


class DocumentInDBBase(DocumentBase):
    id: str
    index_id: str
    fields: DocumentFields

    class Config:
        orm_mode = True


class DocumentInDBWithoutSource(DocumentInDBBase):
    pass


class DocumentInDB(DocumentInDBBase):
    source: DocumentSource


class DocumentLimitOffset(BaseModel):
    total: int
    offset: int
    limit: int
    documents: list[DocumentInDBWithoutSource]


class Token(BaseModel):
    access_token: str
