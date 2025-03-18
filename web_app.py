from flask import Flask, render_template, request, jsonify, redirect, url_for, session, flash
import os
import json
from db import UniversityDatabase
from matcher import UniversityMatcher
from admission_analytics import AdmissionRateCalculator
import matplotlib
matplotlib.use('Agg')  # Set the backend to Agg for server environment
import matplotlib.pyplot as plt
import base64
from io import BytesIO
import numpy as np
import threading
import pandas as pd
from datetime import datetime
import functools

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Configure Deepseek API (can be set through environment variables)
os.environ["USE_DEEPSEEK_API"] = os.environ.get("USE_DEEPSEEK_API", "false")
os.environ["DEEPSEEK_API_KEY"] = os.environ.get("DEEPSEEK_API_KEY", "")
os.environ["DEEPSEEK_API_URL"] = os.environ.get("DEEPSEEK_API_URL", 
                                              "https://api.deepseek.com/v1/match")

# Add custom Jinja2 filters
@app.template_filter('format_number')
def format_number(value):
    """Format a number with commas as thousands separators"""
    try:
        return f"{int(value):,}"
    except (ValueError, TypeError):
        return value

# Initialize database and matcher
db = UniversityDatabase()
db.insert_sample_data()
matcher = UniversityMatcher(db)

# Add a lock for thread safety
db_lock = threading.Lock()

def get_user_profile():
    """Get user profile from session or create a default one"""
    if 'user_profile' in session:
        return session['user_profile']
    
    # For logged-in users, try to get profile from DB
    if 'user_id' in session:
        user_id = session['user_id']
        profiles = db.get_user_profiles(user_id)
        
        if profiles and len(profiles) > 0:
            # Get the most recent profile
            profile = profiles[0]
            
            # Format for consistency
            user_profile = {
                "gpa": float(profile.get('gpa', 3.5)),
                "sat_score": int(profile.get('sat_score', 1200)),
                "preferred_majors": profile.get('majors', '').split(',') if profile.get('majors') else [],
                "budget": int(profile.get('budget', 30000)),
                "preferred_locations": profile.get('locations', '').split(',') if profile.get('locations') else [],
                "preferred_environment": profile.get('environment', 'Urban')
            }
            
            return user_profile
    
    # Default profile if nothing is found
    return {
        "gpa": 3.5,
        "sat_score": 1200,
        "preferred_majors": ["Computer Science", "Engineering"],
        "budget": 30000,
        "preferred_locations": ["Boston, MA, USA", "New York, NY, USA"],
        "preferred_environment": "Urban",
        "importance_weights": {
            "academic": 0.35,
            "financial": 0.3,
            "location": 0.15,
            "career": 0.15,
            "campus": 0.05
        }
    }

