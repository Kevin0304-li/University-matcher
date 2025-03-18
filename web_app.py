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

# Initialize database and matcher
db = UniversityDatabase()
db.insert_sample_data()
matcher = UniversityMatcher(db)

# Add a lock for thread safety
db_lock = threading.Lock()

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
            gpa = float(request.form['gpa'])
            sat_score = int(request.form['sat_score'])
            
            majors = request.form['majors']
            preferred_majors = [m.strip() for m in majors.split(",") if m.strip()]
            
            budget = int(request.form['budget'])
            
            locations = request.form['locations']
            preferred_locations = [loc.strip() for loc in locations.split(",") if loc.strip()]
            
            environment = request.form['environment']
            
            # Get weights
            academic_weight = int(request.form['academic_weight'])
            financial_weight = int(request.form['financial_weight'])
            location_weight = int(request.form['location_weight'])
            career_weight = int(request.form['career_weight'])
            campus_weight = int(request.form['campus_weight'])
            
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
            weights = {
                "academic": float(academic_weight),
                "financial": float(financial_weight),
                "location": float(location_weight),
                "career": float(career_weight),
                "campus": float(campus_weight)
            }
            
            # Store in session
            session['user_profile'] = user_profile
            session['weights'] = weights
            
            # Generate recommendations
            return redirect(url_for('recommendations'))
            
        except ValueError:
            error = "Please enter valid values for all fields."
            return render_template('profile.html', error=error)
    
    # For GET requests or if form validation fails
    return render_template('profile.html')

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
    if 'recommendations' not in session:
        return redirect(url_for('recommendations'))
    
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
        
        # Generate comparison chart
        img_str = generate_comparison_chart(selected_unis)
        
        return render_template('comparison_results.html', 
                               universities=selected_unis, 
                               comparison_chart=img_str)
    
    # For GET request, show the selection form
    return render_template('compare.html', recommendations=session['recommendations'])

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

def generate_radar_chart(university):
    """Generate a radar chart for a university and return as base64 string"""
    # Define dimensions
    dimensions = [
        ("Academic", 0.35),
        ("Financial", 0.30),
        ("Location", 0.15),
        ("Career", 0.15),
        ("Campus", 0.05)
    ]
    
    # Create scores (similar to the original visualizer)
    scores = [
        min(university["academic_rank"] / 10, 1.0) * 100,
        max(0, 1 - university["tuition_fee"] / 60000) * 100,
        70,  # Location score (dummy)
        university["job_placement"],
        university["diversity_score"] * 100
    ]
    
    # Create radar chart
    labels = [dim[0] for dim in dimensions]
    angles = np.linspace(0, 2*np.pi, len(labels), endpoint=False).tolist()
    angles += angles[:1]  # Close the loop
    
    scores = scores + scores[:1]  # Close the loop
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    ax.plot(angles, scores, 'o-', linewidth=2)
    ax.fill(angles, scores, alpha=0.25)
    ax.set_thetagrids(np.degrees(angles[:-1]), labels)
    ax.set_ylim(0, 100)
    ax.grid(True)
    
    plt.title(f"Match Profile: {university['name']}")
    
    # Save to BytesIO object
    img = BytesIO()
    plt.savefig(img, format='png')
    plt.close()
    img.seek(0)
    
    # Convert to base64 for embedding in HTML
    img_str = base64.b64encode(img.getvalue()).decode('utf-8')
    
    return img_str

