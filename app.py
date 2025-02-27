import streamlit as st
import google.generativeai as genai
import os
import json
import glob
import PyPDF2
import docx

# Page configuration with clean, centered layout
st.set_page_config(
    page_title="AI Assistant",
    page_icon="🤖",
    layout="centered"
)

# Apply custom CSS for a cleaner interface
st.markdown("""
    <style>
    .stApp {
        max-width: 800px;
        margin: 0 auto;
    }
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    .stChatMessageContent {
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    .stChatMessage [data-testid="chatAvatarIcon-user"] {
        background-color: #2979ff;
    }
    .stChatMessage [data-testid="chatAvatarIcon-assistant"] {
        background-color: #43a047;
    }
    </style>
""", unsafe_allow_html=True)

# Helper functions to read different file types
def read_pdf(file_path):
    """Extract text from PDF files"""
    with open(file_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
    return text

def read_docx(file_path):
    """Extract text from DOCX files"""
    doc = docx.Document(file_path)
    text = ""
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

def read_txt(file_path):
    """Read text from TXT files"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

# Load configuration from file
def load_config():
    # Default configuration in case file is not found
    default_config = {
        "bot_name": "AI Assistant",
        "temperature": 0.7,
        "model": "gemini-1.5-pro"
    }
    
    # Try to load from config file
    try:
        config_path = "config/settings.json"
        with open(config_path, 'r') as file:
            return json.load(file)
    except Exception as e:
        st.warning(f"Could not load configuration file. Using defaults. Error: {e}")
        return default_config

# Load system prompt from file
def load_system_prompt():
    try:
        prompt_path = "config/system_prompt.txt"
        with open(prompt_path, 'r', encoding='utf-8') as file:
            return file.read().strip()
    except Exception as e:
        st.warning(f"Could not load system prompt. Using default. Error: {e}")
        return "You are a helpful assistant. You're friendly, concise, and informative."

# Load suggested prompts from file
def load_suggested_prompts():
    try:
        prompts_path = "config/initial_prompts.txt"
        with open(prompts_path, 'r', encoding='utf-8') as file:
            prompts = [line.strip() for line in file.readlines() if line.strip()]
            return prompts
    except Exception as e:
        # Return default prompts if file not found
        return [
            "What can you help me with?",
            "Tell me about yourself.",
            "How does this work?"
        ]

# Load document context from files in the documents directory
def load_documents():
    context = ""
    try:
        # Look for documents in the documents folder
        document_files = []
        document_files.extend(glob.glob("documents/*.txt"))
        document_files.extend(glob.glob("documents/*.pdf"))
        document_files.extend(glob.glob("documents/*.docx"))
        
        for file_path in document_files:
            try:
                if file_path.endswith('.pdf'):
                    file_content = read_pdf(file_path)
                elif file_path.endswith('.docx'):
                    file_content = read_docx(file_path)
                else:  # .txt files
                    file_content = read_txt(file_path)
                
                context += f"\n\n--- Content from {os.path.basename(file_path)} ---\n{file_content}"
            except Exception as e:
                st.warning(f"Error reading {file_path}: {e}")
        
        return context
    except Exception as e:
        st.warning(f"Error loading documents: {e}")
        return ""

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Initialize conversation log file if enabled
def log_conversation(user_message, bot_response, config):
    if config.get("enable_logging", False):
        try:
            os.makedirs("logs", exist_ok=True)
            with open("logs/conversations.log", "a", encoding="utf-8") as log_file:
                log_file.write(f"User: {user_message}\n")
                log_file.write(f"Assistant: {bot_response}\n")
                log_file.write("-" * 50 + "\n")
        except Exception as e:
            st.error(f"Failed to log conversation: {e}")

# Initialize Gemini API
api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
if not api_key:
    st.error("API key not found. Please configure it in the Streamlit secrets or .env file.")
    st.stop()

genai.configure(api_key=api_key)

# Load configuration, system prompt, and documents
config = load_config()
BOT_NAME = config.get("bot_name", "AI Assistant")
SYSTEM_PROMPT = load_system_prompt()
TEMPERATURE = config.get("temperature", 0.7)
MODEL = config.get("model", "gemini-1.5-pro")
SUGGESTED_PROMPTS = load_suggested_prompts()

# Load document context once at startup
DOCUMENT_CONTEXT = load_documents()

# Display header with bot name
st.title(f"{BOT_NAME}")

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Display suggested prompts if no messages yet
if not st.session_state.messages:
    st.markdown("### Suggested Questions")
    cols = st.columns(min(3, len(SUGGESTED_PROMPTS)))
    
    for i, prompt in enumerate(SUGGESTED_PROMPTS[:6]):  # Limit to 6 suggestions
        with cols[i % 3]:
            if st.button(prompt, key=f"suggestion_{i}"):
                st.session_state.messages.append({"role": "user", "content": prompt})
                st.rerun()

# Function to get response from Gemini
def get_response(prompt):
    # Prepare context with system prompt and chat history
    context