# Authentication decorator
def login_required(view_func):
    @functools.wraps(view_func)
    def wrapped_view(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return view_func(*args, **kwargs)
    return wrapped_view

# User authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Authenticate user
        user = db.authenticate_user(username, password)
        
        if user:
            # Store user info in session
            session['user_id'] = user['id']
            session['username'] = user['username']
            
            # Redirect to dashboard or home page
            next_page = request.args.get('next', url_for('index'))
            return redirect(next_page)
        else:
            return render_template('login.html', error="Invalid username or password")
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validate form data
        if password != confirm_password:
            return render_template('register.html', error="Passwords do not match")
        
        if len(password) < 8:
            return render_template('register.html', error="Password must be at least 8 characters long")
        
        # Register user
        success = db.register_user(username, email, password)
        
        if success:
            return redirect(url_for('login', success="Registration successful! Please login with your new account."))
        else:
            return render_template('register.html', error="Username or email already exists")
    
    return render_template('register.html')

@app.route('/logout')
def logout():
    """Handle user logout"""
    session.clear()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """User dashboard with saved profiles and recommendations"""
    # Get user profiles
    user_id = session['user_id']
    profiles = db.get_user_profiles(user_id)
    
    # Get saved recommendations
    recommendations = db.get_saved_recommendations(user_id)
    
    return render_template('dashboard.html', 
                          profiles=profiles,
                          recommendations=recommendations,
                          username=session['username'])

@app.route('/save_profile', methods=['POST'])
@login_required
def save_profile():
    """Save user profile to database"""
    if 'user_profile' not in session:
        flash("No profile data found to save", "error")
        return redirect(url_for('profile'))
    
    user_id = session['user_id']
    profile_data = session['user_profile']
    
    # Add profile name (use timestamp if not provided)
    profile_name = request.form.get('profile_name', f"Profile {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    profile_data['profile_name'] = profile_name
    
    # Debug info
    print(f"Saving profile for user {user_id}")
    print(f"Profile data: {profile_data}")
    
    # Save profile to database
    profile_id = db.save_user_profile(user_id, profile_data)
    
    if profile_id:
        # If recommendations exist, save them too
        if 'recommendations' in session:
            for uni in session['recommendations']:
                db.save_recommendation(
                    user_id, 
                    profile_id, 
                    uni['id'], 
                    uni['match_score']
                )
        
        flash("Profile saved successfully!", "success")
        return redirect(url_for('dashboard'))
    else:
        flash("Failed to save profile. Please try again.", "error")
        return redirect(url_for('profile'))

@app.route('/')
def index():
    """Render the homepage"""
    return render_template('index.html')

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """Handle user profile creation and updates"""
    if request.method == 'POST':
        try:
            # Get form data
            gpa = float(request.form.get('gpa', 3.5))
            sat_score = int(request.form.get('sat_score', 1200))
            
            # Handle majors - check for both new and old format
            preferred_majors = request.form.getlist('preferred_majors')
            if not preferred_majors and 'majors' in request.form:
                # Fallback to old format if present
            majors = request.form['majors']
            preferred_majors = [m.strip() for m in majors.split(",") if m.strip()]
            
            budget = int(request.form.get('budget', 30000))
            
            # Handle locations - check for both formats
            preferred_locations = request.form.getlist('preferred_locations')
            if not preferred_locations and 'locations' in request.form:
                # Fallback to old format if present
            locations = request.form['locations']
            preferred_locations = [loc.strip() for loc in locations.split(",") if loc.strip()]
            
            environment = request.form.get('preferred_environment', 'Urban')
            
            # Get weights with defaults
            academic_weight = int(request.form.get('weight_academic', 5))
            financial_weight = int(request.form.get('weight_financial', 5))
            location_weight = int(request.form.get('weight_location', 5))
            career_weight = int(request.form.get('weight_career', 5))
            campus_weight = int(request.form.get('weight_campus', 5))
            
            # Create user profile
            user_profile = {
                "gpa": gpa,
                "sat_score": sat_score,
                "preferred_majors": preferred_majors,
                "budget": budget,
                "preferred_locations": preferred_locations,
                "preferred_environment": environment
            }
            
            # Create weights
            total_weight = academic_weight + financial_weight + location_weight + career_weight + campus_weight
            if total_weight == 0:
                total_weight = 1  # Avoid division by zero
                
            # Normalize weights to ensure they sum to 1
            weights = {
                "academic": float(academic_weight) / total_weight,
                "financial": float(financial_weight) / total_weight,
                "location": float(location_weight) / total_weight,
                "career": float(career_weight) / total_weight,
                "campus": float(campus_weight) / total_weight
            }
            
            # Store in session
            session['user_profile'] = user_profile
            session['weights'] = weights
            
            # If edit_profile_id is provided, update existing profile
            edit_profile_id = request.args.get('edit_profile_id')
            if edit_profile_id:
                profile_id = int(edit_profile_id)
                
                # Format data for database
                profile_data = {
                    'id': profile_id,
                    'user_id': session['user_id'],
                    'profile_name': request.form.get('profile_name', 'My Profile'),
                    'gpa': gpa,
                    'sat_score': sat_score,
                    'majors': ','.join(preferred_majors),
                    'budget': budget,
                    'locations': ','.join(preferred_locations),
                    'environment': environment,
                    'weights': json.dumps(weights)
                }
                
                # Update profile in DB
                success = db.update_user_profile(profile_data)
                
                if success:
                    flash("Profile updated successfully!", "success")
                else:
                    flash("Failed to update profile. Please try again.", "error")
            else:
                # Format data for database
                profile_data = {
                    'user_id': session['user_id'],
                    'profile_name': request.form.get('profile_name', 'My Profile'),
                    'gpa': gpa,
                    'sat_score': sat_score,
                    'majors': ','.join(preferred_majors),
                    'budget': budget,
                    'locations': ','.join(preferred_locations),
                    'environment': environment,
                    'weights': json.dumps(weights)
                }
                
                # Save profile to DB
                success = db.save_user_profile(session['user_id'], profile_data)
                
                if success:
                    flash("Profile saved successfully!", "success")
                else:
                    flash("Failed to save profile. Please try again.", "error")
                    
            # Redirect to recommendations
            return redirect(url_for('recommendations'))
        except Exception as e:
            flash(f"Error processing profile: {str(e)}", "error")
            print(f"Profile error: {e}")
    
    # For GET request, show the form
    edit_profile = None
    edit_profile_id = request.args.get('edit_profile_id')
    
    if edit_profile_id:
        try:
            # Get profile from DB
            profile = db.get_user_profile(int(edit_profile_id))
            
            if profile:
                # Format for template
                edit_profile = {
                    'id': profile['id'],
                    'profile_name': profile.get('profile_name', 'My Profile'),
                    'gpa': profile.get('gpa', 3.5),
                    'sat_score': profile.get('sat_score', 1200),
                    'preferred_majors': profile.get('majors', '').split(',') if profile.get('majors') else [],
                    'budget': profile.get('budget', 30000),
                    'preferred_locations': profile.get('locations', '').split(',') if profile.get('locations') else [],
                    'preferred_environment': profile.get('environment', 'Urban'),
                    'importance_weights': json.loads(profile.get('weights', '{}')) if profile.get('weights') else {
                        "academic": 0.35,
                        "financial": 0.3,
                        "location": 0.15,
                        "career": 0.15,
                        "campus": 0.05
                    }
                }
        except Exception as e:
            flash(f"Error loading profile: {str(e)}", "error")
            print(f"Profile load error: {e}")
    
    return render_template('profile.html', edit_profile=edit_profile)

@app.route('/recommendations')
def recommendations():
    """Generate university recommendations based on user profile"""
    
    # Check if there is a user profile in session
    has_profile = 'user_profile' in session
    
    # Get filters from the request
    filters = {
        'location': request.args.get('location', ''),
        'environment': request.args.get('environment', ''),
        'min_acceptance': request.args.get('min_acceptance', ''),
        'max_acceptance': request.args.get('max_acceptance', ''),
        'max_tuition': request.args.get('max_tuition', ''),
        'domestic_only': request.args.get('domestic_only') == 'true',
        'country': request.args.get('country', ''),
        'region': request.args.get('region', ''),
        'campus_size': request.args.get('campus_size', ''),
        'university_type': request.args.get('university_type', ''),
        'religious_affiliation': request.args.get('religious_affiliation', ''),
        'major': request.args.get('major', '')
    }
    
    # Get all universities from database
    universities = db.get_all_universities()
    
    # If there is a profile, calculate match scores
    if has_profile:
        profile = session['user_profile']
        weights = session.get('weights', {
            'academic': 1.0,
            'financial': 1.0,
            'location': 1.0,
            'career': 1.0,
            'campus': 1.0
        })
        
        # Match universities to user profile
        matcher.set_weights(weights)
        universities = matcher.match_universities(profile, universities)
        
        # Sort by match score (descending)
        universities.sort(key=lambda u: u.get('match_score', 0), reverse=True)
    
    # Filter results based on request parameters
    if filters['location']:
        universities = [u for u in universities if u['location'] == filters['location']]
        
    if filters['environment']:
        universities = [u for u in universities if u['environment'] == filters['environment']]
        
    if filters['min_acceptance']:
        min_acceptance = float(filters['min_acceptance'])
        universities = [u for u in universities if u['acceptance_rate'] >= min_acceptance]
        
    if filters['max_acceptance']:
        max_acceptance = float(filters['max_acceptance'])
        universities = [u for u in universities if u['acceptance_rate'] <= max_acceptance]
        
    if filters['max_tuition']:
        max_tuition = float(filters['max_tuition'])
        universities = [u for u in universities if u['tuition_fee'] <= max_tuition]
    
    if filters['domestic_only']:
        universities = [u for u in universities if u.get('country', '') == 'USA']
    
    if filters['country']:
        universities = [u for u in universities if u.get('country', '') == filters['country']]
        
    if filters['region']:
        universities = [u for u in universities if u.get('region', '') == filters['region']]
        
    if filters['campus_size']:
        universities = [u for u in universities if u.get('campus_size', '') == filters['campus_size']]
        
    if filters['university_type']:
        universities = [u for u in universities if u.get('university_type', '') == filters['university_type']]
        
    if filters['religious_affiliation']:
        if filters['religious_affiliation'] == 'None':
            universities = [u for u in universities if not u.get('religious_affiliation')]
        else:
            universities = [u for u in universities if u.get('religious_affiliation') == filters['religious_affiliation']]
    
    if filters['major']:
        # Filter by major (case-insensitive substring match)
        major_filter = filters['major'].lower()
        universities = [u for u in universities if major_filter in u.get('major_strengths', '').lower()]
    
    # Get unique values for filter dropdowns
    all_locations = sorted(list({u['location'] for u in db.get_all_universities() if 'location' in u}))
    all_environments = sorted(list({u['environment'] for u in db.get_all_universities() if 'environment' in u}))
    
    # Get unique regions organized by country
    all_regions = []
    regions_by_country = {}
    for uni in db.get_all_universities():
        if 'region' in uni and 'country' in uni and uni['region'] and uni['country']:
            country = uni['country']
            region = uni['region']
            if country not in regions_by_country:
                regions_by_country[country] = set()
            regions_by_country[country].add(region)
    
    for country, regions in regions_by_country.items():
        for region in sorted(regions):
            all_regions.append({"name": region, "country": country})
    
    # Get unique countries
    all_countries = sorted(list({u['country'] for u in db.get_all_universities() if 'country' in u}))
    
    # Get unique campus sizes
    all_campus_sizes = sorted(list({u['campus_size'] for u in db.get_all_universities() if 'campus_size' in u}))
    
    # Get unique university types
    all_university_types = sorted(list({u['university_type'] for u in db.get_all_universities() if 'university_type' in u}))
    
    # Get unique religious affiliations
    all_religious_affiliations = sorted(list({u['religious_affiliation'] for u in db.get_all_universities() 
                                            if 'religious_affiliation' in u and u['religious_affiliation']}))
    
    # Get all majors (from all universities' major_strengths)
    all_majors = set()
    for uni in db.get_all_universities():
        if 'major_strengths' in uni and uni['major_strengths']:
            majors = uni['major_strengths'].split(',')
            all_majors.update(majors)
    all_majors = sorted(list(all_majors))
    
    # Check if we're using the Deepseek API
    api_info = {
        "using_deepseek_api": os.environ.get("USE_DEEPSEEK_API", "false").lower() == "true"
    }
    
    # Render the recommendations template
    return render_template('recommendations.html', 
                          recommendations=universities, 
                          has_profile=has_profile,
                          locations=all_locations,
                          environments=all_environments,
                          regions=all_regions,
                          countries=all_countries,
                          campus_sizes=all_campus_sizes,
                          university_types=all_university_types,
                          religious_affiliations=all_religious_affiliations,
                          majors=all_majors,
                          filters=filters,
                          api_info=api_info)

@app.route('/university/<int:uni_id>')
def university_detail(uni_id):
    """Show detailed information about a specific university"""
    if 'recommendations' not in session:
        return redirect(url_for('recommendations'))
    
    # Find the university in the recommendations
    university = None
    for uni in session['recommendations']:
        if uni['id'] == uni_id:
            university = uni
            break
    
    if not university:
        return redirect(url_for('recommendations'))
    
    # Generate radar chart image
    img_str = generate_radar_chart(university)
    
    return render_template('university_detail.html', university=university, radar_chart=img_str)

@app.route('/compare', methods=['GET', 'POST'])
def compare():
    """Compare multiple universities"""
    # Check if user has viewed recommendations first
    if 'recommendations' not in session:
        # Initialize recommendations if not in session
        try:
            user_profile = get_user_profile()
            matcher = UniversityMatcher(db)
            recommendations = matcher.get_recommendations(user_profile, top_n=100)
            session['recommendations'] = recommendations
        except Exception as e:
            print(f"Error getting recommendations: {e}")
            flash("Please complete your profile first to get personalized university recommendations.", "error")
            return redirect(url_for('profile'))
    
    # Get user profile for customized comparison
    user_profile = get_user_profile()
    
    if request.method == 'POST':
        # Get selected university IDs
        selected_ids = request.form.getlist('university_ids')
        
        if not selected_ids or len(selected_ids) < 2:
            return render_template('compare.html', 
                                   recommendations=session['recommendations'],
                                   error="Please select at least 2 universities to compare.")
        
        # Convert to integers
        selected_ids = [int(id) for id in selected_ids]
        
        # Get the selected universities
        selected_unis = []
        for uni in session['recommendations']:
            if uni['id'] in selected_ids:
                selected_unis.append(uni)
        
        # Generate comparison chart with user profile info
        img_str = generate_comparison_chart(selected_unis, user_profile)
        
        # Generate personalized insights based on user profile
        insights = generate_personalized_insights(selected_unis, user_profile)
        
        return render_template('comparison_results.html', 
                               universities=selected_unis, 
                               comparison_chart=img_str,
                               user_profile=user_profile,
                               insights=insights)
    
    # For GET request, show the selection form
    return render_template('compare.html', 
                          recommendations=session['recommendations'],
                          user_profile=user_profile)

@app.route('/api_settings', methods=['GET', 'POST'])
@login_required
def api_settings():
    """Configure API settings"""
    if request.method == 'POST':
        # Update API settings
        use_api = request.form.get('use_deepseek_api', 'false')
        api_key = request.form.get('deepseek_api_key', '')
        api_url = request.form.get('deepseek_api_url', 'https://api.deepseek.com/v1/match')
        
        # Set environment variables
        os.environ["USE_DEEPSEEK_API"] = use_api
        os.environ["DEEPSEEK_API_KEY"] = api_key
        os.environ["DEEPSEEK_API_URL"] = api_url
        
        # Refresh matcher to pick up new settings
        global matcher
        matcher = UniversityMatcher(db)
        
        return redirect(url_for('index'))
    
    # For GET request, show settings form
    current_settings = {
        "use_deepseek_api": os.environ.get("USE_DEEPSEEK_API", "false"),
        "deepseek_api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "deepseek_api_url": os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/match")
    }
    
    return render_template('api_settings.html', settings=current_settings)

@app.route('/admin/admission-analytics', methods=['GET', 'POST'])
@login_required
def admin_admission_analytics():
    """Admin dashboard for admission rate analytics"""
    # Get all universities for the dropdown
    universities = db.get_all_universities()
    
    # Get form parameters
    selected_university_id = request.form.get('university_id', '1')  # Default to first university
    try:
        selected_university_id = int(selected_university_id)
    except ValueError:
        selected_university_id = 1
        
    include_incomplete = request.form.get('include_incomplete', 'false').lower() == 'true'
    time_interval = request.form.get('time_interval', 'month')
    
    # Get application data for the selected university
    applications = db.get_university_applications(selected_university_id)
    
    # Initialize the calculator
    calculator = AdmissionRateCalculator()
    calculator.load_applications(applications)
    
    # Get validation results
    validation = calculator.validate_data_consistency()
    
    # Calculate overall admission rate
    admission_rate, details = calculator.calculate_admission_rate(
        exclude_incomplete=not include_incomplete
    )
    
    # Calculate program-specific rates
    program_results = calculator.calculate_stratified_rates("program")
    
    # Calculate temporal trends
    time_results = calculator.analyze_trends(interval=time_interval)
    
    # Generate charts
    overall_chart = generate_admission_pie_chart(details["status_breakdown"])
    program_chart = generate_program_bar_chart(program_results)
    time_chart = generate_time_trend_chart(time_results)
    
    # Format stats for display
    stats = {
        "admission_rate": admission_rate,
        "admitted_count": details["status_breakdown"]["admitted"],
        "total_valid_applications": sum(details["status_breakdown"].values()),
        "incomplete_count": details["status_breakdown"]["incomplete"] if "incomplete" in details["status_breakdown"] else 0,
        "overall_chart": overall_chart,
        "program_chart": program_chart,
        "time_chart": time_chart
    }
    
    # Format program stats for display
    program_stats = {}
    for program, data in program_results.items():
        if program == "overall":
            continue
        program_stats[program] = {
            "admission_rate": data["admission_rate"],
            "applications": data["details"]["filtered_applications"],
            "admitted": data["details"]["status_breakdown"]["admitted"]
        }
    
    # Generate time analysis description
    time_analysis = analyze_time_trends(time_results)
    
    return render_template('admin_admission_analytics.html',
                          universities=universities,
                          selected_university_id=selected_university_id,
                          include_incomplete=include_incomplete,
                          time_interval=time_interval,
                          stats=stats,
                          program_stats=program_stats,
                          time_stats=time_results,
                          time_analysis=time_analysis,
                          validation=validation)

@app.route('/admin/fix-data-issues/<int:university_id>')
@login_required
def admin_fix_data_issues(university_id):
    """Fix data issues in application data"""
    # This would typically implement automated fixes for common data issues
    # For demo purposes, redirect back to analytics
    return redirect(url_for('admin_admission_analytics', university_id=university_id))

@app.route('/admin/export-data/<int:university_id>')
@login_required
def admin_export_data(university_id):
    """Export application data for a university"""
    # In a real app, this would generate a CSV or Excel file for download
    # For demo purposes, redirect back to analytics
    return redirect(url_for('admin_admission_analytics', university_id=university_id))

@app.route('/delete_profile/<int:profile_id>')
@login_required
def delete_profile(profile_id):
    """Delete a user profile"""
    user_id = session['user_id']
    success = db.delete_user_profile(user_id, profile_id)
    
    if success:
        flash("Profile deleted successfully.", "success")
    else:
        flash("Failed to delete profile.", "error")
    
    return redirect(url_for('dashboard'))

@app.route('/delete_saved_recommendation/<int:rec_id>')
@login_required
def delete_saved_recommendation(rec_id):
    """Delete a saved recommendation"""
    user_id = session['user_id']
    success = db.delete_saved_recommendation(user_id, rec_id)
    
    if success:
        flash("Recommendation removed from saved list.", "success")
    else:
        flash("Failed to remove recommendation.", "error")
    
    return redirect(url_for('dashboard'))

def generate_admission_pie_chart(status_breakdown):
    """Generate pie chart for admission status breakdown"""
    labels = list(status_breakdown.keys())
    sizes = list(status_breakdown.values())
    
    # Custom colors for different statuses
    colors = {
        'admitted': '#28a745',
        'rejected': '#dc3545',
        'pending': '#ffc107',
        'incomplete': '#6c757d'
    }
    
    color_list = [colors.get(status, '#007bff') for status in labels]
    
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=color_list)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle
    plt.title('Application Status Distribution')
    
    # Save to BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    
    # Convert to base64 for embedding in HTML
    img_str = base64.b64encode(img.getvalue()).decode('utf-8')
    
    return img_str

