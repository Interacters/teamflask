
"""
Gemini API for handling requests to the Gemini language model.
Supports text analysis, citation checking, and other AI-powered features.

Example frontend JavaScript code for reference:
const API_KEY = " YOUR_GEMINI_API_KEY_HERE ";
const ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key=${API_KEY}`;
fetch(ENDPOINT, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        contents: [{
            parts: [{ text: `Please look at this text for correct academic citations, and recommend APA references for each area of concern: ${text}` }]
        }]
    })
});
"""
from __init__ import app
from flask import Blueprint, request, jsonify, current_app, g
from flask_restful import Api, Resource
import requests
from api.jwt_authorize import token_required

gemini_api = Blueprint('gemini_api', __name__, url_prefix='/api')
api = Api(gemini_api)

class GeminiAPI:
    class _Ask(Resource):
        """
        Gemini API Resource to handle requests to the Gemini language model.
        Supports various AI-powered text analysis tasks.
        """
        def post(self):
            """
            Send a request to the Gemini API.
            
            Expected JSON body:
            {
                "text": "Text to analyze",
                "prompt": "Optional custom prompt" (defaults to citation analysis)
            }
            
            Returns:
                JSON response from Gemini API or error message
            """
            current_user = g.current_user
            body = request.get_json()
            
            # Validate request body
            if not body:
                return {'message': 'Request body is required'}, 400
            
            text = body.get('text', '')
            if not text:
                return {'message': 'Text field is required'}, 400
            
            # Get configuration
            api_key = app.config.get('GEMINI_API_KEY')
            server = app.config.get('GEMINI_SERVER')
            
            if not api_key:
                return {'message': 'Gemini API key not configured'}, 500
            
            if not server:
                return {'message': 'Gemini server not configured'}, 500
            
            # Build the endpoint URL
            endpoint = f"{server}?key={api_key}"
            
            # Default prompt for citation analysis, can be overridden
            default_prompt = f"Please look at this text for correct academic citations, and recommend APA references for each area of concern"
            prompt = body.get('prompt', default_prompt)
            
            # Prepare the request payload for Gemini API
            payload = {
                "contents": [{
                    "parts": [{
                        "text": f"{prompt}: {text}"
                    }]
                }]
            }
            
            # Log the request for auditing purposes
            current_app.logger.info(f"User {current_user.uid} made a Gemini API request")
            
            try:
                # Make request to Gemini API
                response = requests.post(
                    endpoint,
                    headers={'Content-Type': 'application/json'},
                    json=payload,
                    timeout=90
                )
                
                # Check if the request was successful
                if response.status_code != 200:
                    current_app.logger.error(f"Gemini API error: {response.status_code}")
                    
                    if response.status_code == 503:
                        return {
                            'message': 'Gemini API is temporarily unavailable (503). Please try again later.',
                            'error_code': 503
                        }, 503
                    elif response.status_code == 429:
                        return {
                            'message': 'Rate limit exceeded. Please try again later.',
                            'error_code': 429
                        }, 429
                    else:
                        return {
                            'message': f'Gemini API error: {response.status_code}',
                            'error_code': response.status_code,
                            'details': response.text
                        }, 500
                
                # Parse the response
                result = response.json()
                
                # Extract the generated text
                try:
                    generated_text = result['candidates'][0]['content']['parts'][0]['text']
                    return {
                        'success': True,
                        'text': generated_text,
                        'user': current_user.uid
                    }
                except (KeyError, IndexError) as e:
                    current_app.logger.error(f"Error parsing Gemini response: {e}")
                    return {
                        'success': False,
                        'message': 'Error parsing Gemini API response',
                        'raw_response': result
                    }, 500
                    
            except requests.RequestException as e:
                current_app.logger.error(f"Error communicating with Gemini API: {e}")
                return {'message': f'Error communicating with Gemini API: {str(e)}'}, 500
            except Exception as e:
                current_app.logger.error(f"Unexpected error in Gemini API: {e}")
                return {'message': f'Unexpected error: {str(e)}'}, 500

    class _MediaBiasChat(Resource):
        """
        Specialized endpoint for media bias game assistance.
        Provides information about news sources without revealing bias classifications.
        Note: Does not require authentication to allow anonymous game play.
        """
        def post(self):
            """
            Handle media bias related queries.
            
            Expected JSON body:
            {
                "query": "User's question about a news source",
                "type": "info" or "hint"
            }
            """
            body = request.get_json()
            
            if not body or 'query' not in body:
                return {'message': 'Query is required'}, 400
            
            query = body.get('query', '').strip()
            query_type = body.get('type', 'info')
            
            # Get configuration
            api_key = app.config.get('GEMINI_API_KEY')
            server = app.config.get('GEMINI_SERVER')
            
            if not api_key or not server:
                return {'message': 'Gemini API not configured'}, 500
            
            endpoint = f"{server}?key={api_key}"
            
            # Create appropriate prompt based on query type
            if query_type == 'hint':
                system_prompt = """You are helping students learn about media literacy by providing hints about news sources. 
                
IMPORTANT RULES:
- Provide helpful hints about how to evaluate the source
- Discuss ownership, funding model, audience, and editorial approach
- DO NOT directly state whether the source is left-leaning, center, or right-leaning
- Focus on objective facts that help students make their own assessment
- Keep hints under 100 words
- Be encouraging and educational

Example good hint: "Consider who owns this organization and how they generate revenue. Think about whether they rely on subscriptions, advertising, or donations, and how that might influence their coverage choices."

Example bad hint: "This source is left-leaning." (Too direct - don't do this!)"""
                
                prompt = f"{system_prompt}\n\nProvide a hint about: {query}"
            else:
                system_prompt = """You are an educational assistant helping students learn about news sources and media literacy.

IMPORTANT RULES:
- Provide factual, neutral information about news organizations
- Include: ownership, founding date, headquarters, funding model, and focus areas
- DO NOT classify sources as left/center/right biased
- DO NOT reveal bias ratings or political leanings
- Focus on verifiable facts that help students evaluate sources themselves
- Keep responses under 150 words
- Be neutral and educational

Example good response: "Reuters is a global news agency founded in 1851, owned by Thomson Reuters Corporation. They operate as a wire service, selling news to other outlets worldwide. Their business model relies on providing accurate, fact-based reporting to maintain credibility with client news organizations."

Example bad response: "Reuters is a center-biased source." (Don't classify bias!)"""
                
                prompt = f"{system_prompt}\n\nProvide information about: {query}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            try:
                response = requests.post(
                    endpoint,
                    headers={'Content-Type': 'application/json'},
                    json=payload,
                    timeout=30
                )
                
                if response.status_code != 200:
                    return {
                        'success': False,
                        'message': f'API error: {response.status_code}'
                    }, response.status_code
                
                result = response.json()
                generated_text = result['candidates'][0]['content']['parts'][0]['text']
                
                return {
                    'success': True,
                    'response': generated_text,
                    'type': query_type
                }
                
            except Exception as e:
                current_app.logger.error(f"Media bias chat error: {e}")
                return {
                    'success': False,
                    'message': str(e)
                }, 500

    class _Health(Resource):
        """
        Health check endpoint for Gemini API integration.
        """
        @token_required()
        def get(self):
            """
            Check if Gemini API is properly configured.
            """
            api_key = app.config.get('GEMINI_API_KEY')
            server = app.config.get('GEMINI_SERVER')
            
            status_info = {
                'gemini_configured': bool(api_key and server),
                'server': server if server else 'Not configured',
                'api_key_present': bool(api_key)
            }
            
            return status_info

    # Register endpoints
    api.add_resource(_Ask, '/gemini')
    api.add_resource(_MediaBiasChat, '/gemini/media-bias-chat')
    api.add_resource(_Health, '/gemini/health')