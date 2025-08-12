"""
Script to update total_marks_percentage for all existing writing samples
"""
from app import app, db
from models import Writing, CriteriaMark
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_total_marks_percentages():
    """Calculate and store total marks percentages for all writings"""
    with app.app_context():
        # Get all writings
        writings = Writing.query.all()
        logger.info(f"Found {len(writings)} writing samples to update")
        
        updated_count = 0
        for writing in writings:
            # Get all criteria marks for this writing
            criteria_marks = writing.criteria_marks
            
            # Calculate percentage if criteria marks exist
            if criteria_marks:
                total_marks = len(criteria_marks)
                total_score = sum(mark.score for mark in criteria_marks)
                # Max score per criterion is 2, so maximum possible score is total_marks * 2
                percentage = (total_score / (total_marks * 2)) * 100
                
                # Update the writing record
                writing.total_marks_percentage = percentage
                updated_count += 1
                
                logger.info(f"Writing ID {writing.id}: {percentage:.1f}% ({total_score}/{total_marks*2})")
        
        # Commit all changes
        db.session.commit()
        logger.info(f"Updated {updated_count} writing samples with total marks percentages")

if __name__ == "__main__":
    update_total_marks_percentages()