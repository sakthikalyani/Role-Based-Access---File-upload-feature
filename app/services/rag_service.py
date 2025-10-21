#rag_service.py
from chromadb import PersistentClient
from dotenv import load_dotenv
import os
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
import pandas as pd

# -------------------- Setup --------------------
load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
client_db = PersistentClient(path="./chroma_db")
collection = client_db.get_or_create_collection(name="company_docs")

# Setup LLM for CSV/Excel agents
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Folder where CSV/Excel files are saved (by department)
csv_folder = "./uploaded_documents"

# Dictionary to store Pandas agents for each department
csv_agents = {}

# Build Pandas agents for every CSV/Excel file per department
print("\n" + "="*80)
print("🔧 INITIALIZING PANDAS AGENTS FOR CSV/EXCEL FILES")
print("="*80)
for dirpath, _, filenames in os.walk(csv_folder):
    for file in filenames:
        if file.endswith((".csv", ".xlsx", ".xls")):
            full_path = os.path.join(dirpath, file)
            # department is the first folder under uploaded_documents
            role = os.path.relpath(full_path, csv_folder).split(os.sep)[0].lower()

            try:
                if file.endswith(".csv"):
                    print(f"📊 Loading CSV: {file} for role '{role}'")
                    df = pd.read_csv(full_path)
                else:
                    print(f"📊 Loading Excel: {file} for role '{role}'")
                    df = pd.read_excel(full_path)

                csv_agents[role] = create_pandas_dataframe_agent(
                    llm,
                    df,
                    verbose=True,
                    agent_type="openai-tools",
                    max_iterations=10,
                    early_stopping_method="generate",
                    allow_dangerous_code=True
                )
                print(f"✅ Successfully loaded agent for role '{role}' from {file}")
                print(f"   DataFrame shape: {df.shape}")
                print(f"   Columns: {list(df.columns)}\n")
            except Exception as e:
                print(f"❌ Failed to load CSV/Excel agent for {role}: {e}\n")

print(f"✅ Total CSV/Excel agents loaded: {len(csv_agents)}")
print(f"   Available roles: {list(csv_agents.keys())}\n")
print("="*80 + "\n")


# -------------------- Embedding helper --------------------
def get_openai_embedding(text: str) -> list:
    """Generate OpenAI embedding for a text"""
    response = client.embeddings.create(
        input=[text],
        model="text-embedding-3-small"
    )
    return response.data[0].embedding


