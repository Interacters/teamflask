import json, os, fcntl
from flask import current_app

# Our 5 static prompts
prompt_list = [
    "What is the political bias of {source}?",
    "Show me recent top stories from {source}",
    "How does {source} compare to other news outlets?",
    "What are the most controversial topics covered by {source}?",
    "Is {source} a reliable news source?"
]

def get_prompts_file():
    """Get the path to prompts.json in the shared data folder"""
    data_folder = current_app.config['DATA_FOLDER']
    return os.path.join(data_folder, 'prompts.json')

def _read_prompts_file():
    """Read prompts from JSON file with file locking"""
    PROMPTS_FILE = get_prompts_file()
    if not os.path.exists(PROMPTS_FILE):
        return []
    with open(PROMPTS_FILE, 'r') as f:
        fcntl.flock(f, fcntl.LOCK_SH)  # Shared lock for reading
        try:
            data = json.load(f)
        except Exception:
            data = []
        fcntl.flock(f, fcntl.LOCK_UN)  # Unlock
    return data

def _write_prompts_file(data):
    """Write prompts to JSON file with exclusive lock"""
    PROMPTS_FILE = get_prompts_file()
    with open(PROMPTS_FILE, 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock for writing
        json.dump(data, f)
        fcntl.flock(f, fcntl.LOCK_UN)

def initPrompts():
    """Initialize prompts.json if it doesn't exist"""
    PROMPTS_FILE = get_prompts_file()
    # Only initialize if file does not exist
    if os.path.exists(PROMPTS_FILE):
        return
    
    prompts_data = []
    for idx, prompt_text in enumerate(prompt_list, start=1):
        prompts_data.append({
            "id": idx,
            "text": prompt_text,
            "clicks": 0
        })
    
    _write_prompts_file(prompts_data)
    print(f"✅ Initialized {len(prompts_data)} prompts")

def getPrompts():
    """Get all prompts"""
    return _read_prompts_file()

def getPrompt(id):
    """Get a single prompt by ID"""
    prompts = _read_prompts_file()
    # Find prompt with matching ID
    for prompt in prompts:
        if prompt['id'] == id:
            return prompt
    return None

def getPromptClicks():
    """Get click counts for all prompts as a dictionary"""
    prompts = _read_prompts_file()
    # Return format: {1: 45, 2: 32, 3: 28, 4: 15, 5: 12}
    return {prompt['id']: prompt['clicks'] for prompt in prompts}

def _increment_prompt_click(id):
    """Atomically increment click count for a prompt"""
    PROMPTS_FILE = get_prompts_file()
    with open(PROMPTS_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
        prompts = json.load(f)
        
        # Find and increment the prompt
        for prompt in prompts:
            if prompt['id'] == id:
                prompt['clicks'] += 1
                break
        
        # Write back to file
        f.seek(0)  # Move to start
        json.dump(prompts, f)
        f.truncate()  # Remove any leftover data
        fcntl.flock(f, fcntl.LOCK_UN)
    
    # Return the updated prompt
    return getPrompt(id)

def countPrompts():
    """Get total number of prompts"""
    prompts = _read_prompts_file()
    return len(prompts)

# For testing
if __name__ == "__main__":
    # This would run if you execute: python prompts.py
    print("Testing prompts system...")
    print(f"Total prompts: {countPrompts()}")
    print(f"All prompts: {getPrompts()}")
    print(f"Click counts: {getPromptClicks()}")