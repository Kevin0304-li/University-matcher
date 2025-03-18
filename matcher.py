from typing import List, Dict
from db import UniversityDatabase
import requests
import json
import os
import math
from admission_analytics import AdmissionRateCalculator

class UniversityMatcher:
    def __init__(self, db: UniversityDatabase):
        self.db = db
        self.default_weights = {
            "academic": 0.35,    # Academic match (ranks, acceptance rate)
            "financial": 0.30,   # Financial match (tuition, scholarships)
            "location": 0.15,    # Geographic match
            "career": 0.15,      # Career prospects
            "campus": 0.05       # Campus culture and diversity
        }
        # Deepseek API configuration
        self.use_deepseek = os.environ.get("USE_DEEPSEEK_API", "false").lower() == "true"
        self.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
        self.deepseek_api_url = os.environ.get("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/match")
        
        # Initialize admission calculator
        self.admission_calculator = AdmissionRateCalculator()
    
    def set_weights(self, weights: Dict[str, float]):
        """Updates the weights used for matching"""
        # Normalize weights to ensure they sum to 1
        total = sum(weights.values())
        self.weights = {k: v/total for k, v in weights.items()}
    
    def calculate_match_score_with_deepseek(self, user_profile: Dict, university: Dict) -> float:
        """Calculate match score using Deepseek API"""
        if not self.deepseek_api_key:
            print("Warning: Deepseek API key not set. Using fallback algorithm.")
            return self.calculate_match_score(user_profile, university)
            
        try:
            # Prepare data for API request
            payload = {
                "user_profile": user_profile,
                "university": university
            }
            
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }
            
            # Make API request
            response = requests.post(
                self.deepseek_api_url,
                headers=headers,
                data=json.dumps(payload)
            )
            
            # Check if request was successful
            if response.status_code == 200:
                result = response.json()
                # Assuming API returns a match_score field with value between 0-1
                return result.get("match_score", 0.5)
            else:
                print(f"Deepseek API error: {response.status_code}, {response.text}")
                # Fallback to regular algorithm if API fails
                return self.calculate_match_score(user_profile, university)
                
        except Exception as e:
            print(f"Error calling Deepseek API: {str(e)}")
            # Fallback to regular algorithm if API fails
            return self.calculate_match_score(user_profile, university)
    
    def get_accurate_acceptance_rate(self, university_id: int) -> float:
        """
        Get accurate acceptance rate for a university using the advanced calculator
        
        Args:
            university_id: The ID of the university
            
        Returns:
            Accurate acceptance rate as a percentage
        """
        # Check if we have application data for this university
        university_applications = self.db.get_university_applications(university_id)
        
        if not university_applications:
            # Fallback to stored rate if no application data
            university = self.db.get_university(university_id)
            return self._validate_acceptance_rate(university.get("acceptance_rate", 0.0))
        
        # Load and validate application data
        self.admission_calculator.load_applications(university_applications)
        
        # Validate data consistency
        validation_result = self.admission_calculator.validate_data_consistency()
        if not validation_result.get("is_valid", False):
            print(f"Warning: Data consistency issues for university {university_id}: {validation_result['issues']}")
        
        # Calculate accurate admission rate
        admission_rate, details = self.admission_calculator.calculate_admission_rate()
        
        # Validate and adjust the calculated rate
        return self._validate_acceptance_rate(admission_rate)
    
    def _validate_acceptance_rate(self, rate: float) -> float:
        """
        Validate and adjust acceptance rate to ensure it's within realistic bounds
        
        Args:
            rate: The raw acceptance rate as a percentage
            
        Returns:
            Adjusted acceptance rate
        """
        # Handle None values
        if rate is None:
            return 50.0  # Default to average
        
        # Check for decimal errors (e.g., 0.35 instead of 35%)
        if rate < 1.0 and rate > 0:
            # Likely a decimal (e.g. 0.35 instead of 35%)
            rate = rate * 100
        
        # Check for inverted percentage (e.g., 95% rejection = 5% acceptance)
        if rate > 95:
            # Very high rates are likely inverted (e.g., selectivity vs acceptance)
            rate = 100 - rate
        
        # Ensure rate is within realistic bounds
        if rate < 1.0:
            # Extremely selective schools still typically have >1% acceptance
            return 1.0
        elif rate > 95.0:
            # Almost no schools have truly open admissions above 95%
            return 95.0
        
        return rate
    
    def calculate_academic_match(self, user_profile: Dict, university: Dict) -> float:
        """Calculate the academic compatibility score between user and university"""
        academic_score = 0
        
        # Calculate academic strength based on GPA and SAT
        if "gpa" in user_profile and "sat_score" in user_profile:
            # Enhanced normalization of GPA with non-linear scaling (gives bonus to very high GPAs)
            gpa = user_profile["gpa"]
            if gpa > 4.0:  # Handle weighted GPAs gracefully
                gpa = 4.0
            
            gpa_normalized = (gpa / 4.0) ** 0.8  # Non-linear scaling gives more weight to higher GPAs
            
            # Enhanced SAT normalization with percentile approximation
            sat = user_profile["sat_score"]
            # SAT score percentile approximation (rough mapping of scores to percentiles)
            if sat >= 1500: sat_percentile = 0.99
            elif sat >= 1400: sat_percentile = 0.94
            elif sat >= 1300: sat_percentile = 0.86
            elif sat >= 1200: sat_percentile = 0.74
            elif sat >= 1100: sat_percentile = 0.58
            elif sat >= 1000: sat_percentile = 0.40
            elif sat >= 900: sat_percentile = 0.27
            elif sat >= 800: sat_percentile = 0.15
            else: sat_percentile = max(0.01, sat / 1600 * 0.15)  # Minimum percentile
            
            # Academic strength combines GPA and SAT with greater weight to GPA
            academic_strength = (gpa_normalized * 0.6) + (sat_percentile * 0.4)
            
            # Get university rank and scale it properly
            academic_rank = university.get("academic_rank")
            
            # Handle None values or invalid ranks for academic_rank
            if academic_rank is None or not isinstance(academic_rank, (int, float)) or academic_rank <= 0:
                # Default to median rank if not available or invalid
                rank_match = 0.5
            else:
                # Validate rank is within reasonable bounds
                # Some ranking systems use higher numbers for better schools,
                # so we'll detect and correct this if needed
                if academic_rank > 1000:
                    # Likely a points-based ranking system, higher is better
                    # Convert to a percentile (assuming max around 1500)
                    rank_match = min(academic_rank / 1500, 1.0)
                else:
                    # Standard ranking, lower is better
                    # Cap at 200 for normalization
                    rank = min(max(1, academic_rank), 200)
                    # Logarithmic rank scaling (difference between #1 and #10 is more significant than #90 and #100)
                    rank_match = 1 - (math.log10(rank) / math.log10(200))
                
            # Use accurate acceptance rate if available
            if "id" in university:
                try:
                    acceptance_rate = self.get_accurate_acceptance_rate(university["id"])
                except Exception as e:
                    # Fallback to stored rate if error occurs
                    acceptance_rate = university.get("acceptance_rate", 50.0)
            else:
                acceptance_rate = university.get("acceptance_rate", 50.0)
                
            # Handle None value for acceptance_rate
            if acceptance_rate is None:
                acceptance_rate = 50.0  # Default to average acceptance rate
                
            # Calculate selectivity match - how well student's credentials align with university's selectivity
            # Uses logistic function for a more gradual transition between match levels
            selectivity_differential = academic_strength - (1 - (acceptance_rate / 100))
            admit_match = 1 / (1 + math.exp(-5 * (selectivity_differential + 0.1)))  # +0.1 gives slight boost
            
            # Combine rank match and admit match (rank is slightly more important)
            academic_score = (rank_match * 0.55) + (admit_match * 0.45)
        
        # Major preferences match with more sophisticated analysis
        if "preferred_majors" in user_profile and university.get("major_strengths"):
            major_strengths = university.get("major_strengths", "")
            
            # Skip if major_strengths is None or empty
            if not major_strengths:
                return academic_score
            
            university_majors = [m.strip().lower() for m in major_strengths.split(",")]
            user_majors = []
            
            # Handle both string and list formats for user majors (for API flexibility)
            if isinstance(user_profile["preferred_majors"], str):
                user_majors = [m.strip().lower() for m in user_profile["preferred_majors"].split(",")]
            else:
                user_majors = [m.strip().lower() for m in user_profile["preferred_majors"]]
            
            # Skip if no valid majors
            if not user_majors:
                return academic_score
            
            # Count exact matches
            exact_matches = sum(1 for major in user_majors if major in university_majors)
            
            # Count partial matches (e.g., "Computer Science" matches with "Computer Engineering")
            partial_matches = 0
            for user_major in user_majors:
                for uni_major in university_majors:
                    # Skip if already counted as exact match
                    if user_major == uni_major:
                        continue
                    
                    # Check for partial matches with shared words
                    user_words = set(user_major.split())
                    uni_words = set(uni_major.split())
                    common_words = user_words.intersection(uni_words)
                    
                    if common_words and len(common_words) / max(len(user_words), len(uni_words)) > 0.3:
                        partial_matches += 0.5  # Half credit for partial matches
            
            # Calculate total match score, giving more weight to exact matches
            total_matches = exact_matches + partial_matches
            major_match_score = min(total_matches / max(len(user_majors), 1), 1.0)
            
            # Combine academic and major scores - increase major importance
            academic_score = (academic_score * 0.65) + (major_match_score * 0.35)
        
        return academic_score
    
    def calculate_financial_match(self, user_profile: Dict, university: Dict) -> float:
        """Calculate the financial compatibility score between user and university"""
        if "budget" not in user_profile:
            return 0.5  # Default mid-range score if no budget specified
            
        budget = user_profile["budget"]
        tuition = university.get("tuition_fee", 0)
        
        # Handle None value for tuition
        if tuition is None:
            tuition = 0
            
        # Enhanced affordability calculation with exponential penalty for exceeding budget
        if tuition <= budget:
            # Under budget - full affordability score with bonus for significant savings
            savings_ratio = max(0, (budget - tuition) / budget) if budget > 0 else 0
            affordability = min(1.0, 0.9 + savings_ratio * 0.1)  # Slight bonus for significant savings
        else:
            # Over budget - exponential penalty based on how much over budget
            overage_ratio = (tuition - budget) / budget if budget > 0 else 1.0
            affordability = max(0, 0.9 * math.exp(-2 * overage_ratio))
        
        # Consider scholarships more intelligently
        scholarship_percent = university.get("scholarship_percent", 0)
        
        # Handle None value for scholarship_percent
        if scholarship_percent is None:
            scholarship_percent = 0
        
        # Calculate effective tuition after typical scholarship
        effective_tuition = tuition * (1 - (scholarship_percent / 100) * 0.5)  # Assume 50% chance of getting average scholarship
        
        # Calculate secondary affordability score with scholarships
        if effective_tuition <= budget:
            scholarship_affordability = min(1.0, 0.9 + (budget - effective_tuition) / budget * 0.1) if budget > 0 else 0.9
        else:
            overage_ratio = (effective_tuition - budget) / budget if budget > 0 else 1.0
            scholarship_affordability = max(0, 0.9 * math.exp(-2 * overage_ratio))
        
        # Return weighted combination of raw affordability and scholarship-adjusted affordability
        return (affordability * 0.6) + (scholarship_affordability * 0.4)
    
    def calculate_location_match(self, user_profile: Dict, university: Dict) -> float:
        """
        Calculate how well a university's location matches user preferences
        
        Args:
            user_profile: Dictionary with user preferences
            university: Dictionary with university data
            
        Returns:
            Match score as a percentage (0-100)
        """
        # Default if no preferences
        if not user_profile.get("preferred_locations"):
            return 70  # Neutral score
        
        match_score = 0
        max_score = 0
        
        # Universities's location components
        uni_location = university.get("location", "")
        uni_environment = university.get("environment", "")
        uni_climate = university.get("climate", "")
        uni_region = university.get("region", "")
        uni_country = university.get("country", "")
        
        # Extract user location preferences
        preferred_locations = user_profile["preferred_locations"]
        if isinstance(preferred_locations, str):
            preferred_locations = [loc.strip() for loc in preferred_locations.split(',')]
        
        # Preferred environment from user profile
        preferred_environment = user_profile.get("preferred_environment", "")
        
        # Preferred region and country
        preferred_region = user_profile.get("preferred_region", "")
        preferred_country = user_profile.get("preferred_country", "")
        
        # Country match
        if preferred_country and uni_country:
            if preferred_country == uni_country:
                match_score += 25
                
        # Regional match
        if uni_region and preferred_region:
            if uni_region == preferred_region:
                match_score += 30
            # Partial region match (same country, different region)
            elif uni_country and preferred_country and uni_country == preferred_country:
                match_score += 15
                
        # Location text match
        location_match = False
        for loc in preferred_locations:
            if loc.lower() in uni_location.lower():
                location_match = True
                match_score += 25
                break
        
        # City/state match if no direct match found
        if not location_match and preferred_locations:
            # Check if any city/state components match
            for loc in preferred_locations:
                location_components = loc.lower().split(", ")
                uni_location_components = uni_location.lower().split(", ")
                
                for component in location_components:
                    if component in uni_location_components:
                        match_score += 15
                        break
        
        # Environment match
        if preferred_environment and uni_environment:
            if preferred_environment.lower() == uni_environment.lower():
                match_score += 20
            # Partial environment matches
            elif (("Urban" in preferred_environment and "Suburban" in uni_environment) or
                 ("Suburban" in preferred_environment and "Urban" in uni_environment)):
                match_score += 10
            elif (("Rural" in preferred_environment and "College town" in uni_environment) or
                 ("College town" in preferred_environment and "Rural" in uni_environment)):
                match_score += 10
                
        # Calculate final score (max possible score is 100)
        total_score = min(100, match_score)
            
        return total_score
    
    def calculate_career_prospects_match(self, user_profile: Dict, university: Dict) -> float:
        """Calculate the career prospects compatibility score"""
        # Base job placement rate
        job_placement = university.get("job_placement", 80)  # Default to 80% if not specified
        
        # Handle None value
        if job_placement is None:
            job_placement = 80
            
        job_placement_score = job_placement / 100
        
        # Adjust based on major-specific career outcomes (if we have user's preferred majors)
        if "preferred_majors" in user_profile and university.get("major_strengths"):
            major_strengths = university.get("major_strengths", "")
            
            # Handle None value
            if major_strengths is None:
                major_strengths = ""
                
            university_majors = [m.strip().lower() for m in major_strengths.split(",") if m.strip()]
            
            user_majors = []
            if isinstance(user_profile["preferred_majors"], str):
                user_majors = [m.strip().lower() for m in user_profile["preferred_majors"].split(",")]
            else:
                user_majors = [m.strip().lower() for m in user_profile["preferred_majors"]]
            
            # Check how well the university's major strengths align with user preferences
            major_matches = 0
            if user_majors and university_majors:
                major_matches = sum(1 for major in user_majors if any(major in uni_major or uni_major in major for uni_major in university_majors))
            major_match_ratio = major_matches / max(len(user_majors), 1) if user_majors else 0
            
            # Adjust job placement score based on major match (boost if strong match in majors)
            job_placement_score = job_placement_score * (0.8 + 0.2 * major_match_ratio)
        
        return min(job_placement_score, 1.0)
    
    def calculate_campus_match(self, user_profile: Dict, university: Dict) -> float:
        """
        Calculate how well a university's campus matches user preferences
        
        Args:
            user_profile: Dictionary with user preferences
            university: Dictionary with university data
            
        Returns:
            Match score as a percentage (0-100)
        """
        base_score = 70  # Start with a neutral score
        
        # Match campus environment and type
        preferred_environment = user_profile.get("preferred_environment", "")
        university_environment = university.get("environment", "")
        
        if preferred_environment and university_environment:
            if preferred_environment.lower() == university_environment.lower():
                base_score += 20
            # Partial matches for similar environments
            elif (preferred_environment.lower() in university_environment.lower() or 
                  university_environment.lower() in preferred_environment.lower()):
                base_score += 10
                
        # Match campus size if specified in user profile
        preferred_size = user_profile.get("preferred_size", "")
        campus_size = university.get("campus_size", "")
        
        if preferred_size and campus_size:
            if preferred_size == campus_size:
                base_score += 20
            # Handle partial size matches
            elif ("Small" in preferred_size and "Small" in campus_size) or \
                 ("Medium" in preferred_size and "Medium" in campus_size) or \
                 ("Large" in preferred_size and ("Large" in campus_size or "Very Large" in campus_size)):
                base_score += 10
                
        # Consider university type match
        preferred_type = user_profile.get("preferred_university_type", "")
        university_type = university.get("university_type", "")
        
        if preferred_type and university_type:
            if preferred_type == university_type:
                base_score += 20
                
        # Consider religious affiliation if specified
        preferred_religious = user_profile.get("preferred_religious_affiliation", "")
        university_religious = university.get("religious_affiliation", "")
        
        if preferred_religious:
            if preferred_religious == "None" and not university_religious:
                base_score += 10
            elif preferred_religious != "None" and university_religious == preferred_religious:
                base_score += 10
                
        # Diversity factor consideration
        diversity_score = university.get("diversity_score", 0.7)  # Default is medium diversity
        
        # Handle None value for diversity_score
        if diversity_score is None:
            diversity_score = 0.7
            
        base_score += 10 * diversity_score  # Higher diversity adds up to 10 points
        
        # Cap at 100%
        return min(100, base_score)
    
    def calculate_match_score(self, user_profile: Dict, university: Dict, weights=None) -> float:
        """Calculates a match score between a user profile and a university"""
        # Use custom weights if provided, otherwise use default
        weights = weights or self.default_weights
        
        # Calculate individual component scores using enhanced methods
        academic_score = self.calculate_academic_match(user_profile, university)
        financial_score = self.calculate_financial_match(user_profile, university)
        location_score = self.calculate_location_match(user_profile, university)
        career_score = self.calculate_career_prospects_match(user_profile, university)
        campus_score = self.calculate_campus_match(user_profile, university)
        
        # Combine scores according to weights
        total_score = 0
        if "academic" in weights:
            total_score += academic_score * weights["academic"]
        if "financial" in weights:
            total_score += financial_score * weights["financial"]
        if "location" in weights:
            total_score += location_score * weights["location"]
        if "career" in weights:
            total_score += career_score * weights["career"]
        if "campus" in weights:
            total_score += campus_score * weights["campus"]
        
        # Apply final sigmoid normalization to ensure scores are well-distributed
        # between 0-1 with a concentration around 0.5 for better discrimination
        normalized_score = 1 / (1 + math.exp(-6 * (total_score - 0.5)))
        
        # Ensure score is between 0 and 1
        return min(max(normalized_score, 0), 1)
    
    def get_recommendations(self, user_profile: Dict, weights=None, top_n=5) -> List[Dict]:
        """Returns a list of recommended universities based on the user profile"""
        # Dynamic weights based on user profile if not explicitly provided
        if weights is None and "importance_weights" in user_profile:
            weights = {
                "academic": user_profile["importance_weights"].get("academic", 0.35),
                "financial": user_profile["importance_weights"].get("financial", 0.30),
                "location": user_profile["importance_weights"].get("location", 0.15),
                "career": user_profile["importance_weights"].get("career", 0.15),
                "campus": user_profile["importance_weights"].get("campus", 0.05)
            }
            # Normalize weights
            total = sum(weights.values())
            if total > 0:  # Avoid division by zero
                weights = {k: v/total for k, v in weights.items()}
            else:
                weights = self.default_weights
        
        all_unis = self.db.get_all_universities()
        scored_unis = []
        seen_names = set()  # Track university names to avoid duplicates
        
        # Pre-filter universities if we have strong constraints
        filtered_unis = all_unis
        if "budget" in user_profile and user_profile.get("strict_budget", False):
            max_budget = user_profile["budget"] * 1.2  # Allow 20% over budget
            filtered_unis = [uni for uni in all_unis if uni.get("tuition_fee") is not None and uni["tuition_fee"] <= max_budget]
        
        for uni in filtered_unis:
            # Skip if we've already seen this university name or if university data is invalid
            if not uni or "name" not in uni or uni["name"] in seen_names:
                continue
            
            try:
                # Use Deepseek API if enabled, otherwise use regular algorithm
                if self.use_deepseek:
                    score = self.calculate_match_score_with_deepseek(user_profile, uni)
                else:
                    score = self.calculate_match_score(user_profile, uni, weights)
                    
                # Validate score before adding
                if not isinstance(score, (int, float)) or math.isnan(score):
                    print(f"Warning: Invalid score for {uni.get('name', 'Unknown')}")
                    continue
                    
                # Ensure score is within valid range
                score = min(max(score, 0), 1)
                    
                scored_unis.append((uni, score))
                seen_names.add(uni["name"])
            except Exception as e:
                print(f"Error scoring university {uni.get('name', 'Unknown')}: {e}")
                continue
        
        # Sort by score in descending order
        scored_unis.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N results with scores and component scores for more transparency
        recommendations = []
        for uni, score in scored_unis[:top_n]:
            try:
                uni_with_score = uni.copy()
                uni_with_score["match_score"] = round(score * 100, 1)  # Convert to percentage and round
                
                # Add component scores for transparency
                if not self.use_deepseek:
                    # Calculate component scores
                    academic = self.calculate_academic_match(user_profile, uni)
                    financial = self.calculate_financial_match(user_profile, uni)
                    location = self.calculate_location_match(user_profile, uni) / 100  # Convert from 0-100 to 0-1
                    career = self.calculate_career_prospects_match(user_profile, uni)
                    campus = self.calculate_campus_match(user_profile, uni) / 100  # Convert from 0-100 to 0-1
                    
                    # Ensure all scores are valid and within range
                    uni_with_score["component_scores"] = {
                        "academic": round(min(max(academic, 0), 1) * 100, 1),
                        "financial": round(min(max(financial, 0), 1) * 100, 1),
                        "location": round(min(max(location, 0), 1) * 100, 1),
                        "career": round(min(max(career, 0), 1) * 100, 1),
                        "campus": round(min(max(campus, 0), 1) * 100, 1)
                    }
                
                # Add accurate acceptance rate if available
                if "id" in uni:
                    try:
                        uni_with_score["accurate_acceptance_rate"] = self.get_accurate_acceptance_rate(uni["id"])
                    except Exception as e:
                        print(f"Error getting acceptance rate for {uni.get('name', 'Unknown')}: {e}")
                        uni_with_score["accurate_acceptance_rate"] = uni.get("acceptance_rate", 50.0)
                    
                recommendations.append(uni_with_score)
            except Exception as e:
                print(f"Error processing university {uni.get('name', 'Unknown')} for recommendations: {e}")
                continue
            
        return recommendations
    
    def match_universities(self, user_profile: Dict, universities: List[Dict]) -> List[Dict]:
        """
        Match a list of universities to a user profile and return them with match scores

        Args:
            user_profile: Dictionary with user preferences
            universities: List of university dictionaries
            
        Returns:
            List of universities with match_score and component_scores added
        """
        result = []
        
        # Use provided weights or default weights
        weights = getattr(self, 'weights', self.default_weights)
        
        for university in universities:
            # Skip if university is None or empty
            if not university:
                continue
                
            try:
                # Calculate match score and component scores
                if self.use_deepseek and self.deepseek_api_key:
                    match_score = self.calculate_match_score_with_deepseek(user_profile, university)
                    
                    # Add component scores (estimated when using API)
                    component_scores = {
                        "academic": self.calculate_academic_match(user_profile, university),
                        "financial": self.calculate_financial_match(user_profile, university),
                        "location": self.calculate_location_match(user_profile, university) / 100,  # Convert from 0-100 to 0-1
                        "career": self.calculate_career_prospects_match(user_profile, university),
                        "campus": self.calculate_campus_match(user_profile, university) / 100  # Convert from 0-100 to 0-1
                    }
                else:
                    # Calculate component scores first
                    component_scores = {
                        "academic": self.calculate_academic_match(user_profile, university),
                        "financial": self.calculate_financial_match(user_profile, university),
                        "location": self.calculate_location_match(user_profile, university) / 100,  # Convert from 0-100 to 0-1
                        "career": self.calculate_career_prospects_match(user_profile, university),
                        "campus": self.calculate_campus_match(user_profile, university) / 100  # Convert from 0-100 to 0-1
                    }
                    
                    # Calculate overall match score using component scores and weights
                    match_score = 0
                    for component, score in component_scores.items():
                        weight = weights.get(component, 0.2)  # Default weight 0.2 if not found
                        match_score += score * weight
                
                    # Ensure match score is between 0 and 1
                    match_score = min(max(match_score, 0), 1)
                
                # Add accurate acceptance rate if available
                university_id = university.get('id')
                if university_id:
                    try:
                        university['accurate_acceptance_rate'] = self.get_accurate_acceptance_rate(university_id)
                    except Exception as e:
                        print(f"Error calculating accurate acceptance rate for university {university_id}: {e}")
                        # Use regular acceptance_rate or default value
                        university['accurate_acceptance_rate'] = university.get('acceptance_rate', 50.0)
                
                # Create a copy of the university with match scores added
                university_with_scores = university.copy()
                university_with_scores['match_score'] = round(match_score * 100, 1)  # Convert to percentage and round
                
                # Convert component scores to percentages and ensure they're within 0-100 range
                university_with_scores['component_scores'] = {
                    k: round(min(v * 100, 100), 1) for k, v in component_scores.items()  # Convert to percentages with bounds
                }
                
                result.append(university_with_scores)
                
            except Exception as e:
                print(f"Error matching university {university.get('name', 'Unknown')}: {e}")
                # Skip this university in case of error
                continue
        
        return result 