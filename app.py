import streamlit as st
import google.generativeai as genai
import PyPDF2
from docx import Document
import io
import os

# --- Helper Functions ---

def extract_pdf_text(pdf_file):
    """Extracts text from an uploaded PDF file."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(pdf_file)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    except Exception as e:
        st.error(f"Error extracting PDF: {e}")
        return None
    return text

def extract_docx_text(docx_file):
    """Extracts text from an uploaded DOCX file."""
    text = ""
    try:
        doc = Document(docx_file)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        st.error(f"Error extracting DOCX: {e}")
        return None
    return text

def clean_text(text):
    """Cleans text by replacing multiple newlines/spaces with single spaces."""
    if not text:
        return ""
    cleaned = text.replace('\n', ' ').replace('\r', ' ')
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def chunk_text(text, chunk_size=1500, overlap=100):
    """Splits text into chunks with optional overlap for context."""
    if not text:
        return []
    words = text.split()
    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i:i + chunk_size]
        chunks.append(' '.join(chunk))
        i += (chunk_size - overlap) if (chunk_size - overlap) > 0 else chunk_size
    return chunks

# --- Streamlit App ---

st.set_page_config(page_title="Finance Document Assistant", layout="wide")
st.title("📈 Finance Document Summarizer & Q&A Assistant")

# --- Sidebar for Configuration and Upload ---
with st.sidebar:
    st.header("Configuration")
    
    # FOR LOCAL TESTING ONLY: Paste your key directly here
    # Make sure to replace "YOUR_API_KEY_HERE" with your actual key
    api_key = "AIzaSyA7I6XE39Ekh_Ry4B5-y-ijYiJlQvflex8"

    st.header("Upload Document")
    # This is the correct way to upload files in Streamlit
    uploaded_file = st.file_uploader(
        "Upload your PDF or DOCX file",
        type=["pdf", "docx"]
    )
    
    summarize_button = st.button("Generate Summary", disabled=(not uploaded_file or not api_key))

# --- Main App Logic ---

if api_key:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Failed to configure Gemini API: {e}")
        api_key = None
else:
    st.info("API Key not found.")


# Initialize session state variables
if "document_text" not in st.session_state:
    st.session_state.document_text = None
if "document_summary" not in st.session_state:
    st.session_state.document_summary = None
if "messages" not in st.session_state:
    st.session_state.messages = []


# Process uploaded file
if uploaded_file is not None:
    if st.session_state.get("last_uploaded_filename") != uploaded_file.name:
        st.session_state.last_uploaded_filename = uploaded_file.name
        st.session_state.document_summary = None
        st.session_state.messages = []
        
        with st.spinner(f"Processing {uploaded_file.name}..."):
            file_extension = os.path.splitext(uploaded_file.name)[1].lower()
            if file_extension == ".pdf":
                st.session_state.document_text = extract_pdf_text(uploaded_file)
            elif file_extension == ".docx":
                st.session_state.document_text = extract_docx_text(uploaded_file)
            else:
                st.session_state.document_text = None
        
        if st.session_state.document_text:
            st.success(f"Successfully extracted text from {uploaded_file.name}.")
        else:
            st.error("Failed to extract text from the document.")


# Handle summarization
if summarize_button and st.session_state.document_text:
    st.session_state.document_summary = None
    with st.spinner("🧠 Generating summary with Gemini... This may take a moment."):
        full_text = st.session_state.document_text
        cleaned_text = clean_text(full_text)
        chunks = chunk_text(cleaned_text)

        all_summaries = []
        for i, chunk in enumerate(chunks):
            prompt = (
                "You are an expert financial analyst. Summarize the following text in a clear, "
                "crisp, and detailed bullet-point format. Focus on key financial information, "
                "figures, and important concepts. Each bullet point should be concise but informative. "
                f"If there are specific numbers, dates, or names, include them.\n\n"
                f"Text to summarize:\n{chunk}\n\n"
                "Summary (in bullet points):"
            )
            try:
                response = model.generate_content(prompt)
                all_summaries.append(response.text)
            except Exception as e:
                st.error(f"Error summarizing chunk {i+1}: {e}")
                all_summaries.append(f"• Error during summarization for chunk {i+1}.")

        st.session_state.document_summary = "\n\n".join(all_summaries)

# Display Summary
if st.session_state.document_summary:
    st.subheader("✅ Document Summary")
    st.markdown(st.session_state.document_summary)
    st.info("You can now ask questions about the document below.")


# --- Chat Interface ---
if st.session_state.document_text and api_key:
    st.subheader("💬 Chat with the Document")
    
    if not st.session_state.messages:
        st.session_state.messages.append({
            "role": "assistant",
            "content": "I have read the document. How can I help you?"
        })

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Ask a question about your document..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                chat_prompt = (
                    "Based on the following document content, answer the user's question. "
                    "If the information is not explicitly available in the document, state that you cannot answer based on the provided text. "
                    "Be concise and directly answer the question.\n\n"
                    f"Document Content:\n{clean_text(st.session_state.document_text)}\n\n"
                    f"User Question: {prompt}\n\n"
                    "Answer:"
                )
                try:
                    response = model.generate_content(chat_prompt)
                    response_text = response.text
                except Exception as e:
                    response_text = f"An error occurred: {e}"

                st.markdown(response_text)
        
        st.session_state.messages.append({"role": "assistant", "content": response_text})