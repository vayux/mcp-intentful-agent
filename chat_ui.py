"""Streamlit Chat UI for MCP Agent Service.

A simple web interface for interacting with the MCP agent service.
Provides:
- Real-time chat interface
- Service status monitoring
- Quick action buttons
- Session management
"""
import requests
import streamlit as st

# Configuration
AGENT_SERVICE_URL = "http://localhost:3000"

# Page configuration
st.set_page_config(
    page_title="MCP Agent Chat",
    page_icon=None,
    layout="centered",
)

# Custom CSS for better chat appearance
st.markdown("""
<style>
    .stChatMessage {
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 0.5rem;
    }
    .status-indicator {
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        margin-right: 8px;
    }
    .status-online {
        background-color: #00c853;
    }
    .status-offline {
        background-color: #ff1744;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("MCP Agent Chat")
st.markdown("*AI Agent for Order Management - Powered by MCP*")

# Sidebar with status and controls
with st.sidebar:
    st.header("Controls")
    
    # Check service status
    def check_services():
        backend_ok = False
        agent_ok = False
        try:
            resp = requests.get("http://localhost:8080/health", timeout=2)
            backend_ok = resp.status_code == 200
        except:
            pass
        try:
            resp = requests.get(f"{AGENT_SERVICE_URL}/health", timeout=2)
            agent_ok = resp.status_code == 200
        except:
            pass
        return backend_ok, agent_ok
    
    backend_ok, agent_ok = check_services()
    
    st.subheader("Service Status")
    if backend_ok:
        st.markdown('<span class="status-indicator status-online"></span> Backend (8080)', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-indicator status-offline"></span> Backend (8080) - Offline', unsafe_allow_html=True)
    
    if agent_ok:
        st.markdown('<span class="status-indicator status-online"></span> Agent Service (3000)', unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-indicator status-offline"></span> Agent Service (3000) - Offline', unsafe_allow_html=True)
    
    st.divider()
    
    # Reset conversation button
    if st.button("New Conversation", use_container_width=True):
        # Clear session state
        if "session_id" in st.session_state:
            # Try to clear server-side session
            try:
                requests.delete(f"{AGENT_SERVICE_URL}/sessions/{st.session_state.session_id}", timeout=2)
            except:
                pass
        st.session_state.messages = []
        st.session_state.session_id = None
        st.rerun()
    
    st.divider()
    
    # Quick actions
    st.subheader("Try These")
    quick_messages = [
        "Hello!",
        "What can you do?",
        "What is my order status?",
        "Show my latest order",
        "Cancel my order",
        "Order 2 widgets and 1 gadget",
    ]
    
    for msg in quick_messages:
        if st.button(msg, key=f"quick_{msg}", use_container_width=True):
            st.session_state.quick_message = msg
            st.rerun()
    
    st.divider()
    
    # Session info
    if "session_id" in st.session_state and st.session_state.session_id:
        st.caption(f"Session: `{st.session_state.session_id[:8]}...`")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle quick message if set
if "quick_message" in st.session_state and st.session_state.quick_message:
    prompt = st.session_state.quick_message
    st.session_state.quick_message = None
    
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Call agent service
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                payload = {"message": prompt}
                if st.session_state.session_id:
                    payload["session_id"] = st.session_state.session_id
                
                response = requests.post(
                    f"{AGENT_SERVICE_URL}/chat",
                    json=payload,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    reply = data["reply"]
                    st.session_state.session_id = data["session_id"]
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                else:
                    error_msg = f"Error: {response.status_code} - {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except requests.exceptions.ConnectionError:
                error_msg = "Cannot connect to Agent Service. Make sure it's running on port 3000."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Chat input
if prompt := st.chat_input("Type your message..."):
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Call agent service
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                payload = {"message": prompt}
                if st.session_state.session_id:
                    payload["session_id"] = st.session_state.session_id
                
                response = requests.post(
                    f"{AGENT_SERVICE_URL}/chat",
                    json=payload,
                    timeout=30,
                )
                
                if response.status_code == 200:
                    data = response.json()
                    reply = data["reply"]
                    st.session_state.session_id = data["session_id"]
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                else:
                    error_msg = f"Error: {response.status_code} - {response.text}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except requests.exceptions.ConnectionError:
                error_msg = "Cannot connect to Agent Service. Make sure it's running on port 3000."
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# Footer
st.divider()
st.caption("MCP Agent Service POC | Built with FastMCP + FastAPI + Streamlit")
