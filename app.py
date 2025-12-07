# Refactored: Use CRUD naming (read, create) in InfoModel
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restful import Api, Resource
import os
import google.generativeai as genai

# --- Mood model + routes ---
from model.mood import db
from api.mood_routes import MoodSubmit, MoodSummary

app = Flask(__name__)
CORS(app, supports_credentials=True, origins='*')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///moods.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

api = Api(app)
api.add_resource(MoodSubmit, "/submit-mood")
api.add_resource(MoodSummary, "/mood-summary")

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

# --- NEW: Chat API Resource with Gemini ---
class ChatAPI(Resource):
    def post(self):
        try:
            data = request.get_json()
            
            # Validate input
            if not data or 'message' not in data or 'type' not in data:
                return {"error": "Missing required fields: type and message"}, 400
            
            message = data['message']
            msg_type = data['type']
            
            print(f"Received {msg_type} request: {message}")
            
            # Check if API key is configured
            if not GEMINI_API_KEY:
                return {
                    "error": "Gemini API key not configured",
                    "details": "Please set GEMINI_API_KEY environment variable"
                }, 500
            
            # Prepare prompt based on type
            if msg_type == 'hint':
                prompt = f"Provide a helpful hint (not the full answer) for this question: {message}"
            else:
                prompt = f"Provide detailed information about: {message}"
            
            # Call Gemini API
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            
            # Extract the text from response
            ai_response = response.text
            
            # Send response back to frontend
            return {
                "success": True,
                "type": msg_type,
                "question": message,
                "answer": ai_response
            }, 200
            
        except Exception as e:
            print(f"Error in ChatAPI: {str(e)}")
            return {
                "error": "Internal server error",
                "details": str(e)
            }, 500

api.add_resource(ChatAPI, '/api/chat')

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
    app.run(port=5001)

"""
SETUP INSTRUCTIONS:

1. Install Gemini SDK:
   pip install google-generativeai

2. Set your Gemini API key:
   - Get your key from: https://makersuite.google.com/app/apikey
   - Windows: set GEMINI_API_KEY=your_key_here
   - Mac/Linux: export GEMINI_API_KEY=your_key_here

3. Run the server:
   python app.py

4. Update your frontend HTML to use port 5001:
   Change: const backendUrl = 'http://localhost:5001/api/chat';
"""