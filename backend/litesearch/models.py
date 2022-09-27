from sqlalchemy import JSON, Column, ForeignKey, String
from sqlalchemy.orm import relationship

from .database import Base
from .schemas import DocumentFields, DocumentSource, IndexFields


class Index(Base):
    __tablename__ = "indexes"

    id = Column(String, primary_key=True)
    fields: IndexFields = Column(JSON, default={})

    documents: list["Document"] = relationship(
        "Document", back_populates="index", cascade="all, delete"
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    index_id = Column(String, ForeignKey("indexes.id"), primary_key=True)
    source: DocumentSource = Column(JSON)
    fields: DocumentFields = Column(JSON, index=True)

    index: Index = relationship(Index, back_populates="documents")
