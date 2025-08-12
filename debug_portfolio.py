"""
Debugging script for student portfolio issues
"""
from app import app, db
from models import Writing, CriteriaMark, Student, Criteria, Assignment

def debug_student_portfolio(student_id=48):
    with app.app_context():
        print(f"Debugging portfolio for student ID {student_id}")
        
        # Get the student
        student = Student.query.get(student_id)
        if not student:
            print(f"Error: Student with ID {student_id} not found")
            return
        
        print(f"Student: {student.first_name} {student.last_name}")
        
        # Get writing samples
        writing_samples = Writing.query.filter_by(student_id=student_id).order_by(Writing.created_at.desc()).all()
        print(f"Found {len(writing_samples)} writing samples")
        
        # For each writing sample, check criteria marks
        for i, sample in enumerate(writing_samples):
            print(f"\nSample {i+1}: ID={sample.id}, Filename={sample.filename}")
            print(f"  Assignment: {sample.assignment.title if sample.assignment else 'None'}")
            
            # Check if criteria_marks is loaded
            if hasattr(sample, 'criteria_marks'):
                criteria_marks = sample.criteria_marks
                print(f"  Criteria marks: {len(criteria_marks)}")
                
                # Calculate marks
                if criteria_marks:
                    total_criteria = len(criteria_marks)
                    criteria_met = sum(1 for mark in criteria_marks if mark.score == 2)
                    criteria_partial = sum(1 for mark in criteria_marks if mark.score == 1)
                    
                    if total_criteria > 0:
                        met_percent = (criteria_met / total_criteria * 100)
                        partial_percent = (criteria_partial / total_criteria * 100)
                        total_mark = (met_percent + (partial_percent / 2))
                        
                        print(f"  Met criteria: {criteria_met}/{total_criteria} ({met_percent:.1f}%)")
                        print(f"  Partially met: {criteria_partial}/{total_criteria} ({partial_percent:.1f}%)")
                        print(f"  Total mark: {total_mark:.1f}%")
                    else:
                        print("  Error: Zero total criteria")
                else:
                    print("  Error: No criteria marks")
            else:
                print("  Error: No criteria_marks attribute found")
                
                # Check if marks exist in the database
                db_marks = CriteriaMark.query.filter_by(writing_id=sample.id).all()
                if db_marks:
                    print(f"  Database has {len(db_marks)} criteria marks for this writing")
                    print(f"  Scores: {[mark.score for mark in db_marks]}")
                else:
                    print("  No criteria marks found in database")

if __name__ == "__main__":
    debug_student_portfolio(48)