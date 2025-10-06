# ChatPDF-AI-Agent
ChatPDF: AI-Agent with RAG and Text- to-SQL Tool
# AI Agent with RAG + Text-to-SQL

This project is an AI Agent that can answer questions by intelligently switching between two powerful tools:
1.  **Retrieval-Augmented Generation (RAG):** To query the content of uploaded PDF documents.
2.  **Text-to-SQL:** To query structured metadata about users, workspaces, and files.

The agent is context-aware, handles user permissions, and provides a simple web interface for interaction.

You can see demo at here (https://drive.google.com/file/d/1r9Jo9a-cvtfpxUQgRwkSuzrGBVvaxJ08/view?usp=sharing)
## Features

- **ReAct-Powered Agent**: Utilizes the ReAct (Reasoning and Acting) framework to dynamically choose between RAG for content search and Text-to-SQL for metadata queries.
- **Conversational Memory:** Understands the context of the conversation (e.g., knows which file was just uploaded).
- **Permission System:** Users can only access data and documents they are authorized to see.
- **Re-ranking** methods to increase the relevance of retrieved results.
- **Vector Database:** Uses FAISS for efficient semantic search on PDF content.
- **Metadata Database:** Uses SQLite to manage users, files, and permissions.
- **File Upload:** Users can upload new PDF documents into their workspaces.
- **Web Interface:** A simple and interactive UI built with Streamlit.

## Tech Stack

- **Backend:** Python, LangChain
- **AI Models:** Google Gemini (for Chat & Embeddings)
- **UI:** Streamlit
- **Databases:** FAISS (Vector), SQLite (Relational)

---

## Quickstart Guide

Follow these steps to set up and run the project locally.

### 1. Prerequisites

- Python 3.10
- Git

### 2. Setup

**1. Clone the repository:**
```bash
git clone git@github.com:trthminh/ChatPDF-AI-Agent.git
cd ChatPDF-AI-Agent
```
**2. Install libraries:**
```bash
pip install -r requirements.txt
```
**3. Set up your API Key**
- Get a free Google API Key from Google AI Studio.
- Get a free Cohere API Key from (https://dashboard.cohere.com/api-keys)
- Create file .env.
- Open the .env file and paste your API key:
```bash
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY_HERE"
```
**4. Prepare the Data:**
- Ingest data:
```bash
python scripts/ingest_data.py
```
**5. Run the Application**
```bash
streamlit run app.py
```