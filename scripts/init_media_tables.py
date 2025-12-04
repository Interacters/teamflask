#!/usr/bin/env python3
"""
Initialize Media Bias Game Tables

This script creates the media_persons and media_scores tables.

Usage:
    python scripts/init_media_tables.py
"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from __init__ import app, db


def init_media_tables():
    """Initialize the media bias game tables"""
    
    print("=" * 60)
    print("INITIALIZING MEDIA BIAS GAME TABLES")
    print("=" * 60)
    
    with app.app_context():
        # Import models
        from api.media_api import MediaPerson, MediaScore
        
        try:
            # Create tables
            print("\n📦 Creating media tables...")
            db.create_all()
            print("✅ Media tables created successfully!")
            
            # Check existing data
            person_count = MediaPerson.query.count()
            score_count = MediaScore.query.count()
            
            print("\n" + "=" * 60)
            print("INITIALIZATION COMPLETE")
            print("=" * 60)
            print(f"✅ Media Persons: {person_count}")
            print(f"✅ Media Scores: {score_count}")
            print("\n🎉 Media Bias Game database is ready!")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ Error during initialization: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == '__main__':
    print("\n🚀 Media Bias Game Database Initialization Script\n")
    
    try:
        init_media_tables()
    except KeyboardInterrupt:
        print("\n\n⚠️  Initialization cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)