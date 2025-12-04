from flask_restful import Resource
from flask import request, jsonify
from model.mood import db, Mood

class MoodSubmit(Resource):
    def post(self):
        data = request.get_json()
        mood_value = data.get("mood")

        if mood_value not in ["happy", "sad"]:
            return {"error": "Invalid mood"}, 400

        new_mood = Mood(mood=mood_value)
        db.session.add(new_mood)
        db.session.commit()

        return {"message": "Mood saved"}, 201


class MoodSummary(Resource):
    def get(self):
        happy_count = Mood.query.filter_by(mood="happy").count()
        sad_count = Mood.query.filter_by(mood="sad").count()

        return jsonify({
            "happy": happy_count,
            "sad": sad_count
        })