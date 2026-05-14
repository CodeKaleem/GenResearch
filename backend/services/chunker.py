# ============================================================
# GenResearch — Text Chunker
# LangChain RecursiveCharacterTextSplitter
# ============================================================
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config import settings


def chunk_text(text: str) -> list[str]:
    """
    Split extracted text into overlapping chunks using
    RecursiveCharacterTextSplitter.
    """
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "],
        length_function=len,
    )
    return splitter.split_text(text)
