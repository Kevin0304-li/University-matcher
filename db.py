import sqlite3
from typing import List, Dict
import datetime
import hashlib
import os
import uuid

class UniversityDatabase:
    def __init__(self, db_name="universities.db"):
        self.conn = sqlite3.connect(db_name, check_same_thread=False)
        self._create_tables()
    
    def _create_tables(self):
        """Creates the necessary tables if they don't exist"""
        # Universities table
        self.conn.execute('''CREATE TABLE IF NOT EXISTS universities
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            acceptance_rate REAL,
            tuition_fee INTEGER,
            academic_rank INTEGER,
            location TEXT,
            climate TEXT,
            environment TEXT,
            scholarship_percent REAL,
            job_placement REAL,
            diversity_score REAL,
            major_strengths TEXT,
            university_type TEXT,
            region TEXT,
            country TEXT,
            year_founded INTEGER,
            student_faculty_ratio TEXT,
            campus_size TEXT,
            religious_affiliation TEXT);''')
        
        # Applications table for detailed admission rate calculation
        self.conn.execute('''CREATE TABLE IF NOT EXISTS applications
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            applicant_id TEXT NOT NULL,
            university_id INTEGER NOT NULL,
            program TEXT NOT NULL,
            status TEXT NOT NULL,
            submission_date TEXT NOT NULL,
            gpa REAL,
            sat_score INTEGER,
            extracurricular_score REAL,
            FOREIGN KEY (university_id) REFERENCES universities(id));''')
            
        # Users table for authentication
        self.conn.execute('''CREATE TABLE IF NOT EXISTS users
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_login TEXT);''')
            
        # User profiles table to store user's academic profiles
        self.conn.execute('''CREATE TABLE IF NOT EXISTS user_profiles
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            profile_name TEXT NOT NULL,
            gpa REAL,
            sat_score INTEGER,
            preferred_majors TEXT,
            budget INTEGER,
            preferred_locations TEXT,
            preferred_environment TEXT,
            preferred_size TEXT,
            preferred_region TEXT,
            preferred_university_type TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id));''')
            
        # Saved recommendations
        self.conn.execute('''CREATE TABLE IF NOT EXISTS saved_recommendations
            (id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            profile_id INTEGER NOT NULL,
            university_id INTEGER NOT NULL,
            match_score REAL,
            notes TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (profile_id) REFERENCES user_profiles(id),
            FOREIGN KEY (university_id) REFERENCES universities(id));''')
            
        self.conn.commit()
    
    def insert_sample_data(self):
        """Inserts sample university data"""
        # First, remove any existing data to avoid duplicates
        self.conn.execute("DELETE FROM universities")
        
        # List of diverse university types
        university_types = ["Public Research", "Private Research", "Liberal Arts", "Technical Institute", 
                           "Community College", "Art School", "Military Academy", "Medical School", 
                           "Business School", "Religious College", "Historically Black", "Women's College"]
        
        # List of regions
        regions = {
            "USA": ["Northeast", "Midwest", "South", "West", "Pacific Northwest", "Southwest", "Mid-Atlantic", "New England"],
            "Canada": ["Eastern", "Western", "Central", "Atlantic", "Northern"],
            "UK": ["England", "Scotland", "Wales", "Northern Ireland"],
            "Australia": ["Eastern", "Western", "Northern", "Southern"],
            "Europe": ["Northern", "Southern", "Eastern", "Western", "Central"],
            "Asia": ["East Asia", "Southeast Asia", "South Asia", "Central Asia"],
        }
        
        # List of environments
        environments = ["Urban", "Suburban", "Rural", "College town", "Coastal", "Mountain", "Resort town"]
        
        # List of campus sizes
        campus_sizes = ["Small (< 5,000 students)", "Medium (5,000-15,000 students)", "Large (15,000-30,000 students)", "Very Large (> 30,000 students)"]
        
        # List of religious affiliations (including None)
        religious_affiliations = [None, "Catholic", "Protestant", "Jewish", "Islamic", "Buddhist", "Hindu", "Inter-denominational"]
        
        # Create 100 diverse universities
        sample_data = []
        
        # Top tier research universities (US)
        sample_data.extend([
            ("MIT", 4, 55000, 1, "Cambridge, MA", "Temperate", "Urban", 85, 97, 0.8, "Computer Science,Engineering,Mathematics,Physics,Robotics", "Private Research", "Northeast", "USA", 1861, "3:1", "Medium (5,000-15,000 students)", None),
            ("Stanford University", 5, 57000, 2, "Stanford, CA", "Mediterranean", "Suburban", 80, 96, 0.9, "Computer Science,Business,Engineering,Medicine,Earth Sciences", "Private Research", "West", "USA", 1885, "4:1", "Medium (5,000-15,000 students)", None),
            ("Harvard University", 4, 54000, 2, "Cambridge, MA", "Temperate", "Urban", 90, 97, 0.85, "Law,Business,Medicine,Political Science,History", "Private Research", "Northeast", "USA", 1636, "6:1", "Medium (5,000-15,000 students)", None),
            ("California Institute of Technology", 7, 58000, 4, "Pasadena, CA", "Mediterranean", "Suburban", 82, 92, 0.68, "Physics,Astronomy,Engineering,Chemistry,Biology", "Private Research", "West", "USA", 1891, "3:1", "Small (< 5,000 students)", None),
            ("Princeton University", 6, 56000, 1, "Princeton, NJ", "Temperate", "Suburban", 92, 98, 0.80, "Mathematics,Physics,Public Policy,Economics,Architecture", "Private Research", "Mid-Atlantic", "USA", 1746, "5:1", "Medium (5,000-15,000 students)", None),
        ])
        
        # Top public universities (US)
        sample_data.extend([
            ("UC Berkeley", 16, 44000, 3, "Berkeley, CA", "Mediterranean", "Urban", 65, 95, 0.9, "Computer Science,Engineering,Business,Environmental Science,Physics", "Public Research", "West", "USA", 1868, "19:1", "Large (15,000-30,000 students)", None),
            ("University of Michigan", 25, 49000, 8, "Ann Arbor, MI", "Continental", "College town", 70, 93, 0.85, "Engineering,Business,Medicine,Social Sciences,Arts", "Public Research", "Midwest", "USA", 1817, "15:1", "Very Large (> 30,000 students)", None),
            ("UCLA", 17, 43000, 6, "Los Angeles, CA", "Mediterranean", "Urban", 68, 90, 0.88, "Film,Psychology,Biology,Business,Engineering", "Public Research", "West", "USA", 1919, "18:1", "Very Large (> 30,000 students)", None),
            ("University of Virginia", 30, 52000, 18, "Charlottesville, VA", "Humid subtropical", "College town", 55, 86, 0.72, "Law,Business,Architecture,Humanities,Medicine", "Public Research", "South", "USA", 1819, "15:1", "Large (15,000-30,000 students)", None),
            ("University of North Carolina", 31, 36000, 15, "Chapel Hill, NC", "Humid subtropical", "College town", 62, 89, 0.75, "Public Health,Journalism,Chemistry,Medicine,Business", "Public Research", "South", "USA", 1789, "13:1", "Large (15,000-30,000 students)", None),
        ])
            
            # Liberal Arts Colleges
        sample_data.extend([
            ("Williams College", 13, 61000, 1, "Williamstown, MA", "Cold continental", "Rural", 88, 92, 0.72, "Economics,Art History,Mathematics,Political Science,Environmental Studies", "Liberal Arts", "Northeast", "USA", 1793, "6:1", "Small (< 5,000 students)", None),
            ("Amherst College", 11, 63000, 2, "Amherst, MA", "Cold continental", "Small town", 90, 93, 0.75, "Liberal Arts,Social Sciences,Humanities,Mathematics,English", "Liberal Arts", "Northeast", "USA", 1821, "7:1", "Small (< 5,000 students)", None),
            ("Swarthmore College", 9, 58000, 3, "Swarthmore, PA", "Temperate", "Suburban", 85, 92, 0.78, "Engineering,Humanities,Social Sciences,Biology,Economics", "Liberal Arts", "Mid-Atlantic", "USA", 1864, "8:1", "Small (< 5,000 students)", "Quaker heritage"),
            ("Pomona College", 8, 57000, 4, "Claremont, CA", "Mediterranean", "Suburban", 82, 91, 0.80, "Mathematics,Economics,Psychology,Biology,Computer Science", "Liberal Arts", "West", "USA", 1887, "7:1", "Small (< 5,000 students)", None),
            ("Wellesley College", 17, 60000, 5, "Wellesley, MA", "Cold continental", "Suburban", 80, 90, 0.76, "Economics,Political Science,Women's Studies,Neuroscience,English", "Women's College", "Northeast", "USA", 1870, "8:1", "Small (< 5,000 students)", None),
        ])
        
        # Technical/Engineering Focused
        sample_data.extend([
            ("Georgia Tech", 20, 36000, 5, "Atlanta, GA", "Humid subtropical", "Urban", 75, 94, 0.8, "Engineering,Computer Science,Architecture,Industrial Design,Business", "Public Research", "South", "USA", 1885, "19:1", "Large (15,000-30,000 students)", None),
            ("Carnegie Mellon University", 15, 58000, 1, "Pittsburgh, PA", "Continental", "Urban", 75, 95, 0.8, "Computer Science,Engineering,Arts,Design,Information Systems", "Private Research", "Mid-Atlantic", "USA", 1900, "10:1", "Medium (5,000-15,000 students)", None),
            ("Rose-Hulman Institute of Technology", 19, 52000, 24, "Terre Haute, IN", "Continental", "Small town", 76, 89, 0.60, "Engineering,Computer Science,Mathematics,Physics,Chemistry", "Technical Institute", "Midwest", "USA", 1874, "11:1", "Small (< 5,000 students)", None),
            ("Colorado School of Mines", 55, 41000, 34, "Golden, CO", "Semi-arid", "Small town", 70, 86, 0.65, "Mining,Petroleum Engineering,Geology,Metallurgy,Environmental Engineering", "Technical Institute", "West", "USA", 1874, "14:1", "Medium (5,000-15,000 students)", None),
            ("Rensselaer Polytechnic Institute", 57, 58000, 42, "Troy, NY", "Cold continental", "Urban", 68, 85, 0.70, "Engineering,Computer Science,Business,Architecture,Game Design", "Technical Institute", "Northeast", "USA", 1824, "13:1", "Medium (5,000-15,000 students)", None),
        ])
            
            # Business-Focused
        sample_data.extend([
            ("Babson College", 26, 55000, 65, "Wellesley, MA", "Cold continental", "Suburban", 72, 88, 0.75, "Entrepreneurship,Business,Management,Finance,Marketing", "Business School", "Northeast", "USA", 1919, "13:1", "Small (< 5,000 students)", None),
            ("Bentley University", 58, 54000, 76, "Waltham, MA", "Cold continental", "Suburban", 65, 86, 0.70, "Accounting,Finance,Marketing,Information Systems,Economics", "Business School", "Northeast", "USA", 1917, "14:1", "Small (< 5,000 students)", None),
            ("Wharton School - UPenn", 10, 61000, 1, "Philadelphia, PA", "Temperate", "Urban", 85, 95, 0.78, "Finance,Management,Marketing,Real Estate,Statistics", "Business School", "Mid-Atlantic", "USA", 1881, "9:1", "Medium (5,000-15,000 students)", None),
            ("NYU Stern", 21, 56000, 4, "New York, NY", "Temperate", "Urban", 70, 86, 0.85, "Finance,Marketing,International Business,Entrepreneurship,Economics", "Business School", "Northeast", "USA", 1900, "10:1", "Large (15,000-30,000 students)", None),
            ("London School of Economics", 18, 28000, 7, "London, UK", "Temperate maritime", "Urban", 68, 88, 0.90, "Economics,Political Science,Sociology,Finance,International Relations", "Public Research", "England", "UK", 1895, "11:1", "Medium (5,000-15,000 students)", None),
        ])
            
            # Art and Design Schools
        sample_data.extend([
            ("Rhode Island School of Design", 24, 55000, 68, "Providence, RI", "Temperate", "Urban", 60, 84, 0.82, "Fine Arts,Graphic Design,Architecture,Industrial Design,Illustration", "Art School", "Northeast", "USA", 1877, "9:1", "Small (< 5,000 students)", None),
            ("Savannah College of Art and Design", 95, 38000, 76, "Savannah, GA", "Humid subtropical", "Urban", 55, 80, 0.78, "Animation,Fashion,Interior Design,Game Design,Film Production", "Art School", "South", "USA", 1978, "20:1", "Medium (5,000-15,000 students)", None),
            ("Parsons School of Design", 35, 50000, 33, "New York, NY", "Temperate", "Urban", 65, 82, 0.85, "Fashion Design,Graphic Design,Interior Design,Architecture,Fine Arts", "Art School", "Northeast", "USA", 1896, "10:1", "Medium (5,000-15,000 students)", None),
            ("California College of the Arts", 85, 49000, 70, "San Francisco, CA", "Mediterranean", "Urban", 60, 81, 0.83, "Fine Arts,Design,Architecture,Writing,Film", "Art School", "West", "USA", 1907, "8:1", "Small (< 5,000 students)", None),
            ("School of the Art Institute of Chicago", 65, 51000, 42, "Chicago, IL", "Continental", "Urban", 58, 83, 0.80, "Fine Arts,Design,Contemporary Practices,Art Education,Art Therapy", "Art School", "Midwest", "USA", 1866, "12:1", "Small (< 5,000 students)", None),
        ])
            
            # Music and Performing Arts
        sample_data.extend([
            ("Juilliard School", 7, 49000, 55, "New York, NY", "Temperate", "Urban", 60, 86, 0.75, "Music Performance,Dance,Drama,Voice,Piano", "Art School", "Northeast", "USA", 1905, "5:1", "Small (< 5,000 students)", None),
            ("Berklee College of Music", 51, 46000, 102, "Boston, MA", "Temperate", "Urban", 55, 82, 0.80, "Music Production,Film Scoring,Music Business,Jazz Performance,Electronic Production", "Art School", "Northeast", "USA", 1945, "8:1", "Small (< 5,000 students)", None),
            ("New England Conservatory", 36, 48000, 87, "Boston, MA", "Temperate", "Urban", 65, 84, 0.72, "Classical Performance,Jazz Studies,Composition,Musicology,Conducting", "Art School", "Northeast", "USA", 1867, "6:1", "Small (< 5,000 students)", None),
            ("Manhattan School of Music", 42, 47000, 95, "New York, NY", "Temperate", "Urban", 62, 83, 0.78, "Classical Performance,Jazz Performance,Musical Theatre,Opera,Conducting", "Art School", "Northeast", "USA", 1917, "5:1", "Small (< 5,000 students)", None),
            ("Royal Academy of Music", 25, 36000, 22, "London, UK", "Temperate maritime", "Urban", 58, 89, 0.70, "Classical Performance,Composition,Conducting,Opera,Historical Performance", "Art School", "England", "UK", 1822, "7:1", "Small (< 5,000 students)", None),
        ])
        
        # Medical Schools and Health Sciences
        sample_data.extend([
            ("Johns Hopkins University", 11, 58000, 10, "Baltimore, MD", "Temperate", "Urban", 80, 94, 0.82, "Medicine,Public Health,Nursing,Biomedical Engineering,Biology", "Private Research", "Mid-Atlantic", "USA", 1876, "7:1", "Medium (5,000-15,000 students)", None),
            ("Mayo Clinic Alix School of Medicine", 2, 55000, 6, "Rochester, MN", "Continental", "Small town", 85, 96, 0.73, "Medicine,Biomedical Research,Surgery,Medical Physics,Health Sciences", "Medical School", "Midwest", "USA", 1972, "2:1", "Small (< 5,000 students)", None),
            ("University of California San Francisco", 4, 38000, 4, "San Francisco, CA", "Mediterranean", "Urban", 68, 95, 0.85, "Medicine,Dentistry,Pharmacy,Nursing,Biological Sciences", "Public Research", "West", "USA", 1864, "4:1", "Small (< 5,000 students)", None),
            ("Karolinska Institute", 10, 9000, 11, "Stockholm, Sweden", "Cold continental", "Urban", 70, 92, 0.76, "Medicine,Biomedical Sciences,Dentistry,Psychology,Nursing", "Medical School", "Northern", "Europe", 1810, "7:1", "Medium (5,000-15,000 students)", None),
            ("Imperial College London Health Sciences", 14, 42000, 9, "London, UK", "Temperate maritime", "Urban", 65, 90, 0.85, "Medicine,Biomedical Engineering,Public Health,Medical Research,Nursing", "Public Research", "England", "UK", 1907, "10:1", "Large (15,000-30,000 students)", None),
        ])
        
        # Historically Black Colleges and Universities (HBCUs)
        sample_data.extend([
            ("Howard University", 39, 31000, 89, "Washington, DC", "Temperate", "Urban", 75, 82, 0.92, "Business,Communications,Medicine,Law,Social Work", "Historically Black", "Mid-Atlantic", "USA", 1867, "13:1", "Medium (5,000-15,000 students)", None),
            ("Spelman College", 41, 29000, 54, "Atlanta, GA", "Humid subtropical", "Urban", 80, 85, 0.96, "Social Sciences,STEM,Psychology,Arts,Humanities", "Women's College", "South", "USA", 1881, "10:1", "Small (< 5,000 students)", None),
            ("Morehouse College", 58, 28000, 122, "Atlanta, GA", "Humid subtropical", "Urban", 78, 84, 0.95, "Business,STEM,Social Sciences,Humanities,Psychology", "Historically Black", "South", "USA", 1867, "13:1", "Small (< 5,000 students)", None),
            ("Florida A&M University", 33, 17000, 117, "Tallahassee, FL", "Humid subtropical", "Urban", 70, 80, 0.95, "Pharmacy,Business,Engineering,Agriculture,Environmental Sciences", "Historically Black", "South", "USA", 1887, "15:1", "Medium (5,000-15,000 students)", None),
            ("Xavier University of Louisiana", 60, 24000, 165, "New Orleans, LA", "Humid subtropical", "Urban", 75, 83, 0.98, "Pharmacy,Sciences,Business,Education,Psychology", "Historically Black", "South", "USA", 1925, "14:1", "Small (< 5,000 students)", "Catholic"),
        ])
        
        # Religious Affiliated
        sample_data.extend([
            ("University of Notre Dame", 19, 58000, 19, "Notre Dame, IN", "Continental", "Suburban", 77, 91, 0.70, "Business,Architecture,Liberal Arts,Engineering,Science", "Private Research", "Midwest", "USA", 1842, "10:1", "Medium (5,000-15,000 students)", "Catholic"),
            ("Brigham Young University", 69, 6000, 80, "Provo, UT", "Semi-arid", "College town", 65, 85, 0.55, "Business,Education,Engineering,Family Sciences,Law", "Private Research", "West", "USA", 1875, "21:1", "Very Large (> 30,000 students)", "Latter-day Saints"),
            ("Yeshiva University", 55, 43000, 97, "New York, NY", "Temperate", "Urban", 72, 80, 0.65, "Jewish Studies,Medical Sciences,Psychology,Business,Education", "Religious College", "Northeast", "USA", 1886, "7:1", "Small (< 5,000 students)", "Jewish"),
            ("Baylor University", 45, 50000, 76, "Waco, TX", "Humid subtropical", "College town", 68, 82, 0.72, "Business,Health Sciences,Education,Law,Social Work", "Private Research", "South", "USA", 1845, "14:1", "Large (15,000-30,000 students)", "Baptist"),
            ("Boston College", 27, 60000, 38, "Chestnut Hill, MA", "Temperate", "Suburban", 75, 88, 0.75, "Business,Education,Social Sciences,Nursing,Theology", "Private Research", "Northeast", "USA", 1863, "13:1", "Medium (5,000-15,000 students)", "Catholic"),
        ])
        
        # International Universities - Global Elite
        sample_data.extend([
            ("University of Oxford", 18, 45000, 4, "Oxford, UK", "Temperate maritime", "College town", 78, 92, 0.85, "Philosophy,Literature,Medicine,Physics,Classics", "Private Research", "England", "UK", 1096, "11:1", "Medium (5,000-15,000 students)", None),
            ("University of Cambridge", 20, 47000, 5, "Cambridge, UK", "Temperate maritime", "College town", 80, 93, 0.83, "Mathematics,Physics,Computer Science,Engineering,Natural Sciences", "Private Research", "England", "UK", 1209, "11:1", "Medium (5,000-15,000 students)", None),
            ("ETH Zurich", 27, 2000, 11, "Zurich, Switzerland", "Temperate continental", "Urban", 75, 92, 0.76, "Engineering,Architecture,Natural Sciences,Computer Science,Materials Science", "Public Research", "Central", "Europe", 1855, "12:1", "Medium (5,000-15,000 students)", None),
            ("University of Tokyo", 34, 8000, 36, "Tokyo, Japan", "Temperate", "Urban", 70, 88, 0.60, "Engineering,Science,Economics,Medicine,Law", "Public Research", "East Asia", "Asia", 1877, "10:1", "Large (15,000-30,000 students)", None),
            ("National University of Singapore", 5, 32000, 22, "Singapore", "Tropical", "Urban", 70, 93, 0.88, "Engineering,Medicine,Business,Computing,Design", "Public Research", "Southeast Asia", "Asia", 1905, "17:1", "Large (15,000-30,000 students)", None),
        ])
        
        # Community Colleges and Affordable Options
        sample_data.extend([
            ("Santa Monica College", 100, 8000, None, "Santa Monica, CA", "Mediterranean", "Urban", 60, 78, 0.85, "Liberal Arts,Business,Computer Science,Design,Film", "Community College", "West", "USA", 1929, "27:1", "Medium (5,000-15,000 students)", None),
            ("Valencia College", 100, 6000, None, "Orlando, FL", "Humid subtropical", "Urban", 65, 80, 0.82, "Engineering,Business,Culinary Arts,Digital Media,Health Sciences", "Community College", "South", "USA", 1967, "26:1", "Large (15,000-30,000 students)", None),
            ("Miami Dade College", 100, 7000, None, "Miami, FL", "Tropical", "Urban", 70, 75, 0.90, "Business,Healthcare,Culinary Arts,Aviation,Hospitality Management", "Community College", "South", "USA", 1960, "21:1", "Very Large (> 30,000 students)", None),
            ("City College of San Francisco", 100, 5000, None, "San Francisco, CA", "Mediterranean", "Urban", 62, 76, 0.88, "Culinary Arts,Computer Science,Nursing,Business,Engineering", "Community College", "West", "USA", 1935, "24:1", "Large (15,000-30,000 students)", None),
            ("Portland Community College", 100, 4500, None, "Portland, OR", "Marine west coast", "Urban", 68, 80, 0.84, "Healthcare,Technology,Arts,Business,Trades", "Community College", "Pacific Northwest", "USA", 1961, "22:1", "Large (15,000-30,000 students)", None),
        ])
        
        # Military Academies
        sample_data.extend([
            ("United States Naval Academy", 8, 0, 22, "Annapolis, MD", "Temperate", "Small town", 100, 95, 0.68, "Engineering,Political Science,Naval Science,Physics,Mathematics", "Military Academy", "Mid-Atlantic", "USA", 1845, "8:1", "Small (< 5,000 students)", None),
            ("United States Military Academy", 9, 0, 18, "West Point, NY", "Temperate", "Rural", 100, 96, 0.70, "Engineering,Military Science,Political Science,Systems Management,History", "Military Academy", "Northeast", "USA", 1802, "7:1", "Small (< 5,000 students)", None),
            ("United States Air Force Academy", 11, 0, 26, "Colorado Springs, CO", "Semi-arid", "Suburban", 100, 94, 0.65, "Aerospace Engineering,Military Strategy,Physics,Computer Science,Political Science", "Military Academy", "West", "USA", 1954, "8:1", "Small (< 5,000 students)", None),
            ("United States Coast Guard Academy", 21, 0, 65, "New London, CT", "Temperate", "Small town", 100, 92, 0.66, "Engineering,Naval Architecture,Management,Government,Science", "Military Academy", "Northeast", "USA", 1876, "7:1", "Small (< 5,000 students)", None),
            ("Virginia Military Institute", 53, 28000, 72, "Lexington, VA", "Humid subtropical", "Small town", 75, 89, 0.64, "Engineering,Computer Science,International Studies,Psychology,History", "Military Academy", "South", "USA", 1839, "11:1", "Small (< 5,000 students)", None),
        ])
        
        # Universities with Unique Programs and Niches
        sample_data.extend([
            ("Deep Springs College", 14, 0, 176, "Deep Springs, CA", "Desert", "Rural", 80, 80, 0.56, "Liberal Arts,Agriculture,Philosophy,Literature,Political Theory", "Liberal Arts", "West", "USA", 1917, "4:1", "Small (< 5,000 students)", None),
            ("Minerva University", 2, 32000, None, "San Francisco, CA", "Mediterranean", "Urban", 70, 85, 0.90, "Computational Sciences,Business,Arts & Humanities,Social Sciences,Natural Sciences", "Private Research", "West", "USA", 2012, "10:1", "Small (< 5,000 students)", None),
            ("Olin College of Engineering", 16, 55000, 32, "Needham, MA", "Temperate", "Suburban", 85, 93, 0.75, "Engineering,Design,Entrepreneurship,Computing,Robotics", "Technical Institute", "Northeast", "USA", 1997, "9:1", "Small (< 5,000 students)", None),
            ("Hampshire College", 63, 50000, None, "Amherst, MA", "Cold continental", "Rural", 70, 75, 0.82, "Interdisciplinary Studies,Film,Media Arts,Social Justice,Sustainability", "Liberal Arts", "Northeast", "USA", 1970, "10:1", "Small (< 5,000 students)", None),
            ("St. John's College", 67, 35000, 53, "Annapolis, MD & Santa Fe, NM", "Varied", "Small town", 75, 77, 0.65, "Great Books,Classics,Philosophy,Mathematics,Languages", "Liberal Arts", "Multiple", "USA", 1696, "7:1", "Small (< 5,000 students)", None),
        ])
        
        # More Regional Universities - US
        sample_data.extend([
            ("Elon University", 78, 39000, 88, "Elon, NC", "Humid subtropical", "Small town", 65, 83, 0.68, "Communications,Business,Education,Law,Health Sciences", "Private Research", "South", "USA", 1889, "12:1", "Medium (5,000-15,000 students)", None),
            ("Butler University", 76, 45000, 96, "Indianapolis, IN", "Continental", "Urban", 62, 81, 0.70, "Pharmacy,Business,Performing Arts,Education,Communication", "Private Research", "Midwest", "USA", 1855, "11:1", "Small (< 5,000 students)", None),
            ("Drake University", 75, 43000, 92, "Des Moines, IA", "Continental", "Urban", 60, 82, 0.65, "Pharmacy,Journalism,Business,Law,Education", "Private Research", "Midwest", "USA", 1881, "10:1", "Small (< 5,000 students)", None),
            ("Gonzaga University", 73, 48000, 79, "Spokane, WA", "Semi-arid", "Urban", 63, 84, 0.68, "Business,Engineering,Education,Nursing,Liberal Arts", "Private Research", "Pacific Northwest", "USA", 1887, "11:1", "Medium (5,000-15,000 students)", "Catholic"),
            ("University of Portland", 77, 49000, 105, "Portland, OR", "Marine west coast", "Urban", 65, 82, 0.72, "Engineering,Nursing,Business,Education,Arts & Sciences", "Private Research", "Pacific Northwest", "USA", 1901, "11:1", "Small (< 5,000 students)", "Catholic"),
        ])
        
        # Canadian Universities
        sample_data.extend([
            ("University of Toronto", 43, 45000, 18, "Toronto, Canada", "Continental", "Urban", 60, 89, 0.90, "Medicine,Business,Computer Science,Engineering,Architecture", "Public Research", "Eastern", "Canada", 1827, "17:1", "Very Large (> 30,000 students)", None),
            ("McGill University", 46, 40000, 27, "Montreal, Canada", "Continental", "Urban", 62, 88, 0.85, "Medicine,Law,Environmental Science,Music,Engineering", "Public Research", "Eastern", "Canada", 1821, "14:1", "Large (15,000-30,000 students)", None),
            ("University of British Columbia", 55, 38000, 34, "Vancouver, Canada", "Temperate coastal", "Urban", 60, 86, 0.87, "Forestry,Earth Sciences,Asian Studies,Medicine,Business", "Public Research", "Western", "Canada", 1908, "18:1", "Very Large (> 30,000 students)", None),
            ("University of Waterloo", 53, 42000, 47, "Waterloo, Canada", "Continental", "College town", 63, 90, 0.75, "Computer Science,Engineering,Mathematics,Environmental Studies,Accounting", "Public Research", "Central", "Canada", 1957, "20:1", "Large (15,000-30,000 students)", None),
            ("Queen's University", 42, 45000, 51, "Kingston, Canada", "Continental", "College town", 58, 87, 0.72, "Business,Engineering,Arts,Health Sciences,Law", "Public Research", "Eastern", "Canada", 1841, "18:1", "Medium (5,000-15,000 students)", None),
        ])
        
        # European Universities (non-UK)
        sample_data.extend([
            ("Technical University of Munich", 45, 2500, 38, "Munich, Germany", "Continental", "Urban", 70, 89, 0.75, "Engineering,Computer Science,Natural Sciences,Medicine,Architecture", "Public Research", "Southern", "Europe", 1868, "12:1", "Large (15,000-30,000 students)", None),
            ("Sorbonne University", 35, 4000, 45, "Paris, France", "Temperate", "Urban", 65, 85, 0.78, "Humanities,Mathematics,Medicine,Law,Sciences", "Public Research", "Western", "Europe", 1257, "19:1", "Very Large (> 30,000 students)", None),
            ("KU Leuven", 55, 3000, 42, "Leuven, Belgium", "Temperate maritime", "College town", 68, 87, 0.80, "Engineering,Medicine,Humanities,Theology,Bioscience", "Public Research", "Western", "Europe", 1425, "15:1", "Large (15,000-30,000 students)", "Catholic"),
            ("Uppsala University", 40, 1500, 60, "Uppsala, Sweden", "Cold continental", "College town", 72, 84, 0.78, "Medicine,Law,Natural Sciences,Social Sciences,Theology", "Public Research", "Northern", "Europe", 1477, "13:1", "Medium (5,000-15,000 students)", None),
            ("University of Amsterdam", 60, 12000, 55, "Amsterdam, Netherlands", "Temperate maritime", "Urban", 65, 86, 0.82, "Economics,Social Sciences,Humanities,Law,Natural Sciences", "Public Research", "Western", "Europe", 1632, "14:1", "Large (15,000-30,000 students)", None),
        ])
        
        # Asian Universities
        sample_data.extend([
            ("Tsinghua University", 2, 16000, 16, "Beijing, China", "Continental", "Urban", 80, 94, 0.62, "Engineering,Computer Science,Business,Architecture,Sciences", "Public Research", "East Asia", "Asia", 1911, "12:1", "Very Large (> 30,000 students)", None),
            ("Seoul National University", 20, 12000, 37, "Seoul, South Korea", "Continental", "Urban", 65, 89, 0.55, "Engineering,Medicine,Business Administration,Social Sciences,Humanities", "Public Research", "East Asia", "Asia", 1946, "16:1", "Large (15,000-30,000 students)", None),
            ("University of Hong Kong", 18, 42000, 39, "Hong Kong", "Subtropical", "Urban", 65, 90, 0.78, "Business,Medicine,Law,Engineering,Social Sciences", "Public Research", "East Asia", "Asia", 1911, "19:1", "Medium (5,000-15,000 students)", None),
            ("Indian Institute of Technology Bombay", 2, 10000, 44, "Mumbai, India", "Tropical", "Urban", 70, 91, 0.58, "Engineering,Technology,Computer Science,Design,Management", "Technical Institute", "South Asia", "Asia", 1958, "10:1", "Medium (5,000-15,000 students)", None),
            ("Nanyang Technological University", 36, 35000, 13, "Singapore", "Tropical", "Urban", 68, 90, 0.85, "Engineering,Business,Education,Science,Art & Design", "Public Research", "Southeast Asia", "Asia", 1991, "14:1", "Large (15,000-30,000 students)", None),
        ])
        
        # Australia/New Zealand Universities
        sample_data.extend([
            ("University of Melbourne", 70, 38000, 33, "Melbourne, Australia", "Temperate", "Urban", 58, 88, 0.82, "Law,Medicine,Fine Arts,Engineering,Business", "Public Research", "Eastern", "Australia", 1853, "14:1", "Very Large (> 30,000 students)", None),
            ("University of Sydney", 65, 36000, 40, "Sydney, Australia", "Temperate", "Urban", 55, 86, 0.82, "Medicine,Architecture,Engineering,Liberal Arts,Veterinary Science", "Public Research", "Eastern", "Australia", 1850, "15:1", "Very Large (> 30,000 students)", None),
            ("Australian National University", 35, 37000, 31, "Canberra, Australia", "Temperate", "Urban", 60, 85, 0.78, "International Relations,Political Science,Physics,Biology,Earth Sciences", "Public Research", "Eastern", "Australia", 1946, "16:1", "Medium (5,000-15,000 students)", None),
            ("University of Auckland", 75, 32000, 81, "Auckland, New Zealand", "Temperate maritime", "Urban", 62, 84, 0.76, "Business,Engineering,Medical Sciences,Law,Arts", "Public Research", "Northern", "Australia", 1883, "18:1", "Large (15,000-30,000 students)", None),
            ("University of Queensland", 80, 35000, 42, "Brisbane, Australia", "Subtropical", "Urban", 65, 85, 0.80, "Life Sciences,Medicine,Engineering,Business,Environmental Science", "Public Research", "Eastern", "Australia", 1909, "18:1", "Very Large (> 30,000 students)", None),
        ])
        
        # Insert all universities
        self.conn.executemany(
            """INSERT OR IGNORE INTO universities 
               (name, acceptance_rate, tuition_fee, academic_rank, location, climate, environment, 
                scholarship_percent, job_placement, diversity_score, major_strengths, 
                university_type, region, country, year_founded, student_faculty_ratio, campus_size, religious_affiliation) 
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            sample_data
        )
        
        # Insert sample application data for MIT (id=1)
        self._insert_sample_application_data()
        
        # Insert sample user for testing
        self.register_user("demo_user", "demo@example.com", "password123")
        
        self.conn.commit()
    
    def _insert_sample_application_data(self):
        """Insert sample application data for more accurate admission rate calculations"""
        # Get university IDs
        cursor = self.conn.execute("SELECT id FROM universities LIMIT 3")
        university_ids = [row[0] for row in cursor.fetchall()]
        
        if not university_ids:
            return
            
        # Clear existing sample application data
        self.conn.execute("DELETE FROM applications WHERE applicant_id LIKE 'sample%'")
        
        # Sample application statuses and counts for each university
        sample_data = []
        current_year = datetime.datetime.now().year
        
        # Generate realistic application data
        for uni_id in university_ids:
            # Get the university's acceptance rate
            cursor = self.conn.execute("SELECT acceptance_rate FROM universities WHERE id = ?", (uni_id,))
            acceptance_rate = cursor.fetchone()[0] / 100  # Convert to decimal
            
            # Calculate how many applications to generate
            total_apps = 500  # Total sample applications per university
            admitted_count = int(total_apps * acceptance_rate)
            rejected_count = total_apps - admitted_count - 20  # Reserve some for incomplete/pending
            incomplete_count = 10
            pending_count = 10
            
            # Generate sample admitted applications
            for i in range(admitted_count):
                app_date = f"{current_year}-{(i % 8) + 1:02d}-{(i % 28) + 1:02d}"  # Spread across months
                sample_data.append((
                    f"sample_applicant_{uni_id}_{i}", 
                    uni_id,
                    "Computer Science" if i % 3 == 0 else "Engineering" if i % 3 == 1 else "Business",
                    "admitted",
                    app_date,
                    3.7 + (0.3 * (i / admitted_count)),  # Higher GPA for admitted
                    1300 + int(300 * (i / admitted_count)),  # Higher SAT for admitted
                    0.8 + (0.2 * (i / admitted_count))  # Higher extracurricular for admitted
                ))
            
            # Generate sample rejected applications
            for i in range(rejected_count):
                app_date = f"{current_year}-{(i % 8) + 1:02d}-{(i % 28) + 1:02d}"
                sample_data.append((
                    f"sample_applicant_{uni_id}_{i + admitted_count}", 
                    uni_id,
                    "Computer Science" if i % 3 == 0 else "Engineering" if i % 3 == 1 else "Business",
                    "rejected",
                    app_date,
                    2.5 + (0.7 * (i / rejected_count)),  # Lower GPA for rejected
                    1000 + int(200 * (i / rejected_count)),  # Lower SAT for rejected
                    0.4 + (0.3 * (i / rejected_count))  # Lower extracurricular for rejected
                ))
            
            # Generate sample incomplete applications
            for i in range(incomplete_count):
                app_date = f"{current_year}-{(i % 8) + 1:02d}-{(i % 28) + 1:02d}"
                sample_data.append((
                    f"sample_applicant_{uni_id}_{i + admitted_count + rejected_count}", 
                    uni_id,
                    "Computer Science" if i % 3 == 0 else "Engineering" if i % 3 == 1 else "Business",
                    "incomplete",
                    app_date,
                    3.0 + (0.5 * (i / incomplete_count)),
                    1100 + int(200 * (i / incomplete_count)),
                    0.5 + (0.3 * (i / incomplete_count))
                ))
                
            # Generate sample pending applications
            for i in range(pending_count):
                app_date = f"{current_year}-{(i % 8) + 1:02d}-{(i % 28) + 1:02d}"
                sample_data.append((
                    f"sample_applicant_{uni_id}_{i + admitted_count + rejected_count + incomplete_count}", 
                    uni_id,
                    "Computer Science" if i % 3 == 0 else "Engineering" if i % 3 == 1 else "Business",
                    "pending",
                    app_date,
                    3.2 + (0.5 * (i / pending_count)),
                    1200 + int(200 * (i / pending_count)),
                    0.6 + (0.3 * (i / pending_count))
                ))
        
        # Insert the sample application data
        self.conn.executemany(
            "INSERT INTO applications (applicant_id, university_id, program, status, submission_date, gpa, sat_score, extracurricular_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            sample_data
        )
    
    def get_all_universities(self) -> List[Dict]:
        """Retrieves all universities from the database"""
        cursor = self.conn.execute("SELECT * FROM universities")
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_university(self, uni_id: int) -> Dict:
        """Retrieves a specific university by ID"""
        cursor = self.conn.execute("SELECT * FROM universities WHERE id = ?", (uni_id,))
        columns = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None
    
    def get_university_applications(self, university_id: int) -> List[Dict]:
        """
        Retrieves application data for a specific university
        
        Args:
            university_id: The ID of the university
            
        Returns:
            List of application dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM applications WHERE university_id = ?", 
            (university_id,)
        )
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_application_statistics(self, university_id: int) -> Dict:
        """
        Get application statistics for a university
        
        Args:
            university_id: The ID of the university
            
        Returns:
            Dictionary with application statistics
        """
        cursor = self.conn.execute(
            """
            SELECT 
                COUNT(*) as total_applications,
                SUM(CASE WHEN status = 'admitted' THEN 1 ELSE 0 END) as admitted_count,
                SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected_count,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
                SUM(CASE WHEN status = 'incomplete' THEN 1 ELSE 0 END) as incomplete_count
            FROM applications 
            WHERE university_id = ?
            """, 
            (university_id,)
        )
        
        row = cursor.fetchone()
        if not row or row[0] == 0:
            return {
                "total_applications": 0,
                "admission_rate": 0,
                "has_application_data": False
            }
            
        total = row[0]
        admitted = row[1]
        
        return {
            "total_applications": total,
            "admitted_count": admitted,
            "rejected_count": row[2],
            "pending_count": row[3],
            "incomplete_count": row[4],
            "admission_rate": (admitted / total) * 100 if total > 0 else 0,
            "has_application_data": True
        }
    
    # User authentication methods
    def _hash_password(self, password: str, salt: str = None) -> tuple:
        """
        Hash a password with a salt using PBKDF2
        
        Args:
            password: The plain text password
            salt: Optional salt, generated if not provided
            
        Returns:
            Tuple of (password_hash, salt)
        """
        if salt is None:
            salt = uuid.uuid4().hex
            
        # Use PBKDF2 with SHA-256, 100,000 iterations
        password_hash = hashlib.pbkdf2_hmac(
            'sha256', 
            password.encode('utf-8'), 
            salt.encode('utf-8'), 
            100000
        ).hex()
        
        return password_hash, salt
    
    def register_user(self, username: str, email: str, password: str) -> bool:
        """
        Register a new user
        
        Args:
            username: The user's username
            email: The user's email
            password: The plain text password
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Check if username or email already exists
            cursor = self.conn.execute(
                "SELECT id FROM users WHERE username = ? OR email = ?", 
                (username, email)
            )
            if cursor.fetchone():
                return False
                
            # Hash password
            password_hash, salt = self._hash_password(password)
            
            # Get current timestamp
            now = datetime.datetime.now().isoformat()
            
            # Insert new user
            self.conn.execute(
                "INSERT INTO users (username, email, password_hash, salt, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, email, password_hash, salt, now)
            )
            self.conn.commit()
            
            return True
            
        except Exception as e:
            print(f"Error registering user: {e}")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Dict:
        """
        Authenticate a user
        
        Args:
            username: The user's username
            password: The plain text password
            
        Returns:
            User dictionary if authentication successful, None otherwise
        """
        try:
            # Get user by username
            cursor = self.conn.execute(
                "SELECT id, username, email, password_hash, salt FROM users WHERE username = ?", 
                (username,)
            )
            user_data = cursor.fetchone()
            
            if not user_data:
                return None
                
            user_id, username, email, stored_hash, salt = user_data
            
            # Hash the provided password with the stored salt
            password_hash, _ = self._hash_password(password, salt)
            
            # Check if password matches
            if password_hash != stored_hash:
                return None
                
            # Update last login timestamp
            now = datetime.datetime.now().isoformat()
            self.conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now, user_id)
            )
            self.conn.commit()
            
            # Return user information
            return {
                "id": user_id,
                "username": username,
                "email": email
            }
            
        except Exception as e:
            print(f"Error authenticating user: {e}")
            return None
    
    def save_user_profile(self, user_id: int, profile_data: Dict) -> int:
        """
        Save a user's academic profile
        
        Args:
            user_id: The user's ID
            profile_data: Dictionary with profile data
            
        Returns:
            Profile ID if successful, None otherwise
        """
        try:
            # Validate user_id
            cursor = self.conn.execute("SELECT id FROM users WHERE id = ?", (user_id,))
            if not cursor.fetchone():
                print(f"Error: User ID {user_id} does not exist")
                return None
                
            # Get current timestamp
            now = datetime.datetime.now().isoformat()
            
            # Extract profile data with defaults
            profile_name = profile_data.get("profile_name", "My Profile")
            gpa = profile_data.get("gpa", 0.0)
            sat_score = profile_data.get("sat_score", 0)
            
            # Ensure list fields are actually lists before joining
            preferred_majors_raw = profile_data.get("preferred_majors", [])
            preferred_locations_raw = profile_data.get("preferred_locations", [])
            
            # Convert to lists if they're not already
            if not isinstance(preferred_majors_raw, list):
                preferred_majors_raw = [str(preferred_majors_raw)]
                print(f"Warning: preferred_majors was not a list, converted: {preferred_majors_raw}")
                
            if not isinstance(preferred_locations_raw, list):
                preferred_locations_raw = [str(preferred_locations_raw)]
                print(f"Warning: preferred_locations was not a list, converted: {preferred_locations_raw}")
                
            # Join to strings
            preferred_majors = ",".join(preferred_majors_raw)
            preferred_locations = ",".join(preferred_locations_raw)
            
            preferred_environment = profile_data.get("preferred_environment", "")
            budget = profile_data.get("budget", 0)
            
            # Print debug info
            print(f"Saving profile for user {user_id}: {profile_name}")
            print(f"GPA: {gpa}, SAT: {sat_score}, Budget: {budget}")
            print(f"Majors: {preferred_majors}")
            print(f"Locations: {preferred_locations}")
            print(f"Environment: {preferred_environment}")
            
            # Insert profile
            cursor = self.conn.execute(
                """INSERT INTO user_profiles 
                   (user_id, profile_name, gpa, sat_score, preferred_majors, 
                    budget, preferred_locations, preferred_environment, created_at, updated_at) 
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (user_id, profile_name, gpa, sat_score, preferred_majors, 
                 budget, preferred_locations, preferred_environment, now, now)
            )
            self.conn.commit()
            
            profile_id = cursor.lastrowid
            print(f"Profile saved successfully with ID: {profile_id}")
            return profile_id
            
        except Exception as e:
            print(f"Error saving user profile: {e}")
            import traceback
            traceback.print_exc()
            self.conn.rollback()
            return None
    
    def get_user_profiles(self, user_id: int) -> List[Dict]:
        """
        Get all profiles for a user
        
        Args:
            user_id: The user's ID
            
        Returns:
            List of profile dictionaries
        """
        cursor = self.conn.execute(
            "SELECT * FROM user_profiles WHERE user_id = ? ORDER BY updated_at DESC", 
            (user_id,)
        )
        columns = [col[0] for col in cursor.description]
        profiles = []
        
        for row in cursor.fetchall():
            profile = dict(zip(columns, row))
            
            # Convert comma-separated strings back to lists
            if profile.get("preferred_majors"):
                profile["preferred_majors"] = profile["preferred_majors"].split(",")
            else:
                profile["preferred_majors"] = []
                
            if profile.get("preferred_locations"):
                profile["preferred_locations"] = profile["preferred_locations"].split(",")
            else:
                profile["preferred_locations"] = []
                
            profiles.append(profile)
            
        return profiles
    
    def save_recommendation(self, user_id: int, profile_id: int, university_id: int, match_score: float, notes: str = None) -> bool:
        """
        Save a university recommendation for a user profile
        
        Args:
            user_id: The user's ID
            profile_id: The profile ID
            university_id: The university ID
            match_score: The match score
            notes: Optional notes
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current timestamp
            now = datetime.datetime.now().isoformat()
            
            # Check if this recommendation already exists
            cursor = self.conn.execute(
                "SELECT id FROM saved_recommendations WHERE user_id = ? AND profile_id = ? AND university_id = ?",
                (user_id, profile_id, university_id)
            )
            
            if cursor.fetchone():
                # Update existing recommendation
                self.conn.execute(
                    "UPDATE saved_recommendations SET match_score = ?, notes = ?, created_at = ? WHERE user_id = ? AND profile_id = ? AND university_id = ?",
                    (match_score, notes, now, user_id, profile_id, university_id)
                )
            else:
                # Insert new recommendation
                self.conn.execute(
                    "INSERT INTO saved_recommendations (user_id, profile_id, university_id, match_score, notes, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, profile_id, university_id, match_score, notes, now)
                )
                
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving recommendation: {e}")
            return False
    
    def get_saved_recommendations(self, user_id: int, profile_id: int = None) -> List[Dict]:
        """
        Get saved recommendations for a user
        
        Args:
            user_id: The user's ID
            profile_id: Optional profile ID to filter by
            
        Returns:
            List of recommendation dictionaries
        """
        query = """
            SELECT r.id, r.user_id, r.profile_id, r.university_id, r.match_score, r.notes, r.created_at,
                   u.name as university_name, u.location, u.academic_rank, u.tuition_fee, u.acceptance_rate
            FROM saved_recommendations r
            JOIN universities u ON r.university_id = u.id
            WHERE r.user_id = ?
        """
        params = [user_id]
        
        if profile_id:
            query += " AND r.profile_id = ?"
            params.append(profile_id)
            
        query += " ORDER BY r.match_score DESC"
        
        cursor = self.conn.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def delete_user_profile(self, user_id, profile_id):
        """Delete a user profile and associated saved recommendations"""
        try:
            with self.conn:
                # First, delete associated recommendations
                self.conn.execute('''
                    DELETE FROM saved_recommendations
                    WHERE user_id = ? AND profile_id = ?
                ''', (user_id, profile_id))
                
                # Then delete the profile
                self.conn.execute('''
                    DELETE FROM user_profiles
                    WHERE id = ? AND user_id = ?
                ''', (profile_id, user_id))
                
                # Check if profile was deleted (belongs to user)
                return self.conn.total_changes > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False

    def delete_saved_recommendation(self, user_id, rec_id):
        """Delete a single saved recommendation"""
        try:
            with self.conn:
                self.conn.execute('''
                    DELETE FROM saved_recommendations
                    WHERE id = ? AND user_id = ?
                ''', (rec_id, user_id))
                
                # Check if recommendation was deleted (belongs to user)
                return self.conn.total_changes > 0
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
    
    def close(self):
        """Closes the database connection"""
        if self.conn:
            self.conn.close() 