"""
app/clients/chroma_client.py

ChromaDB client singleton.

Architecture decision: ChromaDB runs embedded (in-process) with a persistent
directory. Zero infrastructure required — data survives container restarts via
a mounted volume. Switching to Pinecone is a config change in this file only.

Day 2 status: The client and collection are initialised here. The VectorRetrievalTool
uses this client. The collection will be empty until the document ingestion pipeline
runs (scripts/ingest_documents.py — implemented on Day 4). When empty, the tool
returns ToolStatus.EMPTY, which the synthesizer handles gracefully via data_gaps.

The VectorRetrievalTool is fully functional today — it returns zero chunks with
EMPTY status if no documents are ingested yet. The orchestration engine handles
this identically to a tool with partial results.

Collection name: "financial_docs"
Embedding function: sentence-transformers/all-MiniLM-L6-v2 (384 dimensions)
  - Runs locally, zero API cost
  - ~90MB model download on first use
  - Inference is fast (<50ms per query on CPU)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger(__name__)

# Persistent storage directory
CHROMA_PERSIST_DIR = os.environ.get(
    "CHROMA_PERSIST_DIR",
    str(Path(__file__).parent.parent.parent.parent / "chroma_data"),
)

COLLECTION_NAME = "financial_docs"

# Embedding model for both ingestion and retrieval
# Must be consistent — changing this requires re-ingesting all documents
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# Relevance threshold — chunks below this score are excluded from results
RELEVANCE_THRESHOLD = 0.65


class ChromaClient:
    """
    Manages the ChromaDB client and financial_docs collection.

    Initialised lazily on first use to keep startup time fast.
    Thread-safe for the asyncio.gather parallel dispatch pattern since
    ChromaDB's Python client is synchronous and we run queries in
    a thread pool executor.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._collection: Any = None
        self._embedding_fn: Any = None
        self._initialised = False

    def _ensure_initialised(self) -> None:
        """Lazy initialisation of the ChromaDB client and collection."""
        if self._initialised:
            return

        try:
            import chromadb  # type: ignore[import]
            from chromadb.utils import embedding_functions  # type: ignore[import]

            Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

            self._embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=EMBEDDING_MODEL
            )

            # get_or_create_collection: idempotent — safe to call on restart
            self._collection = self._client.get_or_create_collection(
                name=COLLECTION_NAME,
                embedding_function=self._embedding_fn,
                metadata={
                    "hnsw:space": "cosine",
                    "embedding_model": EMBEDDING_MODEL,
                },
            )

            doc_count = self._collection.count()
            log.info(
                "chroma_client.initialised",
                persist_dir=CHROMA_PERSIST_DIR,
                collection=COLLECTION_NAME,
                document_count=doc_count,
                embedding_model=EMBEDDING_MODEL,
            )

            self._initialised = True

        except ImportError as exc:
            log.error(
                "chroma_client.import_failed",
                error=str(exc),
                hint="Install chromadb and sentence-transformers: pip install chromadb sentence-transformers",
            )
            raise
        except Exception as exc:
            log.error("chroma_client.init_failed", error=str(exc), exc_info=True)
            raise

    def query(
        self,
        query_text: str,
        n_results: int,
        tickers: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Perform a semantic similarity search.

        Parameters
        ----------
        query_text  : Natural language query for embedding
        n_results   : Maximum number of results to return
        tickers     : If provided, filter results to these ticker symbols
                      (stored in chunk metadata as "ticker" field)

        Returns
        -------
        ChromaDB query result dict with keys:
          documents, metadatas, distances, ids

        Raises
        ------
        Exception if ChromaDB is unavailable or collection is corrupt.
        Returns empty structure if collection has no documents.
        """
        self._ensure_initialised()

        if self._collection.count() == 0:
            log.info("chroma_client.collection_empty", hint="Run scripts/ingest_documents.py")
            return {
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
                "ids": [[]],
            }

        where_filter: dict[str, Any] | None = None
        if tickers:
            if len(tickers) == 1:
                where_filter = {"ticker": tickers[0]}
            else:
                where_filter = {"ticker": {"$in": tickers}}

        query_kwargs: dict[str, Any] = {
            "query_texts": [query_text],
            "n_results": min(n_results, self._collection.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where_filter:
            query_kwargs["where"] = where_filter

        return self._collection.query(**query_kwargs)  # type: ignore[no-any-return]

    def count(self) -> int:
        """Return the number of documents in the collection."""
        self._ensure_initialised()
        return self._collection.count()  # type: ignore[no-any-return]

    def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """
        Add documents to the collection (used by the ingestion pipeline).

        Called from scripts/ingest_documents.py on Day 4.
        Idempotent via ChromaDB's upsert semantics if IDs already exist.
        """
        self._ensure_initialised()
        self._collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        log.info(
            "chroma_client.documents_added",
            count=len(ids),
            total=self._collection.count(),
        )

    def health(self) -> dict[str, Any]:
        """Return health status for the /health endpoint."""
        try:
            self._ensure_initialised()
            count = self._collection.count()
            return {
                "status": "ok",
                "document_count": count,
                "embedding_model": EMBEDDING_MODEL,
                "persist_dir": CHROMA_PERSIST_DIR,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
            }


# ── Singleton ──────────────────────────────────────────────────────────────────

_chroma_client: ChromaClient | None = None


def get_chroma_client() -> ChromaClient:
    """Returns the module-level ChromaClient singleton."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = ChromaClient()
    return _chroma_client