import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from langchain import hub
from langchain.agents import create_react_agent, AgentExecutor
from langchain_google_genai import ChatGoogleGenerativeAI

from src.agent.tools import agent_tools
from src.config import *

class MainAgent:
    def __init__(self):
        print("Initilizing Main Agent...")
        self.llm = ChatGoogleGenerativeAI(
            model=MODEL_NAME,
            google_api_key=GOOGLE_API_KEY,
            temperature=0,
            convert_system_message_to_human=True
        )

        prompt = hub.pull("hwchase17/react")

        agent = create_react_agent(self.llm, agent_tools, prompt)

        self.agent_executor = AgentExecutor(
            agent=agent,
            tools=agent_tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=5
        )

    def run(self, user_question: str, user_id: str) -> str:
        structured_input = f"""
        Current user is identified by user_id '{user_id}'.
        User's question: '{user_question}'

        IMPORTANT: When you use a tool, you MUST pass the input in the format 'user_id|question'.
        For example, for the Metadata Database Search tool, the Action Input should be '{user_id}|{user_question}'.
        For the PDF Content Search tool, the Action Input should be '{user_id}|{user_question}'.
        """

        response = self.agent_executor.invoke({
            "input": structured_input
        })
        
        return response['output']

if __name__ == '__main__':
    main_agent = MainAgent()
    
    # print("\n--- TEST CASE 1: Only Text-to-SQL ---")
    # question1 = "How many spaces are in the 'Accounting' workspace?"
    # main_agent.run(question1)

    # print("\n--- TEST CASE 2: Only RAG ---")
    # question2 = "What is the total amount for invoice #18509?"
    # main_agent.run(question2)

    print("\n--- TEST CASE 3: ---")
    question3 = "What is the filename of the most recently uploaded document?"
    main_agent.run(question3)
    # print("\n--- TEST CASE: Alice asks about her workspaces (SQL) ---")
    # # Alice có quyền truy cập vào Marketing và Accounting
    # main_agent.run("List all my workspaces", user_id="alice_01")

    # print("\n--- TEST CASE: Bob asks about his workspaces (SQL) ---")
    # # Bob chỉ có quyền truy cập vào Accounting
    # main_agent.run("List all my workspaces", user_id="bob_02")