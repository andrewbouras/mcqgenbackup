import tiktoken
from utils.azure_config import call_azure_api
import io
from PyPDF2 import PdfReader
import json
from models import get_prompt
import logging

def chunk_text(text, max_tokens=3000):
    enc = tiktoken.get_encoding('cl100k_base')
    tokens = enc.encode(text)
    chunks = []
    current_chunk = []
    current_tokens = 0

    for token in tokens:
        current_chunk.append(token)
        current_tokens += 1
        if current_tokens >= max_tokens:
            chunk = enc.decode(current_chunk)
            chunks.append(chunk)
            current_chunk = []
            current_tokens = 0

    if current_chunk:
        chunk = enc.decode(current_chunk)
        chunks.append(chunk)

    return chunks

def extract_statements(text_chunks, config):
    all_statements = []
    prompt_data = get_prompt("extract_statements")
    
    if not prompt_data:
        logging.error("Failed to retrieve prompt data for extract_statements")
        return []
    
    prompt_text = prompt_data.get("regular_prompt", "")
    if not prompt_text:
        logging.error("No prompt text found for extract_statements")
        return []
    
    for chunk in text_chunks:
        prompt = prompt_text.format(chunk=chunk)
        
        response = call_azure_api(prompt, "statement_extraction", config)
        content = response['choices'][0]['message']['content']
        
        logging.debug(f"Raw API response: {content}")
        
        try:
            statements_data = json.loads(content)
            if isinstance(statements_data, dict):
                chunk_statements = statements_data.get("key_statements") or statements_data.get("Statements of information", [])
            elif isinstance(statements_data, list):
                chunk_statements = statements_data
            else:
                chunk_statements = []
                logging.warning(f"Unexpected JSON structure: {statements_data}")
            
            all_statements.extend(chunk_statements)
        except json.JSONDecodeError:
            logging.error(f"Failed to parse API response: {content}")
            # Try to extract statements using regex if JSON parsing fails
            import re
            chunk_statements = re.findall(r'"([^"]*)"', content)
            all_statements.extend(chunk_statements)

        logging.debug(f"Extracted statements: {chunk_statements}")

    # Remove duplicate statements while preserving order
    return list(dict.fromkeys(all_statements))

def extract_text_from_pdf(pdf_bytes):
    pdf_file = io.BytesIO(pdf_bytes)
    reader = PdfReader(pdf_file)
    text = ''
    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + '\n'
    return text
