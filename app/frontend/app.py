import streamlit as st
import requests
import os
from pathlib import Path

BACKEND_URL = "http://localhost:8000"
LOGIN_URL = f"{BACKEND_URL}/login"
CHAT_URL = f"{BACKEND_URL}/chat"
UPLOAD_URL = f"{BACKEND_URL}/upload"

st.set_page_config(page_title="Enterprise RAG System", layout="wide")

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.session_state.password = ""
    st.session_state.role = ""
    st.session_state.messages = []
    st.session_state.current_mode = None

if not st.session_state.authenticated:
    st.title("🔐 Enterprise RAG System Login")
    st.markdown("---")

    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_btn = st.form_submit_button("Login")

        if login_btn:
            try:
                response = requests.get(
                    LOGIN_URL,
                    auth=(username, password)
                )
                if response.status_code == 200:
                    data = response.json()
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.session_state.password = password
                    st.session_state.role = data["role"]
                    st.success(f"✅ Welcome {username}!")
                    st.rerun()
                else:
                    st.error("❌ Invalid credentials")
            except Exception as e:
                st.error(f"🚨 Error: {e}")

else:
    st.sidebar.title(f"👤 {st.session_state.username}")
    st.sidebar.markdown(f"**Role:** {st.session_state.role}")

    if st.sidebar.button("🚪 Logout"):
        st.session_state.authenticated = False
        st.session_state.username = ""
        st.session_state.password = ""
        st.session_state.role = ""
        st.session_state.messages = []
        st.session_state.current_mode = None
        st.rerun()

    st.sidebar.markdown("---")

    if st.session_state.role == "c-level":
        st.sidebar.subheader("Select Mode")

        if st.sidebar.button("📤 Upload Documents", use_container_width=True):
            st.session_state.current_mode = "upload"
            st.rerun()

        if st.sidebar.button("💬 Chat Access", use_container_width=True):
            st.session_state.current_mode = "chat"
            st.rerun()

        if st.session_state.current_mode == "upload":
            st.title("📤 Document Upload")
            st.markdown("Upload documents and assign them to departments")
            st.markdown("---")

            department = st.selectbox(
                "Select Department",
                ["hr", "engineering", "finance", "marketing", "general"]
            )

            uploaded_files = st.file_uploader(
                "Upload Documents",
                type=["pdf", "csv", "docx", "doc", "pptx", "ppt", "md"],
                accept_multiple_files=True
            )

            if st.button("Process and Index Documents"):
                if uploaded_files:
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    total_files = len(uploaded_files)

                    for idx, uploaded_file in enumerate(uploaded_files):
                        status_text.text(f"Processing {uploaded_file.name}...")

                        try:
                            files = {
                                'file': (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)
                            }
                            data = {'department': department}

                            response = requests.post(
                                UPLOAD_URL,
                                files=files,
                                data=data,
                                auth=(st.session_state.username, st.session_state.password)
                            )

                            if response.status_code == 200:
                                st.success(f"✅ Processed: {uploaded_file.name}")
                            else:
                                st.error(f"❌ Error: {response.json().get('detail', 'Upload failed')}")

                        except Exception as e:
                            st.error(f"❌ Error processing {uploaded_file.name}: {e}")

                        progress_bar.progress((idx + 1) / total_files)

                    status_text.text("✅ All documents processed successfully!")
                else:
                    st.warning("Please upload at least one document")

        elif st.session_state.current_mode == "chat":
            st.title("💬 Chat with Documents (Full Access)")
            st.markdown("You have access to all department documents")
            st.markdown("---")

            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

            user_input = st.chat_input("Ask a question...")

            if user_input:
                st.session_state.messages.append({"role": "user", "content": user_input})

                with st.chat_message("user"):
                    st.markdown(user_input)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            response = requests.post(
                                CHAT_URL,
                                json={"message": user_input},
                                auth=(st.session_state.username, st.session_state.password)
                            )

                            if response.status_code == 200:
                                answer = response.json()["answer"]
                                st.markdown(answer)
                                st.session_state.messages.append({"role": "assistant", "content": answer})
                            else:
                                error_msg = f"❌ Error: {response.status_code}"
                                st.error(error_msg)
                                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                        except Exception as e:
                            error_msg = f"❌ Error: {e}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})

        else:
            st.title("Welcome to Enterprise RAG System")
            st.markdown("### Please select a mode from the sidebar:")
            st.markdown("- **📤 Upload Documents**: Upload and categorize documents by department")
            st.markdown("- **💬 Chat Access**: Ask questions across all departments")

    else:
        st.title(f"💬 Chat with {st.session_state.role.capitalize()} Documents")
        st.markdown(f"You have access to documents from your department")
        st.markdown("---")

        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        user_input = st.chat_input("Ask a question...")

        if user_input:
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        response = requests.post(
                            CHAT_URL,
                            json={"message": user_input},
                            auth=(st.session_state.username, st.session_state.password)
                        )

                        if response.status_code == 200:
                            answer = response.json()["answer"]
                            st.markdown(answer)
                            st.session_state.messages.append({"role": "assistant", "content": answer})
                        else:
                            error_msg = f"❌ Error: {response.status_code}"
                            st.error(error_msg)
                            st.session_state.messages.append({"role": "assistant", "content": error_msg})
                    except Exception as e:
                        error_msg = f"❌ Error: {e}"
                        st.error(error_msg)
                        st.session_state.messages.append({"role": "assistant", "content": error_msg})
