# 🤖 FinsightAI

**FinsightAI** is a secure, role-based AI assistant built for FinSolve Technologies to empower different departments with instant, accurate, and context-rich insights using RAG (Retrieval-Augmented Generation).

---

## Project Overview

**Domain:** FinTech  
**Function:** AI Engineering  

FinSolve Technologies is a leading FinTech company offering innovative financial services to individuals and enterprises. However, communication delays and siloed data across departments (Finance, Marketing, HR, Engineering, and C-Level) have caused major bottlenecks in decision-making and project execution.

To tackle this, a digital transformation initiative was launched to build **FinsightAI** — a secure, role-aware AI chatbot using RAG (Retrieval-Augmented Generation) and Role-Based Access Control (RBAC). The assistant helps teams access accurate, department-specific insights instantly and securely.

---

## Problem Statement

Traditional workflows in FinSolve suffer from:

-  Communication delays  
-  Data silos across departments  
-  Inefficiencies in decision-making  

These gaps reduce productivity and impact strategic outcomes.

---

## Solution

**FinsightAI** was built to:

-  Authenticate users and assign roles (e.g., HR, Finance, Engineering)
-  Use RAG to retrieve and contextualize internal data
-  Respond to queries using CSV files + vector store (ChromaDB)
-  Enforce role-based access to data

---

## Roles              
**Finance**        
**Marketing**      
**HR**             
**Engineering**    
**C-Level**  - Full access to all department data
**Employee** 
---

## Tech Stack

-  Python 3.11
-  FastAPI (Backend)
-  OpenAI GPT-4o-mini (LLM)
-  ChromaDB (Vector Store for documents)
-  LangChain + Pandas (CSV agents)
-  Streamlit (Chatbot UI)

---

## How to Run Locally

1. Clone the repo:
   git clone https://github.com/yourusername/ds-rpc-01.git

2. Set up virtual environment and install dependencies:
   pip install -r requirements.txt

3. Start the backend:
   uvicorn app.main:app --reload

4. Start the Streamlit frontend:
   streamlit run app.py

5. Visit:
   http://localhost:8501

