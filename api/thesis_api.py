from flask import Blueprint, request, jsonify, current_app
from flask_restful import Api, Resource
import google.generativeai as genai
from __init__ import app
import json
import re

# Create blueprint - let main app handle CORS
thesis_api = Blueprint('thesis_api', __name__, url_prefix='/api')
api = Api(thesis_api)

class ThesisGeneratorAPI(Resource):
    def options(self):
        """Handle OPTIONS preflight for CORS"""
        # Return empty response, headers will be added by main app
        return {}, 200
    
    def post(self):
        """Generate thesis statements using Gemini API"""
        try:
            data = request.get_json()
            
            # Validate input
            if not data:
                return {'error': 'Request body is required'}, 400
            
            topic = data.get('topic', '').strip()
            position = data.get('position', '').strip()
            
            if not topic or not position:
                return {'error': 'Topic and position are required'}, 400
            
            supporting_points = data.get('supportingPoints', [])
            thesis_type = data.get('thesisType', 'Argumentative')
            audience = data.get('audience', '').strip()
            
            # Get Gemini API key
            api_key = app.config.get('GEMINI_API_KEY')
            if not api_key:
                return {'error': 'Gemini API key not configured'}, 500
            
            # Configure Gemini
            genai.configure(api_key=api_key)
            
            # Build the prompt
            prompt = f"""Generate 3 high-quality, human sounding, thesis statements for an essay with the following details:

Topic: {topic}
Position/Argument: {position}
{f"Supporting Points: {', '.join(supporting_points)}" if supporting_points else ''}
Thesis Type: {thesis_type}
{f"Target Audience: {audience}" if audience else ''}

For each thesis statement, provide:
1. The human-like thesis statement itself, but avoid using very complex language
2. A strength rating (1-10)
3. A brief explanation of why it's strong or weak
4. 2-3 supporting arguments that could be used
5. 2-3 potential counterarguments to address

Also provide overall recommendations for improving the thesis.

IMPORTANT: Respond ONLY with a valid JSON object. Do not include any markdown formatting, backticks, or explanatory text. Use this exact structure:
{{
  "theses": [
    {{
      "statement": "...",
      "strength": 8,
      "strengthExplanation": "...",
      "supportingArguments": ["...", "...", "..."],
      "counterarguments": ["...", "...", "..."]
    }}
  ],
  "recommendations": "..."
}}"""

            # Call Gemini API
            model = genai.GenerativeModel('gemini-2.5-flash-lite')
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                return {'error': 'No response from Gemini API'}, 500
            
            # Extract and parse JSON from response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            
            # Try to find JSON object in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                current_app.logger.error(f"Could not find JSON in response: {response_text}")
                return {'error': 'Failed to parse response from AI'}, 500
            
            result = json.loads(json_match.group(0))
            
            # Validate the response structure
            if 'theses' not in result or not isinstance(result['theses'], list):
                return {'error': 'Invalid response structure from AI'}, 500
            
            return {
                'success': True,
                'data': result
            }, 200
            
        except json.JSONDecodeError as e:
            current_app.logger.error(f"JSON decode error: {e}")
            return {'error': 'Failed to parse AI response', 'details': str(e)}, 500
        except Exception as e:
            current_app.logger.error(f"Error generating thesis: {e}")
            return {'error': 'Internal server error', 'details': str(e)}, 500

class ThesisHealthAPI(Resource):
    def options(self):
        """Handle OPTIONS preflight for CORS"""
        return {}, 200
    
    def get(self):
        """Check if Gemini API is configured"""
        api_key = app.config.get('GEMINI_API_KEY')
        return {
            'configured': bool(api_key),
            'message': 'Gemini API is configured' if api_key else 'Gemini API key not found'
        }

# Register endpoints
api.add_resource(ThesisGeneratorAPI, '/thesis/generate')
api.add_resource(ThesisHealthAPI, '/thesis/health')