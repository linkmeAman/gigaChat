from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
import spacy
from app.core.config import settings
import asyncio
from duckduckgo_search import ddg
from typing import Optional

# Load models
tokenizer = None
model = None
nlp = None

def load_models():
    global tokenizer, model, nlp
    
    # Load HuggingFace model and tokenizer
    tokenizer = AutoTokenizer.from_pretrained(settings.MODEL_NAME)
    model = AutoModelForCausalLM.from_pretrained(settings.MODEL_NAME)
    if settings.DEVICE == "cuda" and torch.cuda.is_available():
        model = model.to("cuda")
    
    # Load spaCy model
    nlp = spacy.load("en_core_web_sm")

async def get_web_search_results(query: str) -> Optional[str]:
    """Search the web for additional context."""
    if settings.DUCKDUCKGO_ENABLED:
        try:
            results = ddg(query, max_results=3)
            if results:
                return " ".join([r['body'] for r in results])
        except:
            pass
    return None

async def get_ai_response(input_text: str) -> str:
    """Generate AI response using the loaded model."""
    # Load models if not loaded
    if tokenizer is None:
        load_models()
    
    # Process input with spaCy
    doc = nlp(input_text)
    
    # Get web search results if needed
    web_context = None
    if any(token.text.lower() in ["what", "who", "where", "when", "why", "how"] for token in doc):
        web_context = await get_web_search_results(input_text)
    
    # Prepare prompt with context
    prompt = input_text
    if web_context:
        prompt = f"Context: {web_context}\nQuestion: {input_text}\nAnswer:"
    
    # Generate response
    inputs = tokenizer(prompt, return_tensors="pt")
    if settings.DEVICE == "cuda" and torch.cuda.is_available():
        inputs = inputs.to("cuda")
    
    outputs = model.generate(
        inputs["input_ids"],
        max_length=settings.MAX_LENGTH,
        num_return_sequences=1,
        no_repeat_ngram_size=2,
        temperature=0.7
    )
    
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Clean up response
    if web_context and "Answer:" in response:
        response = response.split("Answer:")[1].strip()
    
    return response