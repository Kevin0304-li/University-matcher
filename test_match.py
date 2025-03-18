from db import UniversityDatabase
from matcher import UniversityMatcher

# Create the database and matcher
db = UniversityDatabase()
matcher = UniversityMatcher(db)

# Create a sample user profile
user_profile = {
    "gpa": 3.8,
    "sat_score": 1400,
    "preferred_majors": ["Computer Science", "Engineering"],
    "budget": 40000,
    "preferred_locations": ["California", "Massachusetts"],
    "preferred_environment": "Urban"
}

# Create a complete university
complete_uni = {
    "id": 1,
    "name": "Test University",
    "acceptance_rate": 20,
    "tuition_fee": 45000,
    "academic_rank": 15,
    "location": "Boston, MA",
    "climate": "Temperate",
    "environment": "Urban",
    "scholarship_percent": 60,
    "job_placement": 95,
    "diversity_score": 0.85,
    "major_strengths": "Computer Science,Engineering,Business"
}

# Create an incomplete university with missing fields
incomplete_uni = {
    "id": 2,
    "name": "Incomplete University",
    "acceptance_rate": 30,
    "tuition_fee": None,
    "academic_rank": None,
    "location": "San Francisco, CA",
    "environment": "Urban",
    "scholarship_percent": None,
    "job_placement": None,
    "diversity_score": 0.8,
    "major_strengths": None
}

# Test matching with complete university
print("Testing with complete university:")
try:
    score = matcher.calculate_match_score(user_profile, complete_uni)
    print(f"Match score: {score:.2f}")
    
    # Test component scores
    academic = matcher.calculate_academic_match(user_profile, complete_uni)
    financial = matcher.calculate_financial_match(user_profile, complete_uni)
    location = matcher.calculate_location_match(user_profile, complete_uni)
    career = matcher.calculate_career_prospects_match(user_profile, complete_uni)
    campus = matcher.calculate_campus_match(user_profile, complete_uni)
    
    print(f"Academic: {academic:.2f}")
    print(f"Financial: {financial:.2f}")
    print(f"Location: {location:.2f}")
    print(f"Career: {career:.2f}")
    print(f"Campus: {campus:.2f}")
    
except Exception as e:
    print(f"Error with complete university: {e}")

# Test matching with incomplete university
print("\nTesting with incomplete university:")
try:
    score = matcher.calculate_match_score(user_profile, incomplete_uni)
    print(f"Match score: {score:.2f}")
    
    # Test component scores
    academic = matcher.calculate_academic_match(user_profile, incomplete_uni)
    financial = matcher.calculate_financial_match(user_profile, incomplete_uni)
    location = matcher.calculate_location_match(user_profile, incomplete_uni)
    career = matcher.calculate_career_prospects_match(user_profile, incomplete_uni)
    campus = matcher.calculate_campus_match(user_profile, incomplete_uni)
    
    print(f"Academic: {academic:.2f}")
    print(f"Financial: {financial:.2f}")
    print(f"Location: {location:.2f}")
    print(f"Career: {career:.2f}")
    print(f"Campus: {campus:.2f}")
    
except Exception as e:
    print(f"Error with incomplete university: {e}")

print("\nTest completed successfully!") 