def generate_program_bar_chart(program_results):
    """Generate bar chart for program-specific admission rates"""
    programs = [prog for prog in program_results.keys() if prog != "overall"]
    rates = [program_results[prog]["admission_rate"] for prog in programs]
    
    # Add overall for comparison
    programs.append("Overall")
    rates.append(program_results["overall"]["admission_rate"])
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Create bars
    bars = ax.bar(programs, rates, color='#007bff')
    
    # Highlight the overall bar
    bars[-1].set_color('#dc3545')
    
    # Add labels and title
    ax.set_xlabel('Program')
    ax.set_ylabel('Acceptance Rate (%)')
    ax.set_title('Acceptance Rates by Program')
    
    # Add rate values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax.annotate(f'{height:.1f}%',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, 3),  # 3 points vertical offset
                   textcoords="offset points",
                   ha='center', va='bottom')
    
    plt.tight_layout()
    
    # Save to BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    
    # Convert to base64 for embedding in HTML
    img_str = base64.b64encode(img.getvalue()).decode('utf-8')
    
    return img_str

def generate_time_trend_chart(time_results):
    """Generate line chart for temporal admission rate trends"""
    if not time_results or "error" in time_results:
        # Create empty chart if no data
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.text(0.5, 0.5, 'No temporal data available', ha='center', va='center', fontsize=14)
        ax.set_xlim([0, 1])
        ax.set_ylim([0, 1])
        ax.axis('off')
        
        # Save to BytesIO object
        img = BytesIO()
        plt.savefig(img, format='png')
        plt.close(fig)
        img.seek(0)
        
        # Convert to base64 for embedding in HTML
        img_str = base64.b64encode(img.getvalue()).decode('utf-8')
        
        return img_str
    
    # Sort periods chronologically
    periods = sorted(time_results.keys())
    rates = [time_results[period]["admission_rate"] for period in periods]
    app_counts = [time_results[period]["application_count"] for period in periods]
    
    # Create figure with two y-axes
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    # Plot admission rates
    color = '#007bff'
    ax1.set_xlabel('Time Period')
    ax1.set_ylabel('Acceptance Rate (%)', color=color)
    line1 = ax1.plot(periods, rates, marker='o', linestyle='-', color=color, label='Acceptance Rate')
    ax1.tick_params(axis='y', labelcolor=color)
    
    # Set x-axis tick marks to show periods
    plt.xticks(rotation=45, ha='right')
    
    # Create second y-axis for application counts
    ax2 = ax1.twinx()
    color = '#dc3545'
    ax2.set_ylabel('Application Count', color=color)
    line2 = ax2.plot(periods, app_counts, marker='s', linestyle='--', color=color, label='Application Count')
    ax2.tick_params(axis='y', labelcolor=color)
    
    # Add legend
    lines = line1 + line2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc='upper left')
    
    plt.title('Acceptance Rate and Application Count Over Time')
    plt.tight_layout()
    
    # Save to BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close(fig)
    img.seek(0)
    
    # Convert to base64 for embedding in HTML
    img_str = base64.b64encode(img.getvalue()).decode('utf-8')
    
    return img_str

