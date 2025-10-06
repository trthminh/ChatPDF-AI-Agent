import os
import sys
from typing import List

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_core.documents import Document
import sqlite3
from src.config import *
from src.utils import get_current_hcm_time_iso

def load_documents_from_directory(directory_path: str) -> List[Document]:
    all_docs = []
    for filename in os.listdir(directory_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(directory_path, filename)
            try:
                loader = PyPDFLoader(file_path)
                docs_for_file = loader.load()
                for doc in docs_for_file:
                    filename = filename.replace(" ", "_") # for sql
                    doc.metadata["source"] = filename
                all_docs.extend(docs_for_file)
            except Exception as e:
                print(f"Error when read file {filename}: {e}")
    return all_docs

def split_documents(documents: List[Document]) -> List[Document]:
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split successfull {len(chunks)} chunks.")
    return chunks

def create_and_save_vector_store(chunks: List[Document], save_path: str):    
    embeddings = GoogleGenerativeAIEmbeddings(
        model=EMBEDDING_MODEL_NAME,
        google_api_key=GOOGLE_API_KEY
    )
    
    vector_store = FAISS.from_documents(chunks, embeddings)
    
    vector_store.save_local(save_path)

def create_metadata_database():
    conn = sqlite3.connect(SQL_DATABASE_PATH)
    cursor = conn.cursor()

    # Bảng User
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS User (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        created_at TEXT NOT NULL
    )
    ''')

    # Bảng Workspace
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Workspace (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    ''')
    
    # Bảng Space
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Space (
        id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (workspace_id) REFERENCES Workspace (id)
    )
    ''')

    # Bảng PDF_Document
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS PDF_Document (
        id TEXT PRIMARY KEY,
        filename TEXT NOT NULL,
        content_hash TEXT, -- Để kiểm tra sự trùng lặp nếu muốn
        space_id TEXT NOT NULL,
        owner_id TEXT NOT NULL,
        size_bytes INTEGER,
        uploaded_at TEXT NOT NULL,
        FOREIGN KEY (space_id) REFERENCES Space (id),
        FOREIGN KEY (owner_id) REFERENCES User (id)
    )
    ''')
    
    # Bảng liên kết User và Workspace (quan hệ nhiều-nhiều)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS User_Workspace_Membership (
        user_id TEXT NOT NULL,
        workspace_id TEXT NOT NULL,
        PRIMARY KEY (user_id, workspace_id),
        FOREIGN KEY (user_id) REFERENCES User (id),
        FOREIGN KEY (workspace_id) REFERENCES Workspace (id)
    )
    ''')

    # Bảng liên kết User và Space (Nhiều-nhiều)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS User_Space_Membership (
        user_id TEXT NOT NULL,
        space_id TEXT NOT NULL,
        PRIMARY KEY (user_id, space_id),
        FOREIGN KEY (user_id) REFERENCES User (id),
        FOREIGN KEY (space_id) REFERENCES Space (id)
    )
    ''')

    conn.commit()
    conn.close()

def insert_sample_data():
    conn = sqlite3.connect(SQL_DATABASE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM User")
    if cursor.fetchone()[0] > 0:
        print("Dữ liệu mẫu đã tồn tại. Bỏ qua.")
        conn.close()
        return

    print("Đang chèn dữ liệu mẫu...")
    now = get_current_hcm_time_iso()

    # Users
    users = [
        ('alice_01', 'Alice', 'alice@example.com', now),
        ('bob_02', 'Bob', 'bob@example.com', now)
    ]
    cursor.executemany("INSERT INTO User VALUES (?, ?, ?, ?)", users)

    # Workspaces
    workspaces = [
        ('ws_marketing', 'Marketing', now, now),
        ('ws_accounting', 'Accounting', now, now)
    ]
    cursor.executemany("INSERT INTO Workspace VALUES (?, ?, ?, ?)", workspaces)
    
    # Spaces
    spaces = [
        ('sp_ads', 'Advertisements', 'ws_marketing', now, now),
        ('sp_invoices', 'Invoices', 'ws_accounting', now, now),
        ('sp_reports', 'Financial Reports', 'ws_accounting', now, now)
    ]
    cursor.executemany("INSERT INTO Space VALUES (?, ?, ?, ?, ?)", spaces)
    
    # PDF Documents
    docs = [
        ('doc_ad_1', 'invoice-0-4.pdf', None, 'sp_ads', 'alice_01', 1024, now),
        ('doc_inv_1', 'invoice_Jasper_Cacioppo_18509.pdf', None, 'sp_invoices', 'bob_02', 2048, now)
    ]
    cursor.executemany("INSERT INTO PDF_Document VALUES (?, ?, ?, ?, ?, ?, ?)", docs)

    # Memberships
    memberships = [
        ('alice_01', 'ws_marketing'),
        ('bob_02', 'ws_accounting'),
        ('alice_01', 'ws_accounting') # Alice có quyền truy cập cả 2 workspace
    ]
    cursor.executemany("INSERT INTO User_Workspace_Membership VALUES (?, ?)", memberships)

    sp_memberships = [
        ('alice_01', 'sp_ads'),
        ('alice_01', 'sp_reports'),
        ('bob_02', 'sp_invoices')
    ]
    cursor.executemany("INSERT INTO User_Space_Membership VALUES (?, ?)", sp_memberships)
    conn.commit()
    conn.close()
    print("Chèn dữ liệu mẫu thành công.")

def main():
    """Hàm chính để thực thi toàn bộ luồng ingestion."""
    print("--- Bắt đầu quá trình nạp dữ liệu ---")
    
    # Load documents
    documents = load_documents_from_directory(RAW_DATA_PATH)
    if not documents:
        print("Không tìm thấy file PDF nào. Kết thúc.")
        return

    # Split documents into chunks
    chunks = split_documents(documents)
    
    # Create and save vector store
    create_and_save_vector_store(chunks, VECTOR_STORE_PATH)
    create_metadata_database()
    insert_sample_data()
    print("--- Hoàn tất quá trình nạp dữ liệu ---")

if __name__ == "__main__":
    main()