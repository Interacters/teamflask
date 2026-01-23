"""
Database Seeding Script for Users, Performance Ratings, and Media Scores
Run this script to populate your database with test data
Usage: python seed_data.py
"""

from datetime import datetime, timedelta
import random
from __init__ import app, db
from model.user import User, Section
from model.performance import Performance
from api.media_api import MediaScore, MediaPerson

def seed_users():
    """Create fake users"""
    print("\n📝 Creating fake users...")
    
    # Fake user data with fake emails
    fake_users = [
        {"name": "Charlie Brown", "uid": "charlie_brown", "role": "User", "email": "charlie.brown@peanuts.com"},
        {"name": "Lucy van Pelt", "uid": "lucy_van_pelt", "role": "User", "email": "lucy.vanpelt@peanuts.com"},
        {"name": "Linus van Pelt", "uid": "linus_van_pelt", "role": "User", "email": "linus.vanpelt@peanuts.com"},
        {"name": "Snoopy", "uid": "snoopy", "role": "User", "email": "snoopy@doghouse.com"},
        {"name": "Peppermint Patty", "uid": "peppermint_patty", "role": "User", "email": "patty@peanuts.com"},
        {"name": "Marcie", "uid": "marcie", "role": "User", "email": "marcie@peanuts.com"},
        {"name": "Eric Cartman", "uid": "eric_cartman", "role": "User", "email": "cartman@southpark.com"},
        {"name": "Stan Marsh", "uid": "stan_marsh", "role": "User", "email": "stan.marsh@southpark.com"},
        {"name": "Mr. Garrison", "uid": "mr_garrison", "role": "Teacher", "email": "garrison@southpark.edu"},
        {"name": "Kyle Broflovski", "uid": "kyle_broflovski", "role": "User", "email": "kyle.b@southpark.com"},
        {"name": "Kenny McCormick", "uid": "kenny_mccormick", "role": "User", "email": "kenny.m@southpark.com"},
        {"name": "Butters Stotch", "uid": "butters_stotch", "role": "User", "email": "butters@southpark.com"},
        {"name": "Wendy Testaburger", "uid": "wendy_testaburger", "role": "User", "email": "wendy.t@southpark.com"},
        {"name": "Sally Brown", "uid": "sally_brown", "role": "User", "email": "sally.brown@peanuts.com"},
        {"name": "Schroeder", "uid": "schroeder", "role": "User", "email": "schroeder@peanuts.com"}
    ]
    
    # Get sections for assignment
    sections = Section.query.all()
    if not sections:
        print("⚠️  No sections found. Creating default sections...")
        s1 = Section(name='Computer Science A', abbreviation='CSA')
        s2 = Section(name='Computer Science Principles', abbreviation='CSP')
        s3 = Section(name='Computer Science and Software Engineering', abbreviation='CSSE')
        sections = [s1, s2, s3]
        for section in sections:
            section.create()
    
    created_users = []
    
    for user_data in fake_users:
        # Check if user already exists
        existing = User.query.filter_by(_uid=user_data['uid']).first()
        if existing:
            print(f"  ⏭️  User {user_data['uid']} already exists, skipping")
            created_users.append(existing)
            continue
        
        # Create user with only constructor parameters
        user = User(
            name=user_data['name'],
            uid=user_data['uid'],
            password=app.config.get('DEFAULT_PASSWORD', '123toby'),
            role=user_data['role'],
            kasm_server_needed=False,
            sid=f"SID{random.randint(100000, 999999)}",
            school="Test High School"
        )
        
        # Create user with email via dictionary
        created = user.create({
            'email': user_data['email']
        })
        
        if created:
            # Assign 1-3 random sections
            num_sections = random.randint(1, min(3, len(sections)))
            user_sections = random.sample(sections, num_sections)
            for section in user_sections:
                user.add_section(section)
            
            created_users.append(user)
            print(f"  ✅ Created user: {user_data['name']} ({user_data['uid']})")
        else:
            print(f"  ❌ Failed to create user: {user_data['uid']}")
    
    db.session.commit()
    print(f"\n✅ Created {len(created_users)} users")
    return created_users


def seed_performance_ratings(users):
    """Create fake performance ratings"""
    print("\n⭐ Creating fake performance ratings...")
    
    if not users:
        print("  ⚠️  No users available for performance ratings")
        return
    
    # Create 2-5 ratings per user with various timestamps
    created_count = 0
    
    for user in users:
        num_ratings = random.randint(2, 5)
        
        for i in range(num_ratings):
            # Random rating 1-5 (weighted towards 3-5)
            rating = random.choices(
                [1, 2, 3, 4, 5],
                weights=[5, 10, 25, 35, 25]
            )[0]
            
            # Random timestamp in the last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            timestamp = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
            
            # Create performance rating
            perf = Performance(
                rating=rating,
                user_id=user.id,
                timestamp=timestamp
            )
            perf.create()
            created_count += 1
    
    print(f"✅ Created {created_count} performance ratings")


def seed_media_scores():
    """Create fake media bias game scores"""
    print("\n🎮 Creating fake media scores...")
    
    # Fake player names - matching the users created above
    fake_players = [
        "charlie_brown", "lucy_van_pelt", "linus_van_pelt", "snoopy",
        "peppermint_patty", "marcie", "eric_cartman", "stan_marsh",
        "mr_garrison", "kyle_broflovski", "kenny_mccormick", "butters_stotch",
        "wendy_testaburger", "sally_brown", "schroeder"
    ]
    
    created_count = 0
    
    for username in fake_players:
        # Create or get MediaPerson
        person = MediaPerson.query.filter_by(name=username).first()
        if not person:
            person = MediaPerson(name=username)
            person.create()
        
        # Random time between 45 seconds and 5 minutes
        time_seconds = random.randint(45, 300)
        
        # Random timestamp in last 14 days
        days_ago = random.randint(0, 14)
        hours_ago = random.randint(0, 23)
        created_at = datetime.utcnow() - timedelta(days=days_ago, hours=hours_ago)
        
        # Create media score
        score = MediaScore(username=username, time=time_seconds)
        score.created_at = created_at
        score.create()
        created_count += 1
    
    print(f"✅ Created {created_count} media scores")


def main():
    """Main seeding function"""
    print("🌱 Starting database seeding...")
    print("=" * 50)
    print("⚠️  This will ADD test data WITHOUT deleting existing data")
    print("=" * 50)
    
    with app.app_context():
        # Seed in order - only adds new data
        users = seed_users()
        seed_performance_ratings(users)
        seed_media_scores()
        
        print("\n" + "=" * 50)
        print("✅ Database seeding completed successfully!")
        print("\nYou can now view your data in the management dashboard")
        print("Test user credentials:")
        print("  Username: charlie_brown (or any character username)")
        print(f"  Password: {app.config.get('DEFAULT_PASSWORD', '123toby')}")
        print("\n💡 Tip: Run this script multiple times to add more test data")


if __name__ == "__main__":
    main()