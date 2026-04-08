# rag.py
import os
from typing import List
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

