from flask import Blueprint, request, jsonify
from flask_restful import Api, Resource
import json
import os
from datetime import datetime

chat_history_api = Blueprint('chat_history_api', __name__, url_prefix='/api')
api = Api(chat_history_api)

# In-memory storage (use database in production)
conversation_sessions = {}

class ChatHistoryAPI(Resource):
    """
    CRUD operations for chat history
    DEMONSTRATES: List/Dictionary manipulation, algorithm
    """
    
    def get(self, user_id=None):
        """
        READ: Get chat history
        INPUT: user_id (optional)
        OUTPUT: List of conversation messages
        DATA STRUCTURE: Dictionary of lists
        """
        if user_id:
            # Get specific user's history
            history = conversation_sessions.get(user_id, [])
            return jsonify({
                'user_id': user_id,
                'messages': history,
                'count': len(history)
            })
        else:
            # Get all users' chat counts
            summary = {
                uid: len(msgs) 
                for uid, msgs in conversation_sessions.items()
            }
            return jsonify(summary)
    
    def post(self):
        """
        CREATE: Save chat message
        INPUT: JSON with user_id, question, answer, type
        OUTPUT: Confirmation with updated count
        ALGORITHM: Append to list, calculate stats
        """
        data = request.get_json()
        
        user_id = data.get('user_id', 'Guest')
        question = data.get('question')
        answer = data.get('answer')
        msg_type = data.get('type', 'hint')
        
        # Initialize list if needed
        if user_id not in conversation_sessions:
            conversation_sessions[user_id] = []
        
        # Create message object
        message = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'answer': answer[:200],  # Truncate long answers
            'type': msg_type
        }
        
        # APPEND to list (demonstrates list manipulation)
        conversation_sessions[user_id].append(message)
        
        return jsonify({
            'saved': True,
            'message_count': len(conversation_sessions[user_id]),
            'user_id': user_id
        }), 201
    
    def delete(self, user_id):
        """
        DELETE: Clear user's chat history
        INPUT: user_id
        OUTPUT: Confirmation
        """
        if user_id in conversation_sessions:
            count = len(conversation_sessions[user_id])
            conversation_sessions[user_id] = []
            return jsonify({
                'cleared': True,
                'messages_deleted': count
            })
        return jsonify({'error': 'User not found'}), 404

# Register routes
api.add_resource(ChatHistoryAPI, 
    '/chat-history',           # GET all users' summary
    '/chat-history/',
    '/chat-history/<user_id>', # GET/DELETE specific user
    '/chat-history/<user_id>/'
)