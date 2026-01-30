from flask import Blueprint, request, jsonify, g
import google.generativeai as genai
import os
from model.performance import Performance
from api.jwt_authorize import token_required

bias_analysis_api = Blueprint('bias_analysis_api', __name__, url_prefix='/api')

# Configure Gemini
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

@bias_analysis_api.route('/analyze-bias/<string:uid>', methods=['POST'])
@token_required()  # ← AUTHENTICATION REQUIRED
def analyze_bias(uid):
    """Analyze user's media literacy performance and biases - LOGIN REQUIRED"""
    try:
        # Get the authenticated user from token_required decorator
        current_user = g.current_user
        
        print(f"🔍 Starting bias analysis for authenticated user: {current_user._uid}")
        print(f"📋 Requested uid: {uid}")
        
        # Security check: users can only analyze their own data (unless admin)
        if current_user.role != 'Admin' and current_user._uid != uid:
            print(f"❌ Permission denied: {current_user._uid} tried to access {uid}'s data")
            return jsonify({
                'error': 'Permission denied',
                'message': 'You can only analyze your own bias profile'
            }), 403
        
        # If admin is requesting someone else's data, get that user
        if current_user.role == 'Admin' and current_user._uid != uid:
            from model.user import User
            target_user = User.query.filter_by(_uid=uid).first()
            if not target_user:
                return jsonify({
                    'error': 'User not found',
                    'message': f'User {uid} does not exist'
                }), 404
            user = target_user
            print(f"👨‍💼 Admin accessing data for user: {uid}")
        else:
            user = current_user
        
        # Get frontend data from request
        frontend_data = request.get_json() or {}
        print(f"📊 Frontend data received: {frontend_data}")
        
        # Initialize combined_data with user info
        combined_data = {
            'user_info': {
                'uid': user._uid,
                'name': user._name,
                'role': user._role
            },
            'performance_ratings': [],
            'media_game_scores': [],
            'frontend_activity': frontend_data
        }
        
        # Get performance ratings from database using your existing model
        try:
            # Use your Performance.list_for_user_id method
            performances = Performance.list_for_user_id(user.id, limit=1000)
            combined_data['performance_ratings'] = [
                {
                    'rating': perf.rating,
                    'timestamp': perf.timestamp.isoformat() if perf.timestamp else None
                }
                for perf in performances
            ]
            print(f"📊 Found {len(performances)} performance ratings for user_id={user.id}")
        except Exception as e:
            print(f"⚠️ Could not fetch performance ratings: {e}")
            import traceback
            traceback.print_exc()
        
        # Get media game scores from database
        try:
            from model.media import MediaScore
            media_scores = MediaScore.query.filter_by(username=user._uid).all()
            combined_data['media_game_scores'] = [
                {
                    'time': score.time,
                    'timestamp': score.timestamp.isoformat() if hasattr(score, 'timestamp') and score.timestamp else None
                }
                for score in media_scores
            ]
            print(f"📊 Found {len(media_scores)} media game scores")
        except ImportError:
            print(f"⚠️ MediaScore model not found - skipping media scores")
        except Exception as e:
            print(f"⚠️ Could not fetch media scores: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"📊 Combined data prepared for {user._uid}")
        print(f"   - Performance ratings: {len(combined_data['performance_ratings'])}")
        print(f"   - Media game scores: {len(combined_data['media_game_scores'])}")
        print(f"   - Frontend citations: {frontend_data.get('citation_count', 0)}")
        print(f"   - Frontend chat messages: {frontend_data.get('chat_messages', 0)}")
        print(f"   - Frontend thesis count: {frontend_data.get('thesis_count', 0)}")
        
        # Create the prompt for Gemini
        analysis_prompt = create_analysis_prompt(combined_data)
        
        # Call Gemini API
        if not GEMINI_API_KEY:
            print("⚠️ No Gemini API key found, using fallback analysis")
            return jsonify({
                'success': True,
                'user': user._uid,
                'analysis': get_fallback_analysis(combined_data)
            }), 200
        
        print("🤖 Calling Gemini API...")
        try:
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(analysis_prompt)
            print(f"✅ Gemini response received ({len(response.text)} chars)")
            
            # Parse Gemini's response
            analysis = parse_gemini_response(response.text)
            print("✅ Analysis parsed successfully")
            
            return jsonify({
                'success': True,
                'user': user._uid,
                'analysis': analysis
            }), 200
        except Exception as gemini_error:
            print(f"⚠️ Gemini API error: {gemini_error}")
            print("⚠️ Falling back to default analysis")
            return jsonify({
                'success': True,
                'user': user._uid,
                'analysis': get_fallback_analysis(combined_data)
            }), 200
        
    except Exception as e:
        print(f"❌ ERROR in bias analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Return a more helpful error response
        return jsonify({
            'error': 'Analysis failed',
            'details': str(e),
            'success': False
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
    
    # Calculate engagement metrics
    total_activities = (
        len(data['performance_ratings']) +
        len(data['media_game_scores']) +
        data['frontend_activity'].get('citation_count', 0) +
        data['frontend_activity'].get('thesis_count', 0) +
        (1 if data['frontend_activity'].get('chat_messages', 0) > 0 else 0)
    )
    
    prompt = f"""You are an educational AI assistant analyzing a student's media literacy performance data. 

STUDENT PROFILE:
- Username: {data['user_info']['uid']}
- Name: {data['user_info']['name']}
- Role: {data['user_info']['role']}

PERFORMANCE DATA (from database):
- Self-assessment ratings: {len(data['performance_ratings'])} submissions
- Average rating: {avg_performance:.1f}/5
- Detailed ratings: {data['performance_ratings']}

MEDIA BIAS GAME DATA (from database):
- Game completions: {len(data['media_game_scores'])}
- Average completion time: {avg_game_time:.0f} seconds
- Detailed scores: {data['media_game_scores']}

CURRENT SESSION ACTIVITY DATA:
- Game AI prompts used: {data['frontend_activity'].get('game_prompts', [])}
- Citations created: {data['frontend_activity'].get('citation_count', 0)}
- Citation formats used: {data['frontend_activity'].get('citation_formats', {})}
- Works cited list created: {data['frontend_activity'].get('has_works_cited', False)}
- AI chat messages: {data['frontend_activity'].get('chat_messages', 0)}
- Sample chat questions: {data['frontend_activity'].get('chat_questions', [])}
- Thesis statements generated: {data['frontend_activity'].get('thesis_count', 0)}
- Thesis topics explored: {data['frontend_activity'].get('thesis_topics', [])}

ENGAGEMENT SUMMARY:
- Total learning activities completed: {total_activities}
- Session engagement level: {"High" if total_activities > 10 else "Medium" if total_activities > 5 else "Low"}

Based on this comprehensive data combining historical performance and current session activity, provide a detailed analysis in the following JSON format:

{{
    "bias_likelihood": <number 1-10, where 1 = highly susceptible to bias, 10 = excellent bias awareness>,
    "bias_explanation": "<2-3 sentences explaining their bias awareness based on game performance and activity patterns>",
    
    "knowledge_score": <number 1-10, based on all activities>,
    "knowledge_explanation": "<2-3 sentences about their overall media literacy knowledge and skill development>",
    
    "learning_patterns": {{
        "strengths": ["<specific strength based on data>", "<another strength>", "<third strength>"],
        "weaknesses": ["<specific area for improvement>", "<another area>"]
    }},
    
    "personalized_insights": {{
        "left_leaning_tendencies": <number 0-10, based on prompts and topics chosen>,
        "center_preference": <number 0-10>,
        "right_leaning_tendencies": <number 0-10>,
        "explanation": "<2-3 sentences about their exposure to different political perspectives and what this indicates about their media diet>"
    }},
    
    "recommendations": [
        "<specific, actionable recommendation based on their weaknesses>",
        "<another specific recommendation>",
        "<third recommendation focused on next steps>"
    ],
    
    "interesting_observation": "<1-2 sentences about a unique pattern, achievement, or noteworthy aspect of their learning journey>"
}}

ANALYSIS GUIDELINES:
- Use specific data points from their history (e.g., "Your {len(data['performance_ratings'])} self-assessments show...")
- Comment on improvement trends if multiple game completions exist
- Acknowledge their engagement level and effort
- Be encouraging but honest about areas needing work
- Make recommendations concrete and achievable

IMPORTANT: Respond ONLY with valid JSON. Do not include any markdown formatting, code blocks, or additional text."""

    return prompt

def parse_gemini_response(response_text):
    """Parse Gemini's JSON response"""
    import json
    
    print(f"🔍 Parsing response ({len(response_text)} chars)...")
    
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
        parsed = json.loads(cleaned)
        print("✅ JSON parsed successfully")
        return parsed
    except json.JSONDecodeError as e:
        print(f"❌ JSON parse error: {e}")
        print(f"Cleaned response preview: {cleaned[:500]}...")
        # Fallback response if parsing fails
        return get_fallback_analysis({})

def get_fallback_analysis(data):
    """Fallback analysis when Gemini fails or API key missing"""
    
    # Try to customize based on available data
    performance_count = len(data.get('performance_ratings', []))
    game_count = len(data.get('media_game_scores', []))
    citation_count = data.get('frontend_activity', {}).get('citation_count', 0)
    thesis_count = data.get('frontend_activity', {}).get('thesis_count', 0)
    chat_messages = data.get('frontend_activity', {}).get('chat_messages', 0)
    
    total_activities = performance_count + game_count + citation_count + thesis_count + (1 if chat_messages > 0 else 0)
    engagement_level = "highly active" if total_activities > 10 else "active" if total_activities > 5 else "engaged"
    
    # Calculate average performance rating if available
    avg_rating = 0
    if performance_count > 0:
        ratings = [p['rating'] for p in data.get('performance_ratings', [])]
        avg_rating = sum(ratings) / len(ratings)
    
    return {
        "bias_likelihood": min(10, max(1, 5 + performance_count)),  # Improves with more practice
        "bias_explanation": f"Based on your {game_count} game completion(s) and {performance_count} self-assessment(s), you're developing bias awareness skills. Your {engagement_level} participation shows commitment to learning media literacy. {'You rated yourself an average of ' + str(round(avg_rating, 1)) + '/5 on preparation.' if avg_rating > 0 else ''}",
        
        "knowledge_score": min(10, max(3, 4 + (total_activities // 3))),  # Scales with activity
        "knowledge_explanation": f"You've engaged with {total_activities} learning activities including {citation_count} citation(s), {thesis_count} thesis statement(s), and {'interactive AI chat sessions' if chat_messages > 0 else 'various tools'}. Your foundation is {'strong' if total_activities > 10 else 'solid'}—continue building on these skills through consistent practice.",
        
        "learning_patterns": {
            "strengths": [
                f"{'Highly active' if total_activities > 10 else 'Active'} participation across multiple learning activities",
                f"Practical application through {'citation tools, thesis generation, and research' if citation_count + thesis_count > 3 else 'hands-on practice'}",
                "Engagement with AI assistance to enhance learning outcomes" if chat_messages > 0 else "Self-directed learning approach"
            ],
            "weaknesses": [
                "Could benefit from more practice identifying bias across diverse news sources" if game_count < 3 else "Consider exploring more controversial topics to challenge your perspectives",
                "Expand critical thinking by analyzing sources from different political perspectives" if citation_count < 5 else "Continue building diverse citation portfolios"
            ]
        },
        
        "personalized_insights": {
            "left_leaning_tendencies": 5,
            "center_preference": 5,
            "right_leaning_tendencies": 5,
            "explanation": f"Your current activity shows balanced exposure across the political spectrum. {'With ' + str(citation_count) + ' citations created, you\'re building awareness of source diversity.' if citation_count > 0 else 'Continue exposing yourself to sources across the political spectrum to develop well-rounded media literacy.'}"
        },
        
        "recommendations": [
            f"Practice the bias game {max(1, 5 - game_count)} more time{'s' if max(1, 5 - game_count) > 1 else ''} to improve your speed and accuracy in identifying media bias",
            f"Create {'more' if thesis_count > 0 else ''} thesis statements on controversial current events to practice balanced argumentation",
            f"Build a diverse works cited list with at least {'one more' if citation_count > 0 else 'three'} source{'s' if citation_count == 0 else ''} from different political perspectives (left, center, right)"
        ],
        
        "interesting_observation": f"You've completed {total_activities} learning activities, showing {'excellent' if total_activities > 15 else 'strong' if total_activities > 8 else 'good'} dedication to developing media literacy skills. {f'Your {performance_count} self-assessments show self-awareness and reflection on your learning progress.' if performance_count > 1 else 'Keep up the momentum and continue tracking your progress!'}"
    }