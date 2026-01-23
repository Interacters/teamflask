from flask import Blueprint, request, jsonify
from flask_login import current_user, login_required
import google.generativeai as genai
import os
from model.performance import Performance
from __init__ import db

bias_analysis_api = Blueprint('bias_analysis_api', __name__, url_prefix='/api')

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@bias_analysis_api.route('/analyze-bias/<string:uid>', methods=['POST'])
@login_required
def analyze_bias(uid):
    """Analyze user's media literacy performance and biases"""
    try:
        # Verify the user is analyzing their own data or is an admin
        if current_user._uid != uid and current_user.role != 'Admin':
            return jsonify({'error': 'Unauthorized'}), 403
        
        # Get frontend data from request
        frontend_data = request.get_json() or {}
        
        # Get backend data from database
        from model.user import User
        user = User.query.filter_by(_uid=uid).first()
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get performance ratings
        performances = Performance.query.filter_by(user_id=user.id).all()
        performance_data = [
            {
                'rating': perf.rating,
                'timestamp': perf.timestamp.isoformat()
            }
            for perf in performances
        ]
        
        # Get media scores from the media_api
        from api.media_api import MediaScore
        media_scores = MediaScore.query.filter_by(username=uid).all()
        media_data = [
            {
                'time': score.time,
                'timestamp': score.timestamp.isoformat()
            }
            for score in media_scores
        ]
        
        # Combine all data
        combined_data = {
            'user_info': {
                'uid': user._uid,
                'name': user._name,
                'role': user._role
            },
            'performance_ratings': performance_data,
            'media_game_scores': media_data,
            'frontend_activity': frontend_data
        }
        
        # Create the prompt for Gemini
        analysis_prompt = create_analysis_prompt(combined_data)
        
        # Call Gemini API
        if not GEMINI_API_KEY:
            return jsonify({
                'error': 'Gemini API key not configured'
            }), 500
        
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(analysis_prompt)
        
        # Parse Gemini's response
        analysis = parse_gemini_response(response.text)
        
        return jsonify({
            'success': True,
            'user': uid,
            'analysis': analysis
        }), 200
        
    except Exception as e:
        print(f"Error in bias analysis: {str(e)}")
        return jsonify({
            'error': 'Analysis failed',
            'details': str(e)
        }), 500

def create_analysis_prompt(data):
    """Create a detailed prompt for Gemini analysis"""
    
    # Calculate some basic stats
    avg_performance = 0
    if data['performance_ratings']:
        ratings = [p['rating'] for p in data['performance_ratings']]
        avg_performance = sum(ratings) / len(ratings)
    
    avg_game_time = 0
    if data['media_game_scores']:
        times = [s['time'] for s in data['media_game_scores']]
        avg_game_time = sum(times) / len(times) if times else 0
    
    prompt = f"""You are an educational AI assistant analyzing a student's media literacy performance data. 

STUDENT PROFILE:
- Username: {data['user_info']['uid']}
- Name: {data['user_info']['name']}
- Role: {data['user_info']['role']}

PERFORMANCE DATA:
- Self-assessment ratings: {len(data['performance_ratings'])} submissions
- Average rating: {avg_performance:.1f}/5
- Detailed ratings: {data['performance_ratings']}

MEDIA BIAS GAME DATA:
- Game completions: {len(data['media_game_scores'])}
- Average completion time: {avg_game_time:.0f} seconds
- Detailed scores: {data['media_game_scores']}

FRONTEND ACTIVITY DATA:
- Game AI prompts used: {data['frontend_activity'].get('game_prompts', [])}
- Citations created: {data['frontend_activity'].get('citation_count', 0)}
- Citation formats used: {data['frontend_activity'].get('citation_formats', {})}
- Works cited list created: {data['frontend_activity'].get('has_works_cited', False)}
- AI chat messages: {data['frontend_activity'].get('chat_messages', 0)}
- Sample chat questions: {data['frontend_activity'].get('chat_questions', [])}
- Thesis statements generated: {data['frontend_activity'].get('thesis_count', 0)}
- Thesis topics explored: {data['frontend_activity'].get('thesis_topics', [])}

Please provide a comprehensive analysis in the following JSON format:

{{
    "bias_likelihood": <number 1-10>,
    "bias_explanation": "<2-3 sentences explaining their bias awareness based on game performance>",
    
    "knowledge_score": <number 1-10>,
    "knowledge_explanation": "<2-3 sentences about their overall media literacy knowledge>",
    
    "learning_patterns": {{
        "strengths": ["<strength 1>", "<strength 2>", "<strength 3>"],
        "weaknesses": ["<weakness 1>", "<weakness 2>"]
    }},
    
    "personalized_insights": {{
        "left_leaning_tendencies": <number 0-10>,
        "center_preference": <number 0-10>,
        "right_leaning_tendencies": <number 0-10>,
        "explanation": "<2-3 sentences about their political awareness exposure>"
    }},
    
    "recommendations": [
        "<specific actionable recommendation 1>",
        "<specific actionable recommendation 2>",
        "<specific actionable recommendation 3>"
    ],
    
    "interesting_observation": "<1-2 sentences about something unique or noteworthy in their data>"
}}

IMPORTANT: Respond ONLY with valid JSON. Do not include any markdown formatting, code blocks, or additional text."""

    return prompt

def parse_gemini_response(response_text):
    """Parse Gemini's JSON response"""
    import json
    
    # Remove any markdown code blocks if present
    cleaned = response_text.strip()
    if cleaned.startswith('```json'):
        cleaned = cleaned[7:]
    if cleaned.startswith('```'):
        cleaned = cleaned[3:]
    if cleaned.endswith('```'):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fallback response if parsing fails
        return {
            "bias_likelihood": 5,
            "bias_explanation": "Unable to fully analyze bias patterns from available data.",
            "knowledge_score": 5,
            "knowledge_explanation": "Moderate engagement with media literacy concepts observed.",
            "learning_patterns": {
                "strengths": ["Active participation", "Tool engagement"],
                "weaknesses": ["Limited data available"]
            },
            "personalized_insights": {
                "left_leaning_tendencies": 5,
                "center_preference": 5,
                "right_leaning_tendencies": 5,
                "explanation": "Insufficient data to determine political exposure patterns."
            },
            "recommendations": [
                "Complete more activities for better analysis",
                "Use the AI chat feature more frequently",
                "Practice with diverse news sources"
            ],
            "interesting_observation": "Continue engaging with the learning materials for deeper insights."
        }