# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource
from flask_sqlalchemy import SQLAlchemy
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Mood model + routes (commented out) ---
# from model.mood import db
# from api.mood_routes import MoodSubmit, MoodSummary
db = SQLAlchemy()

app = Flask(__name__)

# Enhanced CORS configuration
CORS(app, 
     resources={r"/*": {
         "origins": "*",
         "methods": ["GET", "POST", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"],
         "expose_headers": ["Content-Type"],
         "supports_credentials": False
     }})

# Add after_request to ensure CORS headers are always present
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moods.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

api = Api(app)
# api.add_resource(MoodSubmit, "/submit-mood")
# api.add_resource(MoodSummary, "/mood-summary")

# --- Configure Gemini API ---
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("WARNING: GEMINI_API_KEY environment variable not set!")

# --- Model class for InfoDb with CRUD naming ---
class InfoModel:
    def __init__(self):
        self.data = [
            {
                "FirstName": "John",
                "LastName": "Mortensen",
                "DOB": "October 21",
                "Residence": "San Diego",
                "Email": "jmortensen@powayusd.com",
                "Owns_Cars": ["2015-Fusion", "2011-Ranger", "2003-Excursion", "1997-F350", "1969-Cadillac", "2015-Kuboto-3301"]
            },
            {
                "FirstName": "Shane",
                "LastName": "Lopez",
                "DOB": "February 27",
                "Residence": "San Diego",
                "Email": "slopez@powayusd.com",
                "Owns_Cars": ["2021-Insight"]
            }
        ]

    def read(self):
        return self.data

    def create(self, entry):
        self.data.append(entry)

# Instantiate the model
info_model = InfoModel()

# --- API Resource for InfoDb ---
class DataAPI(Resource):
    def get(self):
        return jsonify(info_model.read())

    def post(self):
        # Add a new entry to InfoDb
        entry = request.get_json()
        if not entry:
            return {"error": "No data provided"}, 400
        info_model.create(entry)
        return {"message": "Entry added successfully", "entry": entry}, 201

api.add_resource(DataAPI, '/api/data')

# --- Chat endpoint with proper CORS handling ---
@app.route('/api/chat', methods=['POST', 'OPTIONS'])
def chat_endpoint():
    # Handle OPTIONS preflight request
    if request.method == 'OPTIONS':
        return '', 200
    
    try:
        data = request.get_json()
        
        # Validate input
        if not data or 'message' not in data or 'type' not in data:
            return jsonify({"error": "Missing required fields: type and message"}), 400
        
        message = data['message']
        msg_type = data['type']
        
        print(f"Received {msg_type} request: {message}")
        
        # Check if API key is configured
        if not GEMINI_API_KEY:
            return jsonify({
                "error": "Gemini API key not configured",
                "details": "Please set GEMINI_API_KEY environment variable"
            }), 500
        
        # Prepare prompt based on type
        if msg_type == 'hint':
            prompt = f"Provide a helpful hint (not the full answer) for this question: {message}"
        else:
            prompt = f"Provide detailed information about: {message}"
        
        # Call Gemini API with Gemini 1.5 Flash (higher free tier limits)
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
        
        # Extract the text from response
        ai_response = response.text
        
        # Send response back to frontend
        return jsonify({
            "success": True,
            "type": msg_type,
            "question": message,
            "answer": ai_response
        }), 200
        
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "error": "Internal server error",
            "details": str(e)
        }), 500

# We can use @app.route for HTML endpoints, this will be style for Admin UI
@app.route('/')
def say_hello():
    html_content = """
    <html>
    <head>
        <title>Hello</title>
    </head>
    <body>
        <h2>Hello, World!</h2>
    </body>
    </html>
    """
    return html_content

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8001, debug=True)

"""
SETUP INSTRUCTIONS:

1. Install dependencies:
   pip install python-dotenv google-generativeai flask flask-cors flask-restful

2. Create .env file with:
   GEMINI_API_KEY=your_key_here

3. Run the server:
   python app.py

4. Your frontend is already configured for port 8001!
"""