def analyze_time_trends(time_results):
    """Analyze temporal trends and generate insights"""
    if not time_results or "error" in time_results:
        return {
            "trend_description": "No temporal data available for analysis.",
            "recommendations": []
        }
    
    # Sort periods chronologically
    periods = sorted(time_results.keys())
    
    if len(periods) < 2:
        return {
            "trend_description": "Not enough data points for trend analysis. Need at least two time periods.",
            "recommendations": ["Collect more time-based application data for trend analysis."]
        }
    
    # Calculate trends
    rates = [time_results[period]["admission_rate"] for period in periods]
    app_counts = [time_results[period]["application_count"] for period in periods]
    
    # Calculate overall trend (simple linear regression)
    x = list(range(len(periods)))
    rate_trend = np.polyfit(x, rates, 1)[0]  # Slope of the trend line
    
    # Generate description based on trend
    if rate_trend > 1:
        trend_text = f"Acceptance rate is increasing significantly (by approximately {abs(rate_trend):.1f}% per period)."
    elif rate_trend > 0.5:
        trend_text = f"Acceptance rate is increasing moderately (by approximately {abs(rate_trend):.1f}% per period)."
    elif rate_trend > 0:
        trend_text = f"Acceptance rate is increasing slightly (by approximately {abs(rate_trend):.1f}% per period)."
    elif rate_trend > -0.5:
        trend_text = f"Acceptance rate is decreasing slightly (by approximately {abs(rate_trend):.1f}% per period)."
    elif rate_trend > -1:
        trend_text = f"Acceptance rate is decreasing moderately (by approximately {abs(rate_trend):.1f}% per period)."
    else:
        trend_text = f"Acceptance rate is decreasing significantly (by approximately {abs(rate_trend):.1f}% per period)."
    
    # Check correlation between application count and acceptance rate
    if len(periods) >= 3:
        correlation = np.corrcoef(app_counts, rates)[0, 1]
        if correlation > 0.7:
            trend_text += " There is a strong positive correlation between application volume and acceptance rate."
        elif correlation < -0.7:
            trend_text += " There is a strong negative correlation between application volume and acceptance rate."
    
    # Generate recommendations
    recommendations = []
    if rate_trend > 1:
        recommendations.append("Consider reviewing admission criteria as the current trend shows significant increase in acceptance rates.")
    elif rate_trend < -1:
        recommendations.append("The decreasing acceptance rate trend may indicate increasing selectivity or capacity constraints.")
    
    # Variability check
    rate_std = np.std(rates)
    if rate_std > 5:
        recommendations.append(f"High variability in acceptance rates detected (std.dev: {rate_std:.1f}%). Consider standardizing review processes.")
    
    # Check for seasonal patterns if enough data
    if len(periods) >= 4:
        recommendations.append("Consider seasonal patterns in applications and acceptances for more accurate rate reporting.")
    
    return {
        "trend_description": trend_text,
        "recommendations": recommendations
    }

