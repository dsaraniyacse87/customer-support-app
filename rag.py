# rag.py
import os
from typing import List
from langchain.agents import Tool
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI

KB_PATH = "data/kb_docs"
CHROMA_DIR = "chroma_db"

def load_kb() -> list[Document]:
    """Load KB documents from the specified directory."""
    loader = DirectoryLoader(KB_PATH, glob="**/*.md", show_progress=True, loader_cls=TextLoader)
    docs = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    return splitter.split_documents(docs)

def build_vectorstore(docs: list[Document]) -> Chroma:
    """Build a Chroma vector store from the provided documents."""
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectordb = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=CHROMA_DIR,
    )
    vectordb.persist()
    return vectordb

def get_vectorstore() -> Chroma:
    if os.path.exists(CHROMA_DIR):
        embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
        return Chroma(persist_directory=CHROMA_DIR, embedding_function=embeddings)
    else:
        docs = load_kb()
        return build_vectorstore(docs)
    

def kb_search_tool(query: str) -> str:
    """Search the KB vector store and return the top matching documents."""
    vectordb = get_vectorstore()
    retriever = vectordb.as_retriever(search_kwargs={"k": 3})
    docs = retriever.get_relevant_documents(query)
    if not docs:
        return "No relevant KB documents found."

    results = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        snippet = doc.page_content.strip().replace("\n", " ")
        results.append(f"[{i}] Source: {source}\n{snippet[:800]}")

    return "\n\n".join(results)


def get_kb_search_tool() -> Tool:
    return Tool(
        name="kb_search",
        func=kb_search_tool,
        description="Search the knowledge base for relevant articles and return the top matching results.",
    )


kb_search_tool = get_kb_search_tool()


def get_rag_chain():
    vectordb = get_vectorstore()
    retriever = vectordb.as_retriever(search_kwargs={"k": 4})
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        retriever=retriever,
        return_source_documents=True,
    )
    return qa

