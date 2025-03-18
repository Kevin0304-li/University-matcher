import matplotlib.pyplot as plt
import numpy as np
from typing import List, Dict

class UniversityVisualizer:
    def __init__(self):
        pass
    
    def display_match_table(self, recommendations: List[Dict]):
        """Displays a tabular view of university recommendations"""
        if not recommendations:
            print("No matching universities found.")
            return
        
        # Print header
        print("\n==== TOP UNIVERSITY MATCHES ====")
        print(f"{'University':<40} {'Match %':<10} {'Rank':<8} {'Tuition':<10} {'Acceptance':<10}")
        print("-" * 80)
        
        # Print each university with its score and key metrics
        for uni in recommendations:
            name = uni["name"]
            match_score = f"{uni['match_score']}%"
            rank = f"#{uni['academic_rank']}"
            tuition = f"${uni['tuition_fee']:,}"
            acceptance = f"{uni['acceptance_rate']}%"
            
            print(f"{name:<40} {match_score:<10} {rank:<8} {tuition:<10} {acceptance:<10}")
    
    def plot_comparison_chart(self, universities: List[Dict], metrics=None):
        """Creates a bar chart comparing universities across selected metrics"""
        if not universities:
            print("No universities to compare.")
            return
        
        # Default metrics if none specified
        if not metrics:
            metrics = ["match_score", "academic_rank", "tuition_fee", "acceptance_rate"]
        
        # Prepare data
        names = [uni["name"] for uni in universities]
        data = {}
        
        for metric in metrics:
            if metric == "academic_rank":
                # For rank, lower is better so we invert
                max_rank = max(uni[metric] for uni in universities)
                data[metric] = [max_rank - uni[metric] + 1 for uni in universities]
            elif metric == "tuition_fee":
                # For tuition, lower is better so we invert
                max_tuition = max(uni[metric] for uni in universities)
                data[metric] = [max_tuition - uni[metric] for uni in universities]
            else:
                data[metric] = [uni[metric] for uni in universities]
        
        # Normalize data to 0-1 scale for each metric
        for metric in data:
            max_val = max(data[metric]) if max(data[metric]) > 0 else 1
            data[metric] = [val / max_val for val in data[metric]]
        
        # Create figure
        plt.figure(figsize=(12, 6))
        
        # Number of metrics
        n_metrics = len(metrics)
        bar_width = 0.8 / n_metrics
        index = np.arange(len(names))
        
        # Plot bars for each metric
        for i, metric in enumerate(metrics):
            label = metric.replace("_", " ").title()
            plt.bar(index + i * bar_width, data[metric], bar_width, label=label)
        
        # Customize plot
        plt.xlabel('Universities')
        plt.ylabel('Normalized Score (higher is better)')
        plt.title('University Comparison')
        plt.xticks(index + bar_width * (n_metrics - 1) / 2, names, rotation=45, ha='right')
        plt.legend()
        plt.tight_layout()
        
        # Save the figure
        plt.savefig('university_comparison.png')
        print("Comparison chart saved as 'university_comparison.png'")
    
    def create_radar_chart(self, university: Dict, user_profile: Dict):
        """Creates a radar chart showing how well a university matches different dimensions of a user profile"""
        # Define dimensions to include in radar chart
        dimensions = [
            ("Academic", 0.35),
            ("Financial", 0.30),
            ("Location", 0.15),
            ("Career", 0.15),
            ("Campus", 0.05)
        ]
        
        # Create dummy scores for demonstration
        # In a real implementation, these would be calculated from the match algorithm
        scores = [
            min(university["academic_rank"] / 10, 1.0) * 100,  # Academic score
            max(0, 1 - university["tuition_fee"] / 60000) * 100,  # Financial score
            70,  # Location score (dummy)
            university["job_placement"],  # Career score
            university["diversity_score"] * 100  # Campus score
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
        plt.savefig(f"{university['name']}_radar.png".replace(" ", "_"))
        print(f"Radar chart saved as '{university['name']}_radar.png'.replace(' ', '_')")
        
    def generate_detailed_report(self, university: Dict):
        """Generates a detailed text report about a university"""
        print(f"\n==== DETAILED REPORT: {university['name']} ====")
        print(f"Location: {university['location']}")
        print(f"Environment: {university['environment']}")
        print(f"Climate: {university['climate']}")
        print(f"Academic Ranking: #{university['academic_rank']}")
        print(f"Acceptance Rate: {university['acceptance_rate']}%")
        print(f"Annual Tuition: ${university['tuition_fee']:,}")
        print(f"Scholarship Coverage: {university['scholarship_percent']}%")
        print(f"Job Placement Rate: {university['job_placement']}%")
        print(f"Diversity Score: {university['diversity_score']:.2f} (out of 1.0)")
        print(f"Major Strengths: {university['major_strengths'].replace(',', ', ')}")
        
        if 'match_score' in university:
            print(f"\nOverall Match Score: {university['match_score']}%")
            
        print("\nStrengths:")
        # Identify top 3 strengths based on data
        strengths = []
        if university['academic_rank'] <= 5:
            strengths.append("- Elite academic reputation")
        if university['job_placement'] >= 95:
            strengths.append("- Exceptional job placement")
        if university['scholarship_percent'] >= 75:
            strengths.append("- Strong scholarship opportunities")
        if university['diversity_score'] >= 0.85:
            strengths.append("- Highly diverse campus")
            
        # Add at least one strength if none identified
        if not strengths:
            if university['academic_rank'] <= 15:
                strengths.append("- Strong academic reputation")
            else:
                strengths.append("- Balanced educational experience")
                
        for strength in strengths:
            print(strength) 