def generate_radar_chart(university, user_profile=None):
    """Generate a radar chart for a university"""
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Define the categories and values
    categories = [
        'Academic', 'Financial', 
        'Location', 'Career', 
        'Campus Life'
    ]
    
    # Get component scores, ensuring they are between 0 and 1
    values = [
        min(1.0, max(0.0, university.get('component_academic_score', 0.0))),
        min(1.0, max(0.0, university.get('component_financial_score', 0.0))),
        min(1.0, max(0.0, university.get('component_location_score', 0.0))),
        min(1.0, max(0.0, university.get('component_career_score', 0.0))),
        min(1.0, max(0.0, university.get('component_campus_score', 0.0)))
    ]
    
    # Number of categories
    N = len(categories)
    
    # Set the angle for each category
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop
    
    # Adjust values to plot
    values += values[:1]  # Close the loop
    
    # Draw the chart
    ax.plot(angles, values, linewidth=2, linestyle='solid', label=university['name'])
    ax.fill(angles, values, alpha=0.25)
    
    # Set category labels
    plt.xticks(angles[:-1], categories, size=12)
    
    # Draw y-axis labels
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["20%", "40%", "60%", "80%", "100%"], color="grey", size=10)
    plt.ylim(0, 1)
    
    # Add title with user profile context if available
    if user_profile:
        plt.title(f"Match Profile for {university['name']}\nBased on Your Academic Profile", size=15, y=1.1)
    else:
        plt.title(f"Match Profile for {university['name']}", size=15, y=1.1)
    
    # Add legend
    plt.legend(loc='upper right')
    
    # Save to a Base64 string
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    # Encode to base64
    img_str = "data:image/png;base64,"
    img_str += base64.b64encode(image_png).decode('utf-8')
    
    # Close the figure to free memory
    plt.close(fig)
    
    return img_str

