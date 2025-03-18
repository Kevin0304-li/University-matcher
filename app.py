import os
from db import UniversityDatabase
from matcher import UniversityMatcher
from visualizer import UniversityVisualizer

class UniversityMatcherApp:
    def __init__(self):
        """Initialize the application with its components"""
        self.db = UniversityDatabase()
        self.matcher = UniversityMatcher(self.db)
        self.visualizer = UniversityVisualizer()
        
        # Initialize database with sample data if needed
        self.db.insert_sample_data()
        
        # Store user profile
        self.user_profile = {}
        
        # Store recommendations
        self.recommendations = []
    
    def clear_screen(self):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def get_user_profile(self):
        """Collect user profile information through a questionnaire"""
        self.clear_screen()
        print("===== UNIVERSITY MATCHER =====")
        print("Please answer the following questions to help us find your ideal university matches.\n")
        
        # Academic information
        print("=== ACADEMIC INFORMATION ===")
        try:
            gpa = float(input("What is your GPA (on a 4.0 scale)? "))
            sat_score = int(input("What is your SAT score (out of 1600)? "))
            
            majors = input("What majors are you interested in? (separate with commas) ")
            preferred_majors = [m.strip() for m in majors.split(",") if m.strip()]
            
            # Financial information
            print("\n=== FINANCIAL INFORMATION ===")
            budget = int(input("What is your annual budget for tuition (in USD)? $"))
            
            # Location preferences
            print("\n=== LOCATION PREFERENCES ===")
            locations = input("What locations would you prefer? (cities or states, separate with commas) ")
            preferred_locations = [loc.strip() for loc in locations.split(",") if loc.strip()]
            
            environment = input("What type of environment do you prefer? (Urban, Suburban, Rural, College town) ")
            
            # Set the user profile
            self.user_profile = {
                "gpa": gpa,
                "sat_score": sat_score,
                "preferred_majors": preferred_majors,
                "budget": budget,
                "preferred_locations": preferred_locations,
                "preferred_environment": environment
            }
            
            # Weight preferences
            print("\n=== IMPORTANCE WEIGHTS ===")
            print("Please rate the importance of each factor (1-10):")
            academic_weight = int(input("Academic reputation: "))
            financial_weight = int(input("Affordability: "))
            location_weight = int(input("Location: "))
            career_weight = int(input("Career prospects: "))
            campus_weight = int(input("Campus culture: "))
            
            # Set custom weights
            self.custom_weights = {
                "academic": academic_weight,
                "financial": financial_weight,
                "location": location_weight,
                "career": career_weight,
                "campus": campus_weight
            }
            
            return True
        except ValueError:
            print("Invalid input. Please try again with appropriate values.")
            input("Press Enter to continue...")
            return False
    
    def get_recommendations(self):
        """Generate university recommendations based on user profile"""
        if not self.user_profile:
            print("Please complete your profile first.")
            return
        
        self.recommendations = self.matcher.get_recommendations(
            self.user_profile, 
            self.custom_weights if hasattr(self, 'custom_weights') else None
        )
        
        # Display the results
        self.visualizer.display_match_table(self.recommendations)
    
    def compare_universities(self):
        """Compare selected universities"""
        if not self.recommendations:
            print("Please generate recommendations first.")
            return
        
        print("\n=== COMPARE UNIVERSITIES ===")
        print("Available universities:")
        for i, uni in enumerate(self.recommendations, 1):
            print(f"{i}. {uni['name']}")
        
        try:
            selections = input("\nEnter the numbers of universities to compare (comma separated): ")
            indices = [int(idx.strip()) - 1 for idx in selections.split(",") if idx.strip()]
            
            if any(idx < 0 or idx >= len(self.recommendations) for idx in indices):
                print("Invalid selection. Please try again.")
                return
            
            selected_unis = [self.recommendations[idx] for idx in indices]
            self.visualizer.plot_comparison_chart(selected_unis)
            
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            return
    
    def view_university_details(self):
        """View detailed information about a specific university"""
        if not self.recommendations:
            print("Please generate recommendations first.")
            return
        
        print("\n=== UNIVERSITY DETAILS ===")
        print("Available universities:")
        for i, uni in enumerate(self.recommendations, 1):
            print(f"{i}. {uni['name']}")
        
        try:
            selection = int(input("\nEnter the number of the university to view: ")) - 1
            
            if selection < 0 or selection >= len(self.recommendations):
                print("Invalid selection. Please try again.")
                return
            
            selected_uni = self.recommendations[selection]
            self.visualizer.generate_detailed_report(selected_uni)
            self.visualizer.create_radar_chart(selected_uni, self.user_profile)
            
        except ValueError:
            print("Invalid input. Please enter a number.")
            return
    
    def run(self):
        """Main application loop"""
        while True:
            self.clear_screen()
            print("===== UNIVERSITY MATCHER =====")
            print("1. Create/Update Profile")
            print("2. Get University Recommendations")
            print("3. Compare Universities")
            print("4. View University Details")
            print("5. Exit")
            
            choice = input("\nEnter your choice (1-5): ")
            
            if choice == '1':
                self.get_user_profile()
            elif choice == '2':
                self.get_recommendations()
                input("\nPress Enter to continue...")
            elif choice == '3':
                self.compare_universities()
                input("\nPress Enter to continue...")
            elif choice == '4':
                self.view_university_details()
                input("\nPress Enter to continue...")
            elif choice == '5':
                print("Thank you for using the University Matcher!")
                break
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue...")

# Run the application if this is the main script
if __name__ == "__main__":
    app = UniversityMatcherApp()
    app.run() 