from flask import Blueprint, request, jsonify, current_app
from flask_restful import Api, Resource
import google.generativeai as genai
from __init__ import app
import json
import re
import traceback

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
            print("🎯 Thesis generation request received")
            data = request.get_json()
            print(f"📊 Request data: {data}")
            
            # Validate input
            if not data:
                print("❌ No request body")
                return {'error': 'Request body is required'}, 400
            
            topic = data.get('topic', '').strip()
            position = data.get('position', '').strip()
            
            if not topic or not position:
                print("❌ Missing topic or position")
                return {'error': 'Topic and position are required'}, 400
            
            supporting_points = data.get('supportingPoints', [])
            thesis_type = data.get('thesisType', 'Argumentative')
            audience = data.get('audience', '').strip()
            
            print(f"✅ Input validated - Topic: {topic}, Type: {thesis_type}")
            
            # Get Gemini API key
            api_key = app.config.get('GEMINI_API_KEY')
            if not api_key:
                print("❌ No Gemini API key configured")
                return {'error': 'Gemini API key not configured. Please add GEMINI_API_KEY to your environment variables.'}, 500
            
            print("🔑 Gemini API key found")
            
            # Configure Gemini
            try:
                genai.configure(api_key=api_key)
                print("✅ Gemini configured")
            except Exception as config_error:
                print(f"❌ Gemini configuration error: {config_error}")
                return {'error': f'Failed to configure Gemini: {str(config_error)}'}, 500
            
            # Build the prompt
            prompt = f"""Generate 3 high-quality, human-sounding thesis statements for an essay with the following details:

Topic: {topic}
Position/Argument: {position}
{f"Supporting Points: {', '.join(supporting_points)}" if supporting_points else ''}
Thesis Type: {thesis_type}
{f"Target Audience: {audience}" if audience else ''}

For each thesis statement, provide:
1. The thesis statement itself (clear, concise, and arguable)
2. A strength rating (1-10)
3. A brief explanation of why it's strong or weak
4. 2-3 supporting arguments that could be used
5. 2-3 potential counterarguments to address

Also provide overall recommendations for improving the thesis.

CRITICAL: Respond ONLY with valid JSON. No markdown, no code blocks, no extra text. Use this exact structure:
{{
  "theses": [
    {{
      "statement": "Your thesis statement here",
      "strength": 8,
      "strengthExplanation": "Explanation of strength",
      "supportingArguments": ["Argument 1", "Argument 2", "Argument 3"],
      "counterarguments": ["Counter 1", "Counter 2", "Counter 3"]
    }},
    {{
      "statement": "Second thesis statement",
      "strength": 7,
      "strengthExplanation": "Explanation",
      "supportingArguments": ["Arg 1", "Arg 2", "Arg 3"],
      "counterarguments": ["Counter 1", "Counter 2"]
    }},
    {{
      "statement": "Third thesis statement",
      "strength": 6,
      "strengthExplanation": "Explanation",
      "supportingArguments": ["Arg 1", "Arg 2"],
      "counterarguments": ["Counter 1", "Counter 2"]
    }}
  ],
  "recommendations": "Your recommendations here"
}}"""

            print("📝 Prompt created, calling Gemini API...")
            
            # Call Gemini API with error handling
            try:
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                response = model.generate_content(prompt)
                print(f"✅ Gemini response received ({len(response.text)} chars)")
            except Exception as gemini_error:
                print(f"❌ Gemini API call failed: {gemini_error}")
                traceback.print_exc()
                return {
                    'error': 'Gemini API call failed',
                    'details': str(gemini_error),
                    'message': 'Please check your API key and quota limits'
                }, 500
            
            if not response or not response.text:
                print("❌ Empty response from Gemini")
                return {'error': 'No response from Gemini API'}, 500
            
            # Extract and parse JSON from response
            response_text = response.text.strip()
            print(f"📄 Raw response preview: {response_text[:200]}...")
            
            # Remove markdown code blocks if present
            response_text = re.sub(r'^```json\s*', '', response_text)
            response_text = re.sub(r'^```\s*', '', response_text)
            response_text = re.sub(r'\s*```$', '', response_text)
            response_text = response_text.strip()
            
            # Try to find JSON object in response
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if not json_match:
                print(f"❌ Could not find JSON in response: {response_text[:500]}")
                return {
                    'error': 'Failed to parse response from AI',
                    'details': 'No JSON object found in response',
                    'preview': response_text[:200]
                }, 500
            
            try:
                result = json.loads(json_match.group(0))
                print("✅ JSON parsed successfully")
            except json.JSONDecodeError as parse_error:
                print(f"❌ JSON parse error: {parse_error}")
                print(f"Failed to parse: {json_match.group(0)[:500]}")
                return {
                    'error': 'Failed to parse AI response',
                    'details': str(parse_error)
                }, 500
            
            # Validate the response structure
            if 'theses' not in result or not isinstance(result['theses'], list):
                print(f"❌ Invalid response structure: {result}")
                return {'error': 'Invalid response structure from AI'}, 500
            
            if len(result['theses']) == 0:
                print("❌ No theses in response")
                return {'error': 'AI did not generate any thesis statements'}, 500
            
            print(f"✅ Successfully generated {len(result['theses'])} thesis statements")
            
            return {
                'success': True,
                'data': result
            }, 200
            
        except Exception as e:
            print(f"❌ Unexpected error in thesis generation: {e}")
            traceback.print_exc()
            return {
                'error': 'Internal server error',
                'details': str(e),
                'type': type(e).__name__
            }, 500

class ThesisHealthAPI(Resource):
    def options(self):
        """Handle OPTIONS preflight for CORS"""
        return {}, 200
    
    def get(self):
        """Check if Gemini API is configured"""
        api_key = app.config.get('GEMINI_API_KEY')
        is_configured = bool(api_key)
        
        # Try to actually test the API if configured
        if is_configured:
            try:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-2.5-flash-lite')
                test_response = model.generate_content("Say 'OK' if you can read this.")
                working = bool(test_response and test_response.text)
                
                return {
                    'configured': True,
                    'working': working,
                    'message': 'Gemini API is configured and working' if working else 'Gemini API configured but test failed'
                }
            except Exception as e:
                return {
                    'configured': True,
                    'working': False,
                    'message': f'Gemini API configured but not working: {str(e)}'
                }
        else:
            return {
                'configured': False,
                'working': False,
                'message': 'Gemini API key not found in environment variables'
            }

# Register endpoints
api.add_resource(ThesisGeneratorAPI, '/thesis/generate')
api.add_resource(ThesisHealthAPI, '/thesis/health')