def generate_comparison_chart(universities, user_profile=None):
    """Generate a radar chart for multiple universities"""
    # Create a figure and axis
    fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(polar=True))
    
    # Define the categories
    categories = [
        'Academic', 'Financial', 
        'Location', 'Career', 
        'Campus Life'
    ]
    
    # Number of categories
    N = len(categories)
    
    # Set the angle for each category
    angles = [n / float(N) * 2 * np.pi for n in range(N)]
    angles += angles[:1]  # Close the loop
    
    # Colors for each university
    colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
    
    # Draw each university
    for i, university in enumerate(universities):
        # Get component scores, ensuring they are between 0 and 1
        values = [
            min(1.0, max(0.0, university.get('component_academic_score', 0.0))),
            min(1.0, max(0.0, university.get('component_financial_score', 0.0))),
            min(1.0, max(0.0, university.get('component_location_score', 0.0))),
            min(1.0, max(0.0, university.get('component_career_score', 0.0))),
            min(1.0, max(0.0, university.get('component_campus_score', 0.0)))
        ]
        
        # Close the loop
        values += values[:1]
        
        # Draw the chart for this university
        color = colors[i % len(colors)]
        ax.plot(angles, values, linewidth=2, linestyle='solid', color=color, label=university['name'])
        ax.fill(angles, values, color=color, alpha=0.1)
    
    # Set category labels
    plt.xticks(angles[:-1], categories, size=12)
    
    # Draw y-axis labels
    ax.set_rlabel_position(0)
    plt.yticks([0.2, 0.4, 0.6, 0.8, 1.0], ["20%", "40%", "60%", "80%", "100%"], color="grey", size=10)
    plt.ylim(0, 1)
    
    # Add title with user profile context if available
    if user_profile:
        plt.title(f"University Comparison\nBased on Your Academic Profile (GPA: {user_profile['gpa']}, SAT: {user_profile['sat_score']})", 
                 size=15, y=1.1)
            else:
        plt.title("University Comparison", size=15, y=1.1)
    
    # Add legend
    plt.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
    
    # Create a separate table to compare numerical values
    table_data = []
    headers = ["University", "Academic Rank", "Tuition", "Acceptance Rate", "Aid %", "Job Rate", "Major Match"]
    
    for uni in universities:
        # Calculate major match score if user profile has preferred majors
        major_match = "N/A"
        if user_profile and 'preferred_majors' in user_profile and user_profile['preferred_majors']:
            uni_majors = uni.get('major_strengths', '').lower().split(',')
            user_majors = [m.lower() for m in user_profile['preferred_majors']]
            matches = sum(1 for um in user_majors if any(um in unm for unm in uni_majors))
            total = len(user_majors) if user_majors else 1
            major_match = f"{int((matches/total)*100)}%"
        
        row = [
            uni['name'],
            f"#{uni.get('academic_rank', 'N/A')}",
            f"${uni.get('tuition_fee', 0):,}",
            f"{uni.get('acceptance_rate', 0):.1f}%",
            f"{uni.get('scholarship_percentage', 0):.1f}%",
            f"{uni.get('job_placement_rate', 0):.1f}%",
            major_match
        ]
        table_data.append(row)
    
    # Create a table below the chart
    ax_table = fig.add_axes([0.1, 0.0, 0.8, 0.2])
    ax_table.axis('tight')
    ax_table.axis('off')
    table = ax_table.table(
        cellText=table_data, 
        colLabels=headers,
        loc='center', 
        cellLoc='center'
    )
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.5)
    
    # Add some more space for the table
    plt.subplots_adjust(bottom=0.3)
    
    # Save to a Base64 string
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    image_png = buffer.getvalue()
    buffer.close()
    
    # Encode to base64
    img_str = "data:image/png;base64,"
    img_str += base64.b64encode(image_png).decode('utf-8')
    
    # Close the figure to free memory
    plt.close(fig)
    
    return img_str

