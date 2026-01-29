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
    
    # CRITICAL FIX: Always ensure file exists before reading
    if not os.path.exists(PROMPTS_FILE):
        initPrompts()  # Create it if missing
    
    try:
        with open(PROMPTS_FILE, 'r') as f:
            fcntl.flock(f, fcntl.LOCK_SH)  # Shared lock for reading
            try:
                data = json.load(f)
                # Validate data structure
                if not isinstance(data, list):
                    raise ValueError("Invalid data format")
            except (json.JSONDecodeError, ValueError) as e:
                print(f"⚠️  Corrupted prompts.json, reinitializing: {e}")
                data = []
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)  # Unlock
        return data
    except Exception as e:
        print(f"❌ Error reading prompts file: {e}")
        return []

def _write_prompts_file(data):
    """Write prompts to JSON file with exclusive lock"""
    PROMPTS_FILE = get_prompts_file()
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(PROMPTS_FILE), exist_ok=True)
    
    try:
        with open(PROMPTS_FILE, 'w') as f:
            fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock for writing
            json.dump(data, f, indent=2)  # Added indent for readability
            f.flush()  # CRITICAL: Force write to disk
            os.fsync(f.fileno())  # CRITICAL: Ensure OS writes to disk
            fcntl.flock(f, fcntl.LOCK_UN)
        return True
    except Exception as e:
        print(f"❌ Error writing prompts file: {e}")
        return False

def initPrompts():
    """Initialize prompts.json if it doesn't exist or is corrupted"""
    PROMPTS_FILE = get_prompts_file()
    
    # Always reinitialize to ensure clean state
    prompts_data = []
    for idx, prompt_text in enumerate(prompt_list, start=1):
        prompts_data.append({
            "id": idx,
            "text": prompt_text,
            "clicks": 0
        })
    
    success = _write_prompts_file(prompts_data)
    if success:
        print(f"✅ Initialized {len(prompts_data)} prompts in {PROMPTS_FILE}")
    else:
        print(f"❌ Failed to initialize prompts")
    
    return prompts_data

def getPrompts():
    """Get all prompts"""
    prompts = _read_prompts_file()
    
    # If empty or corrupted, reinitialize
    if not prompts or len(prompts) != len(prompt_list):
        print("⚠️  Prompts missing or incomplete, reinitializing...")
        prompts = initPrompts()
    
    return prompts

def getPrompt(id):
    """Get a single prompt by ID"""
    prompts = getPrompts()
    
    # Find prompt with matching ID
    for prompt in prompts:
        if prompt.get('id') == id:
            return prompt
    
    return None

def getPromptClicks():
    """Get click counts for all prompts as a dictionary"""
    prompts = getPrompts()
    
    # Return format: {1: 45, 2: 32, 3: 28, 4: 15, 5: 12}
    clicks_dict = {}
    for prompt in prompts:
        prompt_id = prompt.get('id')
        clicks = prompt.get('clicks', 0)
        if prompt_id is not None:
            clicks_dict[prompt_id] = clicks
    
    return clicks_dict

def increment_prompt_click(id):
    """Atomically increment click count for a prompt"""
    PROMPTS_FILE = get_prompts_file()
    
    # Ensure file exists
    if not os.path.exists(PROMPTS_FILE):
        initPrompts()
    
    updated_prompt = None
    
    try:
        with open(PROMPTS_FILE, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)  # Exclusive lock
            
            try:
                prompts = json.load(f)
                
                # Find and increment the prompt
                found = False
                for prompt in prompts:
                    if prompt.get('id') == id:
                        prompt['clicks'] = prompt.get('clicks', 0) + 1
                        updated_prompt = prompt.copy()
                        found = True
                        print(f"✅ Incremented prompt {id} to {prompt['clicks']} clicks")
                        break
                
                if not found:
                    print(f"⚠️  Prompt ID {id} not found")
                    return None
                
                # Write back to file
                f.seek(0)  # Move to start
                f.truncate()  # Clear file
                json.dump(prompts, f, indent=2)
                f.flush()
                os.fsync(f.fileno())  # Force write
                
            except json.JSONDecodeError as e:
                print(f"❌ Corrupted JSON in increment: {e}")
                return None
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
                
    except Exception as e:
        print(f"❌ Error incrementing click: {e}")
        return None
    
    # Return the updated prompt
    return updated_prompt

def countPrompts():
    """Get total number of prompts"""
    prompts = getPrompts()
    return len(prompts)

# For testing
if __name__ == "__main__":
    # This would run if you execute: python prompts.py
    print("Testing prompts system...")
    print(f"Total prompts: {countPrompts()}")
    print(f"All prompts: {getPrompts()}")
    print(f"Click counts: {getPromptClicks()}")