def generate_comparison_chart(universities):
    """Generate an advanced multi-faceted comparison of universities"""
    if not universities or len(universities) < 2:
        return None
    
    # Create a figure with multiple subplots for different visualization types
    fig = plt.figure(figsize=(16, 12))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.2])
    
    # 1. Radar chart for holistic comparison
    ax_radar = fig.add_subplot(gs[0, :], polar=True)
    
    # Key metrics to compare in radar chart (normalized where higher is better)
    radar_metrics = [
        {"name": "Academic Strength", "key": lambda u: 1 - min(u["academic_rank"], 50) / 50},
        {"name": "Affordability", "key": lambda u: 1 - min(u["tuition_fee"], 60000) / 60000},
        {"name": "Selectivity", "key": lambda u: 1 - u.get("accurate_acceptance_rate", u["acceptance_rate"]) / 100},
        {"name": "Career Prospects", "key": lambda u: u["job_placement"] / 100},
        {"name": "Scholarship", "key": lambda u: u["scholarship_percent"] / 100},
        {"name": "Diversity", "key": lambda u: u["diversity_score"]}
    ]
    
    # Compute angles for radar chart
    angles = np.linspace(0, 2*np.pi, len(radar_metrics), endpoint=False).tolist()
    
    # Close the radar plot (connect last point to first)
    angles += angles[:1]
    
    # Plot each university on the radar chart
    labels = [metric["name"] for metric in radar_metrics]
    ax_radar.set_theta_offset(np.pi / 2)
    ax_radar.set_theta_direction(-1)
    ax_radar.set_thetagrids(np.degrees(angles[:-1]), labels)
    
    # Custom colors for each university
    colors = plt.cm.tab10(np.linspace(0, 1, len(universities)))
    
    for i, uni in enumerate(universities):
        values = [metric["key"](uni) for metric in radar_metrics]
        values += values[:1]  # Close the polygon
        
        # Plot the university's profile
        ax_radar.plot(angles, values, 'o-', linewidth=2, color=colors[i], label=uni["name"])
        ax_radar.fill(angles, values, alpha=0.1, color=colors[i])
    
    ax_radar.set_ylim(0, 1)
    ax_radar.set_title("Multidimensional University Profile Comparison", fontsize=14, pad=20)
    ax_radar.legend(loc="upper right", bbox_to_anchor=(0.1, 0.1))
    
    # 2. Bar chart comparing key numeric metrics
    ax_bar = fig.add_subplot(gs[1, 0])
    
    # Metrics for bar chart with direct values (not normalized)
    bar_metrics = [
        {"name": "Match Score (%)", "key": "match_score"},
        {"name": "Academic Rank", "key": "academic_rank", "lower_better": True},
        {"name": "Tuition ($K)", "key": lambda u: u["tuition_fee"] / 1000},
        {"name": "Accept. Rate (%)", "key": lambda u: u.get("accurate_acceptance_rate", u["acceptance_rate"])}
    ]
    
    # Set up positions for grouped bars
    bar_width = 0.8 / len(universities)
    x = np.arange(len(bar_metrics))
    
    for i, uni in enumerate(universities):
        # Extract values for each metric
        values = []
        for metric in bar_metrics:
            if isinstance(metric.get("key"), str):
                val = uni[metric["key"]]
            else:
                val = metric["key"](uni)
            # Invert values where lower is better
            if metric.get("lower_better", False):
                # Use a transformation that preserves relative differences
                max_possible = 50  # For ranks, assume 50 is max we care about
                val = max_possible - min(val, max_possible)
            values.append(val)
        
        # Plot bars for this university
        ax_bar.bar(x + i * bar_width, values, bar_width, color=colors[i], label=uni["name"])
    
    # Customize bar chart
    ax_bar.set_xticks(x + bar_width * (len(universities) - 1) / 2)
    ax_bar.set_xticklabels([m["name"] for m in bar_metrics])
    ax_bar.set_title("Key Metrics Comparison", fontsize=14)
    ax_bar.set_ylabel("Value")
    
    # 3. Table with actual values and statistical comparison
    ax_table = fig.add_subplot(gs[1, 1])
    ax_table.axis('tight')
    ax_table.axis('off')
    
    # Prepare table data with improved formatting
    table_metrics = [
        {"name": "University", "key": "name", "format": "{}"},
        {"name": "Match\nScore", "key": "match_score", "format": "{:.1f}%"},
        {"name": "Rank", "key": "academic_rank", "format": "#{:d}"},
        {"name": "Tuition", "key": "tuition_fee", "format": "${:,}"},
        {"name": "Accept.\nRate", "key": lambda u: u.get("accurate_acceptance_rate", u["acceptance_rate"]), "format": "{:.1f}%"},
        {"name": "Scholar-\nship", "key": "scholarship_percent", "format": "{:.0f}%"},
        {"name": "Job\nPlace", "key": "job_placement", "format": "{:.0f}%"},
        {"name": "Environment", "key": "environment", "format": "{}"}
    ]
    
    # Headers for the table
    table_data = [[metric["name"] for metric in table_metrics]]
    
    # Add data for each university
    for uni in universities:
        row = []
        for metric in table_metrics:
            if isinstance(metric.get("key"), str):
                val = uni[metric["key"]]
            else:
                val = metric["key"](uni)
            row.append(metric["format"].format(val))
        table_data.append(row)
    
    # Create the table with improved styling
    table = ax_table.table(
        cellText=table_data, 
        loc='center', 
        cellLoc='center',
        colWidths=[0.2, 0.1, 0.08, 0.12, 0.1, 0.1, 0.1, 0.2]  # Custom column widths
    )
    
    # Set better styling
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.8)  # Taller rows for better readability
    
    # Apply better styling to all cells
    for i in range(len(table_data)):
        for j in range(len(table_metrics)):
            # Add borders to all cells
            table[(i, j)].set_edgecolor('#cccccc')
            
            # Header row styling
            if i == 0:
                table[(i, j)].set_facecolor('#2c3e50')  # Darker blue
                table[(i, j)].set_text_props(color='white', fontweight='bold')
            # Data row styling - alternate row colors
            elif i % 2 == 0:
                table[(i, j)].set_facecolor('#f8f9fa')  # Light gray for even rows
            else:
                table[(i, j)].set_facecolor('#ffffff')  # White for odd rows
    
    # Apply conditional formatting to highlight best values
    for j in range(1, len(table_metrics)):
        metric = table_metrics[j]
        is_lower_better = j == 2  # Only academic rank is better when lower
        
        # Find best value for this metric
        best_idx = None
        best_val = None
        
        for i, uni in enumerate(universities):
            if isinstance(metric.get("key"), str):
                val = uni[metric["key"]]
            else:
                val = metric["key"](uni)
                
            if best_val is None or (is_lower_better and val < best_val) or (not is_lower_better and val > best_val):
                best_val = val
                best_idx = i
        
        # Highlight the best value
        if best_idx is not None:
            table[(best_idx + 1, j)].set_facecolor('#d4edda')  # Light green
            table[(best_idx + 1, j)].set_text_props(weight='bold')
    
    ax_table.set_title("Detailed Comparison Table", fontsize=14, pad=15)
    
    # Add a summary of the comparison at the top
    plt.suptitle("Advanced University Comparison", fontsize=16, y=0.98)
    
    # Adjust layout
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save chart to BytesIO
    img = BytesIO()
    plt.savefig(img, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    img.seek(0)
    
    # Convert to base64 for embedding in HTML
    img_str = base64.b64encode(img.getvalue()).decode('utf-8')
    
    return img_str

if __name__ == '__main__':
    app.run(debug=True, threaded=True) 