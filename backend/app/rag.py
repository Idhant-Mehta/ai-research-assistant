import os
from dotenv import load_dotenv
from typing import List, Optional
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma

# Load .env from the backend directory
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")

class RAGManager:
    def __init__(self):
        self._embeddings = None
        self._vector_store = None
        self._retriever = None

    def _init_stores(self):
        """Lazy initialization — only connect when actually needed."""
        if self._embeddings is None:
            gemini_key = os.getenv("GEMINI_API_KEY", "")
            if not gemini_key:
                raise ValueError(
                    "GEMINI_API_KEY is not set. "
                    "Create a .env file in the backend/ directory with: GEMINI_API_KEY=your-key"
                )
            self._embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=gemini_key
            )
            self._vector_store = Chroma(
                persist_directory=CHROMA_PERSIST_DIR,
                embedding_function=self._embeddings
            )
            self._retriever = self._vector_store.as_retriever(
                search_type="similarity",
                search_kwargs={"k": 4}
            )

    def ingest_pdf(self, file_path: str, filename: str) -> int:
        self._init_stores()
        loader = PyPDFLoader(file_path)
        docs = loader.load()

        for doc in docs:
            doc.metadata["source"] = filename

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200
        )
        splits = text_splitter.split_documents(docs)
        self._vector_store.add_documents(splits)
        return len(splits)

    def query(self, query_text: str) -> List[dict]:
        self._init_stores()
        results = self._vector_store.similarity_search_with_score(query_text, k=4)
        formatted = []
        for doc, score in results:
            formatted.append({
                "page_content": doc.page_content,
                "metadata": doc.metadata,
                "score": float(score)
            })
        return formatted

rag_manager = RAGManager()

