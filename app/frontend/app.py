import streamlit as st
import requests
import json
from datetime import datetime
import pandas as pd

# Constants
API_URL = "http://localhost:8000/api"

def get_token():
    """Retrieve authentication token from session state."""
    return st.session_state.get("token")

def is_authenticated():
    """Check if user is authenticated."""
    return "token" in st.session_state

def login(email: str, password: str) -> bool:
    """Authenticate user and store token."""
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": email, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            return True
        return False
    except:
        return False

def signup(email: str, username: str, password: str) -> bool:
    """Register new user."""
    try:
        response = requests.post(
            f"{API_URL}/auth/signup",
            json={"email": email, "username": username, "password": password}
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.token = data["access_token"]
            return True
        return False
    except:
        return False

def get_conversations():
    """Fetch user's conversations."""
    headers = {"Authorization": f"Bearer {get_token()}"}
    response = requests.get(f"{API_URL}/conversations", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def get_conversation_messages(conversation_id: int):
    """Fetch messages for a specific conversation."""
    headers = {"Authorization": f"Bearer {get_token()}"}
    response = requests.get(f"{API_URL}/conversations/{conversation_id}", headers=headers)
    if response.status_code == 200:
        return response.json()
    return []

def send_message(content: str, conversation_id: int = None):
    """Send message to API and get response."""
    headers = {"Authorization": f"Bearer {get_token()}"}
    data = {"content": content, "conversation_id": conversation_id}
    response = requests.post(f"{API_URL}/chat/send", headers=headers, json=data)
    if response.status_code == 200:
        return response.json()
    return None

def send_feedback(message_id: int, rating: int):
    """Send feedback for a message."""
    headers = {"Authorization": f"Bearer {get_token()}"}
    response = requests.post(
        f"{API_URL}/chat/{message_id}/feedback",
        headers=headers,
        params={"rating": rating}
    )
    return response.status_code == 200

def main():
    st.set_page_config(page_title="AmanChat", layout="wide")
    st.title("AmanChat")

    if not is_authenticated():
        # Login/Signup tabs
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        
        with tab1:
            with st.form("login_form"):
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Login")
                if submit and login(email, password):
                    st.rerun()
        
        with tab2:
            with st.form("signup_form"):
                email = st.text_input("Email")
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit = st.form_submit_button("Sign Up")
                if submit and signup(email, username, password):
                    st.rerun()
    
    else:
        # Chat interface
        col1, col2 = st.columns([1, 3])
        
        with col1:
            st.button("New Chat", on_click=lambda: st.session_state.pop("current_conversation", None))
            conversations = get_conversations()
            for conv in conversations:
                if st.button(
                    f"{conv['title'] or 'Untitled'} ({conv['created_at'][:10]})",
                    key=f"conv_{conv['id']}"
                ):
                    st.session_state.current_conversation = conv["id"]
        
        with col2:
            if "messages" not in st.session_state:
                st.session_state.messages = []
            
            if "current_conversation" in st.session_state:
                messages = get_conversation_messages(st.session_state.current_conversation)
                st.session_state.messages = messages
            
            # Display messages
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.write(msg["content"])
                    if msg["role"] == "assistant":
                        col1, col2 = st.columns([1, 20])
                        with col1:
                            if st.button("👍", key=f"up_{msg['id']}"):
                                send_feedback(msg["id"], 1)
                            if st.button("👎", key=f"down_{msg['id']}"):
                                send_feedback(msg["id"], -1)
            
            # Message input
            if prompt := st.chat_input("What's on your mind?"):
                conversation_id = st.session_state.get("current_conversation")
                if messages := send_message(prompt, conversation_id):
                    st.session_state.messages.extend(messages)
                    if not conversation_id:
                        st.session_state.current_conversation = messages[0]["conversation_id"]
                    st.rerun()

if __name__ == "__main__":
    main()