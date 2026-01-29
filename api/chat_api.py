from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
import google.generativeai as genai
from __init__ import app
import os

# Create blueprint - let main app handle CORS
chat_api = Blueprint('chat_api', __name__, url_prefix='/api')
api = Api(chat_api)

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

class ChatAPI(Resource):
    def options(self):
        """Handle OPTIONS preflight for CORS"""
        # Return empty response, headers will be added by main app
        return {}, 200
    
    def post(self):
        """Handle chat requests with Gemini API"""
        try:
            data = request.get_json()
            
            if not data or 'message' not in data or 'type' not in data:
                return {"error": "Missing required fields: type and message"}, 400
            
            message = data['message']
            msg_type = data['type']
            
            if not GEMINI_API_KEY:
                return {
                    "error": "Gemini API key not configured",
                    "details": "Please set GEMINI_API_KEY environment variable"
                }, 500
            
            # Prepare prompt based on type
            if msg_type == 'hint':
                prompt = f"""Provide a helpful hint (not the full answer) for this question: {message}. You are helping students learn about media literacy by providing hints about news sources. 
                
IMPORTANT RULES:
- Provide helpful hints about how to evaluate the source
- DO NOT directly state whether the source is left-leaning, center, or right-leaning"""
            else:
                prompt = f"""Provide detailed information about: {message} but do not provide any information about political leanings. Keep messages about 200 characters.
You are an educational assistant helping students learn about news sources and media literacy.

IMPORTANT RULES:
- Provide factual, neutral information about news organizations
- DO NOT classify sources as left/center/right biased/conservative/liberal
- Focus on verifiable facts that help students evaluate sources themselves"""            
            # Call Gemini API
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            response = model.generate_content(prompt)
            
            return {
                "success": True,
                "type": msg_type,
                "question": message,
                "answer": response.text
            }, 200
            
        except Exception as e:
            return {
                "error": "Internal server error",
                "details": str(e)
            }, 500

# Register the resource
api.add_resource(ChatAPI, '/chat')