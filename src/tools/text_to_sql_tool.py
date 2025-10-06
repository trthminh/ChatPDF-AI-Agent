import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from langchain_community.tools.sql_database.tool import QuerySQLDataBaseTool
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from operator import itemgetter

from src.config import *
from langchain_google_genai import ChatGoogleGenerativeAI

class TextToSQLTool:
    def __init__(self, db_path=SQL_DATABASE_PATH):
        print("Đang khởi tạo TextToSQL Tool...")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found at {db_path}. Please run ingest_data.py first.")
            
        self.db = SQLDatabase.from_uri(f"sqlite:///{db_path}")
        self.llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
            convert_system_message_to_human=True
        )
        self.chain = self._build_chain()
        print("Initialize Text-to-SQL Tool successful.")

    def get_schema(self, _):
        return self.db.get_table_info()

    def _build_chain(self):        
        generate_query_chain = create_sql_query_chain(self.llm, self.db)
        
        execute_query_tool = QuerySQLDataBaseTool(db=self.db)

        def clean_sql(query_dict):
            q = query_dict["query"]
            if q.strip().lower().startswith("sqlquery:"):
                q = q.split(":", 1)[1].strip()
            return {"query": q}

        sql_chain = (
            generate_query_chain
            | RunnableLambda(lambda q: {"query": q})
            | RunnableLambda(clean_sql)
            | RunnablePassthrough.assign(
                result=itemgetter("query") | execute_query_tool
            )
        )
        return sql_chain
        
    def execute(self, user_question_and_id) -> str:
        try:
            user_id, question = user_question_and_id.split('|', 1)
        except ValueError:
            return "Error: Input for TextToSQLTool must be in the format 'user_id|question'."
            
        print(f"Đang xử lý câu hỏi từ user '{user_id}' bằng TextToSQL Tool: '{question}'")
        
        contextual_question = f"""
        The current user is identified by user_id '{user_id}'. 
        All queries MUST be filtered based on this user's permissions.
        To check for permissions, you MUST use the 'User_Workspace_Membership' and 'User_Space_Membership' tables to join with other tables.
        For example, to find workspaces for this user, you must query 'SELECT T1.name FROM Workspace AS T1 JOIN User_Workspace_Membership AS T2 ON T1.id = T2.workspace_id WHERE T2.user_id = \"{user_id}\"'.
        
        User's original question: '{question}'
        """
        
        result = self.chain.invoke({"question": contextual_question})
        
        print(f"-> SQL Query: {result['query']}")
        print(f"-> SQL Result: {result['result']}")
        
        answer_prompt = f"""
        Based on the user's question: '{question}'
        And the result from the database: '{result['result']}'
        
        Provide a concise, natural language answer.
        If the result is empty or an error, state that you couldn't find the information.
        """
        
        final_answer = self.llm.invoke(answer_prompt).content
        print(f"-> Final Answer: {final_answer}")
        
        return final_answer

if __name__ == '__main__':
    sql_tool = TextToSQLTool()

    # question1 = "How many users are there?"
    # answer1 = sql_tool.execute(question1)
    # print("\n--- Test 1 ---")
    # print(f"Câu hỏi: {question1}")
    # print(f"Câu trả lời: {answer1}")
    
    # Test câu hỏi 2
    question2 = "bob_02|Which workspace was updated most recently?"
    answer2 = sql_tool.execute(question2)
    print("\n--- Test 2 ---")
    print(f"Câu hỏi: {question2}")
    print(f"Câu trả lời: {answer2}")

    # Test câu hỏi 3
    question3 = "bob_02|List all spaces in the 'Accounting' workspace."
    answer3 = sql_tool.execute(question3)
    print("\n--- Test 3 ---")
    print(f"Câu hỏi: {question3}")
    print(f"Câu trả lời: {answer3}")