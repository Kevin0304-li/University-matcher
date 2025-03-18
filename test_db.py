import os
from db import UniversityDatabase

# Delete existing database file if it exists
if os.path.exists("universities.db"):
    print("Removing existing database...")
    os.remove("universities.db")

# Create the database and insert sample data
print("Creating new database with updated schema...")
db = UniversityDatabase()
db.insert_sample_data()

# Get all universities
universities = db.get_all_universities()
print(f"Created {len(universities)} universities")

# Get unique university types
university_types = set(u.get('university_type', '') for u in universities if 'university_type' in u)
print("University types:", sorted(university_types))

# Get unique regions
regions = set(u.get('region', '') for u in universities if 'region' in u)
print("Regions:", sorted(regions))

# Get unique countries
countries = set(u.get('country', '') for u in universities if 'country' in u)
print("Countries:", sorted(countries))

# Get unique campus sizes
campus_sizes = set(u.get('campus_size', '') for u in universities if 'campus_size' in u)
print("Campus sizes:", sorted(campus_sizes))

# Print the first university to check structure
first_uni = universities[0]
print("\nSample university:")
for key, value in first_uni.items():
    print(f"{key}: {value}") 