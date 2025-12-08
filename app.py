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
         "origins": ["http://localhost:4600", "http://127.0.0.1:4600"],
         "methods": ["GET", "POST", "OPTIONS"],
         "allow_headers": ["Content-Type", "Authorization"],
         "expose_headers": ["Content-Type"],
         "supports_credentials": True
     }})

# Add explicit preflight handling
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers['Access-Control-Allow-Origin'] = request.headers.get('Origin', '*')
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Max-Age'] = '3600'
        return response

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:4600', 'http://127.0.0.1:4600']:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
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