# -------------------- Main RAG Answer --------------------
def rag_answer(query: str, role: str) -> str:
    role = role.lower()
    
    print("\n" + "="*80)
    print(f"🔍 NEW QUERY RECEIVED")
    print("="*80)
    print(f"Query: {query}")
    print(f"Role: {role}")
    print(f"Has CSV agent: {role in csv_agents}")
    print("="*80 + "\n")

    # ================== STEP 1: ALWAYS QUERY CHROMA DB FIRST ==================
    print("📚 STEP 1: Querying ChromaDB for embedded documents...")
    
    query_embed = get_openai_embedding(query)
    
    if role == "c-level":
        print("   → C-Level user: Searching ALL departments")
        results = collection.query(query_embeddings=[query_embed], n_results=10)
    else:
        print(f"   → Department user: Searching only '{role}' department")
        results = collection.query(
            query_embeddings=[query_embed],
            n_results=10,
            where={"role": role}
        )
    
    print(f"   → Found {len(results['documents'][0]) if results['documents'] else 0} document chunks")
    
    has_chroma_results = (
        results["documents"] and 
        results["documents"][0] and 
        len(results["documents"][0]) > 0
    )
    
    if has_chroma_results:
        print("   ✅ Found relevant documents in ChromaDB")
        context_chunks = results["documents"][0]
        metas = results["metadatas"][0]
        
        seen = set()
        citations = "\n\nSources:\n"
        for meta in metas:
            source = meta.get("source", "Unknown File")
            if source not in seen:
                citations += f"- {source}\n"
                seen.add(source)
        
        context = "\n".join(context_chunks)
        print(f"   → Context length: {len(context)} characters")
        
        prompt = f"""
You are a helpful enterprise assistant that provides accurate answers only using the data given in the context below.

Your job is to:
1. Read and understand the user query.
2. Match the query against relevant facts in the provided context.
3. Extract exact values and generate a helpful, clear answer.
4. If possible, cite the original source of the data.

If the context does NOT contain the answer, respond EXACTLY with:
"NOT_FOUND_IN_EMBEDDINGS"

Do not make up information. Only answer if the context contains the information.

---
Context:
{context}

User Question:
{query}

Answer:
"""
        
        print("   → Generating answer from ChromaDB context...")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        
        answer = response.choices[0].message.content
        print(f"   → Answer generated: {answer[:100]}...")
        
        if "NOT_FOUND_IN_EMBEDDINGS" not in answer:
            print("   ✅ Answer found in ChromaDB - returning result\n")
            return answer + citations
        else:
            print("   ⚠️  ChromaDB didn't have the answer, falling back to CSV agent...")
    else:
        print("   ⚠️  No relevant documents found in ChromaDB")
    
    
    # ================== STEP 2: FALLBACK TO CSV/EXCEL AGENT ==================
    print("\n📊 STEP 2: Trying CSV/Excel Pandas Agent...")
    
    if role == "c-level":
        print("   → C-Level: Querying ALL CSV agents")
        if csv_agents:
            all_csv_answers = []
            for dept, agent in csv_agents.items():
                print(f"   → Querying {dept} CSV agent...")
                try:
                    ans = agent.run(query)
                    print(f"      ✅ Got response from {dept}")
                    if ans and "I don't know" not in ans.lower() and "sorry" not in ans.lower():
                        # ✅ Extra LLM step for formatting
                        csv_prompt = f"""
You are a helpful enterprise assistant. The following answer was retrieved from the {dept.capitalize()} department's CSV/Excel dataset.
Please rewrite it into a clear, professional, human-readable response.
Give response paragraph which is human rewdeable.
Do not include email or phone number in the response.
---
Raw CSV Response:
{ans}

User Question:
{query}

Answer:
"""
                        llm_response = client.chat.completions.create(
                            model="gpt-4o-mini",
                            messages=[
                                {"role": "system", "content": "You are a helpful assistant."},
                                {"role": "user", "content": csv_prompt}
                            ]
                        )
                        final_ans = llm_response.choices[0].message.content
                        print(f"      🤖 LLM formatted response: {final_ans[:100]}...")  # ADD THIS
                        
                        all_csv_answers.append(f"---\n📊 Data from {dept.capitalize()} Department:\n{final_ans}")
                    else:
                        print(f"      ⚠️  No useful answer from {dept}")
                except Exception as e:
                    print(f"      ❌ Error in {dept} CSV agent: {e}")
                    all_csv_answers.append(f"❌ Error querying {dept} data: {e}")
            
            if all_csv_answers:
                print(f"   ✅ Found {len(all_csv_answers)} CSV answers\n")
                return "\n\n".join(all_csv_answers)
            else:
                print("   ⚠️  No CSV agents had useful answers")
        else:
            print("   ⚠️  No CSV agents available for c-level")
    
    elif role in csv_agents:
        print(f"   → Querying CSV agent for role '{role}'")
        try:
            csv_response = csv_agents[role].run(query)
            print(f"   ✅ Got response from CSV agent")
            print(f"   → Raw Response: {csv_response[:100]}...")
            
            if csv_response and "I don't know" not in csv_response.lower() and "sorry" not in csv_response.lower():
                # ✅ Extra LLM step for formatting
                csv_prompt = f"""
You are a helpful enterprise assistant. The following answer was retrieved directly from the {role.capitalize()} department's CSV/Excel dataset.
Please rewrite it into a clear, professional, human-readable response. Give response paragraph which is human rewdeable.
Do not include email or phone number in the response.
---
Raw CSV Response:
{csv_response}

User Question:
{query}

Answer:
"""
                llm_response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": csv_prompt}
                    ]
                )
                answer = llm_response.choices[0].message.content
                print("   ✅ CSV agent found the answer - returning formatted result\n")
                return answer
            else:
                print("   ⚠️  CSV agent couldn't find the answer")
        except Exception as e:
            print(f"   ❌ Failed to run CSV/Excel agent: {e}")
    else:
        print(f"   ⚠️  No CSV agent available for role '{role}'")
    
    
    # ================== STEP 3: NO ANSWER FOUND ==================
    print("\n❌ STEP 3: No answer found in either ChromaDB or CSV agents")
    print("="*80 + "\n")
    return "I'm sorry, I couldn't find relevant information based on your access level and the available data."
