import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)

from langchain.agents import Tool
from src.tools.rag_tool import RAGTool
from src.tools.text_to_sql_tool import TextToSQLTool

try:
    rag_tool_instance = RAGTool()
    text_to_sql_instance = TextToSQLTool()
except Exception as e:
    print(f"Lỗi khi khởi tạo tools: {e}")
    rag_tool_instance = None
    text_to_sql_instance = None

rag_search_tool = Tool(
    name="PDF Content Search",
    func=rag_tool_instance.answer if rag_tool_instance else lambda x: "RAG Tool is not available.",
    description="""
    Useful for answering questions about the content of PDF documents.
    Use this tool when the user asks about specific details, summaries, or information contained within the files.
    For example: 'What is the total amount of invoice X?', 'Summarize the marketing report.', 'Who are the recipients of invoices shipping to the UK?'
    Input to this tool should be a complete, specific question about the document content.
    """
)

text_to_sql_tool = Tool(
    name="Metadata Database Search",
    func=text_to_sql_instance.execute if text_to_sql_instance else lambda x: "SQL Tool is not available.",
    description="""
    Useful for answering questions about metadata of workspaces, spaces, users, and documents.
    Use this tool for questions about counts, dates, ownership, file names, sizes, and relationships between entities.
    For example: 'How many documents are in the 'Invoices' space?', 'Who is the owner of 'q1_ad_campaign.pdf'?', 'Which workspace was updated most recently?', 'List all spaces for user Alice.'
    Input to this tool should be a complete, natural language question about the metadata.
    """
)

agent_tools = [rag_search_tool, text_to_sql_tool]

if __name__ == '__main__':
    print("Available Agent Tools:")
    for tool in agent_tools:
        print(f"- {tool.name}: {tool.description[:70]}...")