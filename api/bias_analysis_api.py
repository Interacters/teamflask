from flask import Blueprint, request, jsonify
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
def analyze_bias(uid):
    """Analyze user's media literacy performance and biases - NO LOGIN REQUIRED"""
    try:
        # Get frontend data from request
        frontend_data = request.get_json() or {}
        
        # Initialize combined_data
        combined_data = {
            'user_info': {
                'uid': uid,
                'name': 'Guest' if uid == 'guest' else uid,
                'role': 'Guest'
            },
            'performance_ratings': [],
            'media_game_scores': [],
            'frontend_activity': frontend_data
        }
        
        # If not guest, try to get backend data from database
        if uid != 'guest':
            try:
                from model.user import User
                user = User.query.filter_by(_uid=uid).first()
                
                if user:
                    combined_data['user_info'] = {
                        'uid': user._uid,
                        'name': user._name,
                        'role': user._role
                    }
                    
                    # Get performance ratings
                    performances = Performance.query.filter_by(user_id=user.id).all()
                    combined_data['performance_ratings'] = [
                        {
                            'rating': perf.rating,
                            'timestamp': perf.timestamp.isoformat()
                        }
                        for perf in performances
                    ]
                    
                    # Get media scores
                    try:
                        from model.media import MediaScore
                        media_scores = MediaScore.query.filter_by(username=uid).all()
                        combined_data['media_game_scores'] = [
                            {
                                'time': score.time,
                                'timestamp': score.timestamp.isoformat()
                            }
                            for score in media_scores
                        ]
                    except Exception as e:
                        print(f"Could not fetch media scores: {e}")
            except Exception as e:
                print(f"Could not fetch user data: {e}")
                # Continue with guest data
        
        # Create the prompt for Gemini
        analysis_prompt = create_analysis_prompt(combined_data)
        
        # Call Gemini API
        if not GEMINI_API_KEY:
            return jsonify({
                'success': True,
                'user': uid,
                'analysis': get_fallback_analysis(combined_data)
            }), 200
        
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
        import traceback
        traceback.print_exc()
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
    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        print(f"Response text: {cleaned}")
        # Fallback response if parsing fails
        return get_fallback_analysis({})

def get_fallback_analysis(data):
    """Fallback analysis when Gemini fails or API key missing"""
    return {
        "bias_likelihood": 5,
        "bias_explanation": "Based on your activity, you show moderate awareness of media bias. Continue exploring diverse sources to strengthen your critical evaluation skills.",
        "knowledge_score": 6,
        "knowledge_explanation": "You've engaged with multiple aspects of media literacy including citation practices and thesis development. Keep building on this foundation.",
        "learning_patterns": {
            "strengths": [
                "Active participation in learning activities",
                "Engagement with citation tools",
                "Use of AI assistance for learning"
            ],
            "weaknesses": [
                "Could benefit from more practice with diverse news sources",
                "Expand critical thinking through varied activities"
            ]
        },
        "personalized_insights": {
            "left_leaning_tendencies": 5,
            "center_preference": 5,
            "right_leaning_tendencies": 5,
            "explanation": "Your current activity doesn't show strong patterns toward any political lean. Continue exposing yourself to sources across the spectrum to develop balanced media literacy."
        },
        "recommendations": [
            "Practice identifying bias in news sources from different political perspectives",
            "Create more thesis statements on controversial topics to practice argumentation",
            "Build a diverse works cited list with sources from across the political spectrum"
        ],
        "interesting_observation": "You're taking important steps in developing media literacy skills. Continue practicing to build confidence in evaluating sources critically."
    }