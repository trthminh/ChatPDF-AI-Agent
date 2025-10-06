import sys
import os
import sqlite3

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
import uuid
from src.utils import get_current_hcm_time_iso

from src.config import *
def process_and_ingest_single_pdf(file_path: str, space_id: str, owner_id: str):
    filename = os.path.basename(file_path)
    filename = filename.replace(" ", "_") # for sql
    file_size = os.path.getsize(file_path)
    now = get_current_hcm_time_iso()
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    print(f"Updating SQL database for file: {filename}")
    try:
        conn = sqlite3.connect(SQL_DATABASE_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO PDF_Document (id, filename, space_id, owner_id, size_bytes, uploaded_at) VALUES (?, ?, ?, ?, ?, ?)",
            (doc_id, filename, space_id, owner_id, file_size, now)
        )
        conn.commit()
        conn.close()
        print("SQL database updated successfully.")
    except Exception as e:
        print(f"Error updating SQL database: {e}")
        return False, "Failed to update metadata database."

    print(f"Ingesting file into Vector Store: {filename}")
    try:
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        for doc in docs:
            doc.metadata["source"] = filename

            doc.metadata["doc_id"] = doc_id

        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_documents(docs)
        for chunk in chunks:
            source_file = chunk.metadata.get("source", "unknown_source")
            chunk.page_content = f"File name: {source_file}. Nội dung: {chunk.page_content}"

        embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL_NAME, google_api_key=GOOGLE_API_KEY)
        vector_store = FAISS.load_local(VECTOR_STORE_PATH, embeddings, allow_dangerous_deserialization=True)

        vector_store.add_documents(chunks)

        vector_store.save_local(VECTOR_STORE_PATH)
        print("Vector Store updated and saved successfully.")
        return True, f"File '{filename}' uploaded and processed successfully!"
    except Exception as e:
        print(f"Error ingesting file into Vector Store: {e}")
        return False, "Failed to process and ingest the document content."