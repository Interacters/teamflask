from flask import Blueprint, jsonify
from flask_restful import Api, Resource

from hacks.prompts import *

prompt_api = Blueprint('prompt_api', __name__, url_prefix='/api/prompts')

# API generator
api = Api(prompt_api)

class PromptsAPI:
    
    # GET /api/prompts - Get all prompts
    class _Read(Resource):
        def get(self):
            return jsonify(getPrompts())
    
    # GET /api/prompts/clicks - Get click counts as dictionary
    class _ReadClicks(Resource):
        def get(self):
            return jsonify(getPromptClicks())
    
    # GET /api/prompts/<id> - Get single prompt by ID
    class _ReadID(Resource):
        def get(self, id):
            prompt = getPrompt(id)
            if prompt:
                return jsonify(prompt)
            return jsonify({"error": "Prompt not found"}), 404
    
    # POST /api/prompts/<id>/click - Increment click count
    class _IncrementClick(Resource):
        def post(self, id):
            prompt = increment_prompt_click(id)
            if prompt:
                return jsonify(prompt)
            return jsonify({"error": "Prompt not found"}), 404
    
    # GET /api/prompts/count - Get total count
    class _ReadCount(Resource):
        def get(self):
            count = countPrompts()
            return jsonify({'count': count})
    
    # Register routes
    api.add_resource(_Read, '', '/')
    api.add_resource(_ReadClicks, '/clicks', '/clicks/')
    api.add_resource(_ReadID, '/<int:id>', '/<int:id>/')
    api.add_resource(_IncrementClick, '/<int:id>/click', '/<int:id>/click/')
    api.add_resource(_ReadCount, '/count', '/count/')

# For testing
if __name__ == "__main__":
    import requests
    
    server = "http://127.0.0.1:8404"
    url = server + "/api/prompts"
    
    print("Testing Prompts API...")
    
    # Get all prompts
    response = requests.get(url)
    print(f"\nAll prompts: {response.json()}")
    
    # Get click counts
    response = requests.get(url + "/clicks")
    print(f"\nClick counts: {response.json()}")
    
    # Increment prompt 1
    response = requests.post(url + "/1/click")
    print(f"\nAfter clicking prompt 1: {response.json()}")
    
    # Get updated clicks
    response = requests.get(url + "/clicks")
    print(f"\nUpdated counts: {response.json()}")