from fastmcp import FastMCP
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

from ..config import get_config
from ..metadata.store import MetadataStore
from ..retrieval.index import SearchIndex
from ..summarizer.engine import Summarizer

logger = logging.getLogger(__name__)

def create_server():
    cfg = get_config()
    mcp = FastMCP("University Memory System", instructions="I am your university research and student management assistant.")

    # Lazy init components
    store = MetadataStore(cfg.sqlite_path)
    index = SearchIndex(str(cfg.qdrant_path), cfg.embeddings.model)
    summarizer = Summarizer(cfg.llm.model, cfg.llm.base_url)

    @mcp.tool
    def search_documents(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search through all indexed university documents using hybrid retrieval."""
        results = index.search(query, top_k=top_k)
        return results

    @mcp.tool
    def get_folder_summary(folder_path: str) -> str:
        """Get the recursive summary of a specific folder."""
        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT content FROM summaries
                JOIN folders ON summaries.item_id = folders.id
                WHERE folders.path = ? AND summaries.item_type = 'folder'
                ORDER BY summaries.created_at DESC LIMIT 1
            ''', (folder_path,))
            row = cursor.fetchone()
            if row:
                return row[0]
            return f"No summary found for folder {folder_path}"

    @mcp.tool
    def get_student_context(student_name: str) -> str:
        """Get complete context for a student, including their folders, status, and latest activity."""
        with store._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT s.*, f.path as folder_path FROM students s
                LEFT JOIN folders f ON s.folder_id = f.id
                WHERE s.name LIKE ?
            ''', (f"%{student_name}%",))
            student = cursor.fetchone()
            if not student:
                return f"No student found with name {student_name}"

            # (id, name, email, topic, status, folder_id, folder_path)
            context = f"Student: {student[1]}\nEmail: {student[2]}\nTopic: {student[3]}\nStatus: {student[4]}\nFolder: {student[6]}\n"

            # Add folder summary if exists
            if student[6]:
                summary_text = get_folder_summary(student[6])
                context += f"\nFolder Summary:\n{summary_text}"

            return context

    @mcp.tool
    def generate_mail_reply(student_name: str, incoming_mail_text: str) -> str:
        """Generate a draft reply for a student based on their context and previous communication."""
        context = get_student_context(student_name)
        prompt = f"""
You are a university professor. Generate a helpful, professional reply to the following student email.
Use the provided student context to make the reply specific.

Student Context:
{context}

Incoming Email:
{incoming_mail_text}

Draft Reply:
"""
        return summarizer.summarize_file("reply_draft", prompt)

    @mcp.tool
    def get_open_tasks() -> str:
        """Find all open tasks extracted from documents and emails."""
        results = index.search("offene Aufgaben open tasks TODO", top_k=20)
        tasks = []
        for res in results:
            tasks.append(f"- From {res.get('filename', 'Unknown')}: {res['content'][:200]}...")

        return "\n".join(tasks) if tasks else "No open tasks found."

    @mcp.tool
    def compare_document_versions(path1: str, path2: str) -> str:
        """Compare two versions of a document and summarize the changes."""
        from ..parser.factory import ParserFactory
        parser = ParserFactory(cfg.data_dir / "cache")
        c1 = parser.parse(Path(path1))
        c2 = parser.parse(Path(path2))

        if not c1 or not c2:
            return "Could not read one of the files for comparison."

        prompt = f"""
Compare the following two versions of a document and summarize the key changes, improvements, or regressions.

Version 1 ({path1}):
{c1[:5000]}

Version 2 ({path2}):
{c2[:5000]}

Comparison Summary:
"""
        return summarizer.summarize_file("comparison", prompt)

    return mcp

if __name__ == "__main__":
    mcp = create_server()
    mcp.run()
