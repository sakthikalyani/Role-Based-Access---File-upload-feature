import os
import glob
from markdown import markdown
from bs4 import BeautifulSoup
from chromadb import PersistentClient
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def md_to_text(md_path):
    """Convert markdown to plain text"""
    with open(md_path, "r", encoding="utf-8") as file:
        html_conversion = markdown(file.read())
        text_conversion = BeautifulSoup(html_conversion, features="html.parser")
        return text_conversion.get_text()

def get_role_from_path(filepath, base_dir):
    """Extract role/department from file path"""
    p = Path(filepath).resolve()
    base = Path(base_dir).resolve()
    try:
        rel = p.relative_to(base)
        return rel.parts[0].lower()
    except ValueError:
        return "general"

def get_openai_embeddings(texts):
    """Generate embeddings using OpenAI"""
    response = client.embeddings.create(
        input=texts,
        model="text-embedding-3-small"
    )
    return [item.embedding for item in response.data]

def batch_embed(texts, batch_size=100):
    """Batch embedding for efficiency"""
    embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        emb = get_openai_embeddings(batch)
        embeddings.extend(emb)
    return embeddings

def index_documents(docs_dir):
    """
    Index all markdown documents from the specified directory
    Documents are organized by department folders
    """
    md_files = glob.glob(os.path.join(docs_dir, "**/*.md"), recursive=True)

    if not md_files:
        print("No markdown files found to index")
        return

    print(f"Found {len(md_files)} markdown files to index")

    all_chunks = []
    metadata = []

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )

    for md_file in md_files:
        role = get_role_from_path(md_file, docs_dir)
        text = md_to_text(md_file)
        chunks = text_splitter.split_text(text)

        for chunk in chunks:
            chunk = chunk.strip()
            if len(chunk) > 20:
                all_chunks.append(chunk)
                metadata.append({
                    "role": role,
                    "source": os.path.basename(md_file)
                })

    if not all_chunks:
        print("No text chunks generated from documents")
        return

    print(f"Generated {len(all_chunks)} chunks from documents")
    print("Generating embeddings...")

    embeddings = batch_embed(all_chunks)

    chroma_client = PersistentClient(path="./chroma_db")
    collection = chroma_client.get_or_create_collection(name="company_docs")

    existing_count = collection.count()
    print(f"Collection has {existing_count} existing documents")

    collection.add(
        embeddings=embeddings,
        documents=all_chunks,
        metadatas=metadata,
        ids=[f"doc_{existing_count + i}" for i in range(len(all_chunks))]
    )

    print(f"Successfully indexed {len(all_chunks)} chunks")
    print(f"Total documents in collection: {collection.count()}")
