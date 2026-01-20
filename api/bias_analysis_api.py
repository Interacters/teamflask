from flask import Blueprint, jsonify, request
from model.user import User
from model.performance import Performance
from model.media import MediaScore
from model.prompt import PromptClick
import google.generativeai as genai
import os
import json
from datetime import datetime

bias_analysis_api = Blueprint('bias_analysis_api', __name__)

# Configure Gemini API
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

@bias_analysis_api.route('/api/analyze-bias/<username>', methods=['POST'])
def analyze_user_bias(username):
    """
    Aggregate all user data and send to Gemini for bias analysis
    """
    try:
        # Get data from request body (sent from frontend)
        frontend_data = request.json or {}
        
        # Aggregate database data
        user = User.query.filter_by(_uid=username).first()
        if not user:
            return jsonify({"error": "User not found"}), 404
        
        # Get performance ratings
        from model.performance import Performance
        performances = Performance.query.filter_by(user_id=user.id).all()
        performance_ratings = [p.rating for p in performances]
        avg_performance = sum(performance_ratings) / len(performance_ratings) if performance_ratings else 0
        
        # Get game scores
        from model.media import MediaScore
        scores = MediaScore.query.filter_by(username=username).all()
        game_times = [s.time for s in scores]
        best_time = min(game_times) if game_times else None
        
        # Get prompt click patterns
        from model.prompt import PromptClick
        prompt_clicks = PromptClick.query.all()
        click_data = {str(pc.prompt_id): pc.clicks for pc in prompt_clicks}
        
        # Combine all data
        user_data = {
            "username": username,
            "performance": {
                "ratings": performance_ratings,
                "average": round(avg_performance, 2),
                "total_attempts": len(performance_ratings)
            },
            "game": {
                "attempts": len(game_times),
                "best_time": best_time,
                "all_times": game_times,
                "prompts_used": frontend_data.get('game_prompts', [])
            },
            "citations": {
                "total_saved": frontend_data.get('citation_count', 0),
                "formats_used": frontend_data.get('citation_formats', {}),
                "has_works_cited": frontend_data.get('has_works_cited', False)
            },
            "chat": {
                "messages_sent": frontend_data.get('chat_messages', 0),
                "questions_asked": frontend_data.get('chat_questions', [])
            },
            "thesis": {
                "generated": frontend_data.get('thesis_count', 0),
                "topics": frontend_data.get('thesis_topics', [])
            },
            "prompt_clicks": click_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        # Send to Gemini for analysis
        analysis = analyze_with_gemini(user_data)
        
        return jsonify({
            "success": True,
            "analysis": analysis,
            "raw_data": user_data
        })
        
    except Exception as e:
        print(f"Error analyzing bias: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def analyze_with_gemini(user_data):
    """
    Send user data to Gemini API with engineered prompt
    """
    
    # Engineered prompt for bias analysis
    prompt = f"""
You are an educational AI analyzing a student's learning patterns in a media literacy course. Based on the following data, provide a comprehensive bias assessment.

**STUDENT DATA:**
{json.dumps(user_data, indent=2)}

**YOUR TASK:**
Analyze this student's behavior and provide insights in the following JSON structure. Respond ONLY with valid JSON (no markdown, no code fences, no explanations).

{{
  "bias_likelihood": <number 1-10>,
  "bias_explanation": "<2-3 sentences explaining their bias tendencies>",
  
  "knowledge_score": <number 1-10>,
  "knowledge_explanation": "<assessment of their media literacy understanding>",
  
  "learning_patterns": {{
    "strengths": ["<strength 1>", "<strength 2>"],
    "weaknesses": ["<weakness 1>", "<weakness 2>"]
  }},
  
  "personalized_insights": {{
    "left_leaning_tendencies": <number 0-10>,
    "right_leaning_tendencies": <number 0-10>,
    "center_preference": <number 0-10>,
    "explanation": "<why you scored them this way>"
  }},
  
  "recommendations": [
    "<specific actionable advice 1>",
    "<specific actionable advice 2>",
    "<specific actionable advice 3>"
  ],
  
  "interesting_observation": "<one unique insight about this student's learning style>"
}}

**ANALYSIS CRITERIA:**

1. **Bias Likelihood (1-10):**
   - 1-3: Highly aware of bias, actively seeks diverse sources
   - 4-7: Moderate awareness, some blind spots
   - 8-10: Strong bias tendencies, needs intervention

2. **Knowledge Score (1-10):**
   - Based on performance ratings, game completion times, citation usage
   - Consider depth of questions asked, topics explored

3. **Learning Patterns:**
   - Analyze prompt clicks (what sources do they ask about most?)
   - Game times (fast = confident, slow = struggling?)
   - Chat questions (critical thinking vs surface-level?)

4. **Political Leaning Tendencies:**
   - Infer from prompt clicks (if they ask about CNN 10x but never Fox News)
   - Game placements (if they struggled with left sources vs right sources)
   - DON'T make assumptions without data—only analyze what's present

5. **Recommendations:**
   - Must be SPECIFIC (not generic like "read more")
   - Based on actual gaps in their data

**CRITICAL RULES:**
- Respond ONLY with valid JSON (no markdown, no backticks)
- Be honest but constructive
- If data is limited, acknowledge it in explanations
- Never assume demographics—only analyze behavior

Generate the analysis now:
"""
    
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        
        # Parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown code fences if present
        if response_text.startswith('```'):
            lines = response_text.split('\n')
            # Remove first and last lines if they're code fences
            if lines[0].startswith('```'):
                lines = lines[1:]
            if lines[-1].startswith('```'):
                lines = lines[:-1]
            response_text = '\n'.join(lines)
        
        # Remove 'json' language identifier if present
        response_text = response_text.replace('```json', '').replace('```', '').strip()
        
        analysis = json.loads(response_text)
        return analysis
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        print(f"Response text: {response_text}")
        # Return fallback analysis
        return create_fallback_analysis(user_data)
    except Exception as e:
        print(f"Gemini API error: {e}")
        return create_fallback_analysis(user_data)


def create_fallback_analysis(user_data):
    """
    Create a basic analysis when Gemini API fails
    """
    return {
        "bias_likelihood": 5,
        "bias_explanation": "Unable to complete full analysis due to API error. This is a basic assessment based on available data.",
        "knowledge_score": user_data['performance']['average'] if user_data['performance']['average'] > 0 else 5,
        "knowledge_explanation": f"Based on self-reported performance rating of {user_data['performance']['average']}/5.",
        "learning_patterns": {
            "strengths": [
                f"Completed {user_data['game']['attempts']} game attempts" if user_data['game']['attempts'] > 0 else "Getting started with media literacy",
                f"Saved {user_data['citations']['total_saved']} citations" if user_data['citations']['total_saved'] > 0 else "Learning citation formats"
            ],
            "weaknesses": [
                "Continue practicing with diverse news sources",
                "Expand critical thinking skills"
            ]
        },
        "personalized_insights": {
            "left_leaning_tendencies": 5,
            "right_leaning_tendencies": 5,
            "center_preference": 5,
            "explanation": "Insufficient data for detailed political lean analysis. Continue engaging with sources across the spectrum."
        },
        "recommendations": [
            "Complete more activities to generate deeper insights",
            "Try asking the AI chat questions about sources you're unfamiliar with",
            "Practice identifying bias in different citation styles"
        ],
        "interesting_observation": "You're building foundational media literacy skills. Keep exploring!"
    }