def generate_personalized_insights(universities, user_profile):
    """Generate personalized insights based on user profile for each university"""
    insights = {}
    
    for uni in universities:
        uni_insights = []
        
        # Check major match
        if 'preferred_majors' in user_profile and user_profile['preferred_majors']:
            uni_majors = uni.get('major_strengths', '').lower().split(',')
            user_majors = [m.lower() for m in user_profile['preferred_majors']]
            matching_majors = [m for m in user_majors if any(m in unm for unm in uni_majors)]
            
            if matching_majors:
                uni_insights.append({
                    'type': 'positive',
                    'category': 'academic',
                    'text': f"Offers your preferred major(s): {', '.join(matching_majors)}"
                })
            else:
                uni_insights.append({
                    'type': 'negative',
                    'category': 'academic',
                    'text': "Doesn't directly offer your preferred majors"
                })
        
        # Check financial fit
        if 'budget' in user_profile and user_profile['budget']:
            tuition = uni.get('tuition_fee', 0)
            aid_percent = uni.get('scholarship_percentage', 0)
            est_cost = tuition * (1 - (aid_percent / 100))
            
            if est_cost <= user_profile['budget']:
                uni_insights.append({
                    'type': 'positive',
                    'category': 'financial',
                    'text': f"Affordable with your budget (Est. cost: ${est_cost:,.0f})"
                })
            elif est_cost <= user_profile['budget'] * 1.2:
                uni_insights.append({
                    'type': 'neutral',
                    'category': 'financial',
                    'text': f"Slightly over your budget (Est. cost: ${est_cost:,.0f})"
                })
            else:
                uni_insights.append({
                    'type': 'negative',
                    'category': 'financial',
                    'text': f"Significantly exceeds your budget (Est. cost: ${est_cost:,.0f})"
                })
        
        # Check location preference
        if 'preferred_locations' in user_profile and user_profile['preferred_locations']:
            uni_location = uni.get('location', '').lower()
            uni_region = uni.get('region', '').lower()
            preferred_locations = [loc.lower() for loc in user_profile['preferred_locations']]
            
            if any(loc in uni_location or loc in uni_region for loc in preferred_locations):
                uni_insights.append({
                    'type': 'positive',
                    'category': 'location',
                    'text': f"Located in your preferred region: {uni.get('location', '')}"
                })
        
        # Check campus environment
        if 'preferred_environment' in user_profile and user_profile['preferred_environment']:
            uni_environment = uni.get('environment', '')
            
            if uni_environment.lower() == user_profile['preferred_environment'].lower():
                uni_insights.append({
                    'type': 'positive',
                    'category': 'campus',
                    'text': f"Matches your preferred {uni_environment} campus environment"
                })
        
        # Check academic competitiveness
        if 'gpa' in user_profile and 'sat_score' in user_profile:
            user_gpa = user_profile['gpa']
            user_sat = user_profile['sat_score']
            acceptance_rate = uni.get('acceptance_rate', 50)
            
            # Simplified academic competitiveness check
            if acceptance_rate < 10:
                if user_gpa >= 3.9 and user_sat >= 1500:
                    uni_insights.append({
                        'type': 'neutral',
                        'category': 'academic',
                        'text': "Highly competitive, but your academic stats are strong"
                    })
                else:
                    uni_insights.append({
                        'type': 'negative',
                        'category': 'academic',
                        'text': "Very competitive admission - consider as a reach school"
                    })
            elif acceptance_rate < 30:
                if user_gpa >= 3.7 and user_sat >= 1400:
                    uni_insights.append({
                        'type': 'positive',
                        'category': 'academic',
                        'text': "Your academic profile is competitive for this university"
                    })
                else:
                    uni_insights.append({
                        'type': 'neutral',
                        'category': 'academic',
                        'text': "Moderately competitive - consider as a target/reach school"
                    })
            else:
                if user_gpa >= 3.0 and user_sat >= 1200:
                    uni_insights.append({
                        'type': 'positive',
                        'category': 'academic',
                        'text': "Your academic profile is well above average for this school"
                    })
                else:
                    uni_insights.append({
                        'type': 'neutral',
                        'category': 'academic',
                        'text': "Your profile suggests this could be a good target school"
                    })
        
        insights[uni['id']] = uni_insights
    
    return insights

if __name__ == '__main__':
    app.run(debug=True, threaded=True) 