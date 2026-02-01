import json, os, fcntl
from flask import current_app
from flask_restful import Resource

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
            "clicks": 0,
            # ✅ NEW: Track effectiveness
            "effectiveness": {
                "successful_completions": 0,
                "total_uses": 0,
                "success_rate": 0.0
            },
            # ✅ NEW: Track usage by section
            "usage_by_section": {
                "media_bias": 0,
                "thesis_gen": 0,
                "citations": 0
            },
            # ✅ NEW: Track unique users who clicked
            "unique_users": [],
            # ✅ NEW: Recent activity
            "last_clicked": None,
            "trending_score": 0
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

def increment_prompt_click(id, user_id=None, section=None, led_to_success=None):
    """
    ALGORITHM: Track prompt effectiveness across multiple dimensions
    INPUT: id (int), user_id (str), section (str), led_to_success (bool)
    OUTPUT: Updated prompt object (dict)
    DATA STRUCTURES: List of prompt dictionaries
    
    DEMONSTRATES:
    - SEQUENCING: Multiple steps in specific order
    - SELECTION: Conditional logic based on parameters
    - ITERATION: Loop through prompts list
    """
    from datetime import datetime
    
    PROMPTS_FILE = get_prompts_file()
    with open(PROMPTS_FILE, 'r+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        prompts = json.load(f)
        
        # ITERATION: Loop through list
        for prompt in prompts:
            # SELECTION: Find matching prompt
            if prompt['id'] == id:
                # SEQUENCING: Execute steps in order
                
                # Step 1: Increment basic click counter
                prompt['clicks'] += 1
                
                # Step 2: Track unique users (LIST manipulation)
                if user_id and user_id not in prompt.get('unique_users', []):
                    if 'unique_users' not in prompt:
                        prompt['unique_users'] = []
                    prompt['unique_users'].append(user_id)
                
                # Step 3: Track by section (DICTIONARY manipulation)
                if section:
                    if 'usage_by_section' not in prompt:
                        prompt['usage_by_section'] = {
                            "media_bias": 0,
                            "thesis_gen": 0,
                            "citations": 0
                        }
                    if section in prompt['usage_by_section']:
                        prompt['usage_by_section'][section] += 1
                
                # Step 4: Track effectiveness (ALGORITHM)
                if led_to_success is not None:
                    if 'effectiveness' not in prompt:
                        prompt['effectiveness'] = {
                            "successful_completions": 0,
                            "total_uses": 0,
                            "success_rate": 0.0
                        }
                    
                    # SELECTION: Update based on outcome
                    prompt['effectiveness']['total_uses'] += 1
                    if led_to_success:
                        prompt['effectiveness']['successful_completions'] += 1
                    
                    # CALCULATE: Derive success rate
                    total = prompt['effectiveness']['total_uses']
                    successes = prompt['effectiveness']['successful_completions']
                    prompt['effectiveness']['success_rate'] = successes / total if total > 0 else 0
                
                # Step 5: Update timestamp
                prompt['last_clicked'] = datetime.now().isoformat()
                
                # Step 6: Calculate trending score (recent activity matters more)
                hours_since_click = 0  # Just clicked
                time_decay = max(0, 1 - (hours_since_click / 24))  # Decay over 24 hours
                prompt['trending_score'] = prompt['clicks'] * time_decay
                
                break  # Exit loop once found
        
        # Write back to file
        f.seek(0)
        json.dump(prompts, f, indent=4)
        f.truncate()
        fcntl.flock(f, fcntl.LOCK_UN)
    
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

    class PromptsAPI:
    
    # ... your existing code ...
    
    # Add this new class for OPTIONS requests
        class _Options(Resource):
            def options(self, id=None):
                return '', 204
    
    # Register the OPTIONS handler for all routes that need it
    api.add_resource(_Read, '', '/')
    api.add_resource(_ReadClicks, '/clicks', '/clicks/')
    api.add_resource(_ReadID, '/<int:id>', '/<int:id>/')
    api.add_resource(_IncrementClick, '/<int:id>/click', '/<int:id>/click/')
    api.add_resource(_ReadCount, '/count', '/count/')
    
    # Add OPTIONS for the click endpoint specifically
    api.add_resource(_Options, '/<int:id>/click/options')