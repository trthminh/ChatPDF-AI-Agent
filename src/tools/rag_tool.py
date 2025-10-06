import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
import sqlite3
from src.config import *

class RAGTool:
    def __init__(self, vector_store_path=VECTOR_STORE_PATH):
        if not GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY not found in environment variables.")
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model=EMBEDDING_MODEL_NAME,
            google_api_key=GOOGLE_API_KEY
        )
        self.vector_store = self._load_vector_store(vector_store_path)
        self.llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
            convert_system_message_to_human=True
        )
        self.chain = self._build_chain()
        print("Initialize RAG Tool successful!")

    def _load_vector_store(self, path: str):
        try:
            return FAISS.load_local(path, self.embeddings, allow_dangerous_deserialization=True)
        except Exception as e:
            print(f"Error when load vector store: {e}")
            raise

    def _build_chain(self):
        template = """
        Bạn là một trợ lý AI hữu ích, chuyên trả lời các câu hỏi dựa trên nội dung được cung cấp.
        Hãy trả lời câu hỏi của người dùng chỉ dựa vào nội dung dưới đây.
        Nếu thông tin không có trong nội dung, hãy nói rằng bạn không tìm thấy thông tin.

        Nội dung:
        {context}

        Câu hỏi: {question}

        Câu trả lời:
        """

        prompt = PromptTemplate.from_template(template)
        prompt_chain = (
            prompt
            | self.llm
            | StrOutputParser()
        )

        return prompt_chain

    def _get_accessible_doc_sources(self, user_id: str) -> list[str]:
        conn = sqlite3.connect(SQL_DATABASE_PATH)
        cursor = conn.cursor()

        query = """
        SELECT DISTINCT T1.filename
        FROM PDF_Document AS T1
        JOIN User_Space_Membership AS T2 ON T1.space_id = T2.space_id
        WHERE T2.user_id = ?     
        """

        cursor.execute(query, (user_id,))
        results = cursor.fetchall()
        conn.close()

        accessible_sources = [row[0] for row in results]
        print(f"User {user_id} has permission to access into documents: {accessible_sources}")
        return accessible_sources
    
    def _format_docs(self, docs):
        return "\n\n".join(doc.page_content for doc in docs)
    
    def answer(self, user_question_and_id: str) -> str:
        try:
            user_id, question = user_question_and_id.split("|", 1)
        except ValueError:
            return "Error: Input for RAGTool must be in the format 'user_id|question'"
        
        print(f"Getting accessible sources for user {user_id}...")
        accessible_sources = self._get_accessible_doc_sources(user_id)

        if not accessible_sources:
            return "You do not have access to any documents, or no relevant documents were found."
        
        retriever = self.vector_store.as_retriever(
            search_kwargs={
                "k": 10,
                "filter": {"source": accessible_sources}
            }
        )

        rag_chain = (
            {"context": retriever | self._format_docs, "question": RunnablePassthrough()}
            | self.chain
        )

        response = rag_chain.invoke(question)
        return response
    
# if __name__ == '__main__':
#     rag_tool = RAGTool()
#     question = "bob_02|what is order id of invoice 18509?"
#     answer = rag_tool.answer(question)
#     print("\n--- Test ---")
#     print(f"Câu hỏi: {question}")
#     print(f"Câu trả lời: {answer}")