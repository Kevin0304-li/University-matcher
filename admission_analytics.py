from typing import Dict, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime


class AdmissionRateCalculator:
    """
    Class for calculating accurate admission rates with advanced data handling
    """
    
    def __init__(self):
        self.applications = []
        self.application_statuses = ["admitted", "rejected", "pending", "incomplete"]
    
    def load_applications(self, applications: List[Dict]):
        """Load application data with validation and cleaning"""
        # Validate and clean data
        validated_apps = []
        seen_applicants = set()  # For deduplication
        
        for app in applications:
            # Check for required fields
            if not all(key in app for key in ["applicant_id", "status", "program", "submission_date"]):
                continue
                
            # Handle duplicates (same applicant applying to same program)
            app_key = (app["applicant_id"], app["program"])
            if app_key in seen_applicants:
                continue
                
            seen_applicants.add(app_key)
            validated_apps.append(app)
            
        self.applications = validated_apps
        return len(validated_apps)
    
    def _get_effective_applications(self, category_filters=None, exclude_incomplete=True):
        """Get filtered applications based on category and completeness"""
        filtered_apps = self.applications
        
        # Apply category filters if provided
        if category_filters:
            filtered_apps = [app for app in filtered_apps if all(
                app.get(key) == value for key, value in category_filters.items()
            )]
        
        # Exclude incomplete applications if requested
        if exclude_incomplete:
            filtered_apps = [app for app in filtered_apps if app["status"] != "incomplete"]
            
        return filtered_apps
    
    def calculate_admission_rate(self, category_filters=None, exclude_incomplete=True, 
                                cutoff_date=None) -> Tuple[float, Dict]:
        """
        Calculate admission rate with detailed breakdown
        
        Args:
            category_filters: Dict of filters to apply (e.g. {"program": "Computer Science"})
            exclude_incomplete: Whether to exclude incomplete applications
            cutoff_date: Only consider applications before this date
            
        Returns:
            Tuple of (admission_rate, details_dict)
        """
        filtered_apps = self._get_effective_applications(category_filters, exclude_incomplete)
        
        # Apply cutoff date if provided
        if cutoff_date:
            filtered_apps = [app for app in filtered_apps if 
                            datetime.strptime(app["submission_date"], "%Y-%m-%d") <= cutoff_date]
        
        # Count by status
        status_counts = {status: 0 for status in self.application_statuses}
        for app in filtered_apps:
            if app["status"] in status_counts:
                status_counts[app["status"]] += 1
        
        # Calculate admission rate
        total_valid = sum(status_counts.values())
        if total_valid == 0:
            return 0.0, {"error": "No valid applications found"}
        
        admission_rate = status_counts["admitted"] / total_valid * 100
        
        # Prepare detailed results
        details = {
            "total_applications": len(self.applications),
            "filtered_applications": len(filtered_apps),
            "status_breakdown": status_counts,
            "admission_rate": admission_rate
        }
        
        return admission_rate, details
    
    def calculate_stratified_rates(self, stratify_by: str) -> Dict:
        """
        Calculate admission rates stratified by a given category
        
        Args:
            stratify_by: Field to stratify by (e.g. "program", "region")
            
        Returns:
            Dict of categories with their admission rates
        """
        # Identify all unique categories
        categories = set(app.get(stratify_by, "Unknown") for app in self.applications)
        
        # Calculate rate for each category
        results = {}
        for category in categories:
            if category == "Unknown":
                continue
                
            category_filter = {stratify_by: category}
            rate, details = self.calculate_admission_rate(category_filters=category_filter)
            
            results[category] = {
                "admission_rate": rate,
                "details": details
            }
        
        # Calculate overall rate for comparison
        overall_rate, overall_details = self.calculate_admission_rate()
        results["overall"] = {
            "admission_rate": overall_rate,
            "details": overall_details
        }
        
        return results
    
    def analyze_trends(self, time_field="submission_date", interval="month") -> Dict:
        """
        Analyze admission rate trends over time
        
        Args:
            time_field: Field containing date information
            interval: Time interval for grouping ("day", "week", "month", "year")
            
        Returns:
            Dict with time periods and corresponding rates
        """
        if not self.applications:
            return {"error": "No application data loaded"}
            
        # Convert to DataFrame for easier time-based analysis
        df = pd.DataFrame(self.applications)
        
        # Convert date strings to datetime
        df[time_field] = pd.to_datetime(df[time_field])
        
        # Group by time interval
        if interval == "day":
            df['period'] = df[time_field].dt.date
        elif interval == "week":
            df['period'] = df[time_field].dt.to_period('W').apply(lambda x: str(x))
        elif interval == "month":
            df['period'] = df[time_field].dt.to_period('M').apply(lambda x: str(x))
        else:  # year
            df['period'] = df[time_field].dt.year
            
        # Calculate rates for each period
        results = {}
        for period, group in df.groupby('period'):
            period_apps = group.to_dict('records')
            calculator = AdmissionRateCalculator()
            calculator.load_applications(period_apps)
            rate, details = calculator.calculate_admission_rate()
            
            results[str(period)] = {
                "admission_rate": rate,
                "application_count": len(period_apps),
                "admitted_count": details["status_breakdown"]["admitted"]
            }
            
        return results
    
    def validate_data_consistency(self) -> Dict:
        """
        Validate data consistency and identify potential issues
        
        Returns:
            Dict with validation results and issues found
        """
        if not self.applications:
            return {"error": "No application data loaded"}
            
        issues = []
        
        # Check for applications with invalid statuses
        invalid_status = [app for app in self.applications 
                         if app.get("status") not in self.application_statuses]
        if invalid_status:
            issues.append({
                "type": "invalid_status",
                "count": len(invalid_status),
                "examples": invalid_status[:3]
            })
            
        # Check for missing dates
        missing_dates = [app for app in self.applications if not app.get("submission_date")]
        if missing_dates:
            issues.append({
                "type": "missing_dates",
                "count": len(missing_dates),
                "examples": missing_dates[:3]
            })
            
        # Check status distribution for outliers
        status_counts = {}
        for app in self.applications:
            status = app.get("status")
            if status:
                status_counts[status] = status_counts.get(status, 0) + 1
                
        total = len(self.applications)
        for status, count in status_counts.items():
            if status == "admitted" and (count / total > 0.8 or count / total < 0.05):
                issues.append({
                    "type": "unusual_admission_rate",
                    "rate": count / total * 100,
                    "message": "Unusually high or low admission rate detected"
                })
                
        result = {
            "total_applications": len(self.applications),
            "status_distribution": status_counts,
            "issues_found": len(issues),
            "issues": issues,
            "is_valid": len(issues) == 0
        }
        
        return result 