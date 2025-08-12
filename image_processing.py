import io
import logging

import concurrent.futures
import threading
import time
from openai import OpenAI
import os
import base64
import json
from dotenv import load_dotenv
from models import Assignment
from typing import Optional
logger = logging.getLogger(__name__)


load_dotenv()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def encode_image_to_base64(image_bytes):
    return base64.b64encode(image_bytes).decode('utf-8')


def analyze_writing(base64_image, assignment=None):
    """Hybrid analysis approach for fast, accurate writing assessment.
    Uses a combination of parallel API calls and early results to optimize speed."""
    try:
        start_time = time.time()
        logger.debug("Starting hybrid analysis approach...")
        
        # Build a condensed system prompt for maximum efficiency
        system_prompt = """You are an expert teacher analyzing student writing. Be extremely concise and precise.

        Format EXACTLY like this:
        WRITING AGE: [X years Y months]

        Strengths:
        - Strength 1 (Example: "quote from text")
        - Strength 2 (Example: "quote from text")
        - Strength 3 (Example: "quote from text")

        Areas for Development:
        - Area 1 (Example: "quote from text")
        - Area 2 (Example: "quote from text")
        - Area 3 (Example: "quote from text")

        Keep analysis brief and focused. Each point MUST include a quoted example."""

        if assignment:
            # Add only essential assignment context
            system_prompt += f"""

        Key assessment criteria:
        - {assignment.curriculum} standards
        - {assignment.class_group.year_group if assignment.class_group else 'appropriate year group'} expectations
        - {assignment.genre if assignment.genre else 'writing type'} features
        """

        # Track if we've already returned a result
        result_returned = threading.Event()
        final_response = []
        
        # Function to make rapid API call with optimized settings
        def make_api_call(_):
            if result_returned.is_set():
                logger.debug(f"Skipping API call {_+1} as result already returned")
                return None
                
            try:
                logger.debug(f"Starting API call {_+1}")
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "Analyze this writing quickly. Start with WRITING AGE:"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=600,  # Reduced for faster response
                    temperature=0.3  # More consistent results
                )
                logger.debug(f"Completed API call {_+1}")
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"API call {_+1} error: {str(e)}")
                return None
                
        # Function to process the first valid response separately
        def process_first_response(future):
            result = future.result()
            if result and not result_returned.is_set():
                final_response.append(result)
                # Mark that we have a result to potentially short-circuit other calls
                result_returned.set()
        
        # Launch initial parallel passes with minimal timeout for fast response
        all_responses = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            # Submit first two API calls with callback to process first valid result
            futures = []
            for i in range(3):
                future = executor.submit(make_api_call, i)
                # First future gets special callback to potentially return results early
                if i == 0:
                    future.add_done_callback(process_first_response)
                futures.append(future)
            
            # Wait for all futures with a strict timeout
            completed_futures, _ = concurrent.futures.wait(
                futures, 
                timeout=9,  # 9-second hard timeout
                return_when=concurrent.futures.ALL_COMPLETED
            )
            
            # Process completed results
            for future in completed_futures:
                if future.done():
                    result = future.result()
                    if result and result not in all_responses:
                        all_responses.append(result)
        
        # If we have at least one response from the callback function, use it
        if final_response and not all_responses:
            all_responses = final_response

        # Make sure we got at least one valid response
        if not all_responses:
            logger.error("All API calls failed, no valid responses")
            return {
                'age': 'Error occurred',
                'feedback': 'Error analyzing writing: All API calls failed',
                'justification': '',
                'extracted_text': ''
            }

        # Extract writing ages from each response
        all_ages = []
        for content in all_responses:
            if 'WRITING AGE:' in content.upper():
                age_line = [line for line in content.split('\n') if 'WRITING AGE:' in line.upper()][0]
                age_text = age_line.split(':', 1)[1].strip()
                # Extract years and months
                try:
                    years = int(age_text.split('years')[0].strip())
                    months = int(age_text.split('months')[0].split('years')[1].strip())
                    age_in_months = years * 12 + months
                    all_ages.append(age_in_months)
                except Exception as e:
                    logger.warning(f"Could not parse age from: {age_text} - {str(e)}")

        # Calculate average age
        if all_ages:
            avg_months = sum(all_ages) / len(all_ages)
            avg_years = int(avg_months // 12)
            avg_months_remainder = int(avg_months % 12)
            avg_age = f"{avg_years} years {avg_months_remainder} months"
        else:
            avg_age = "Unable to determine"

        # Process and combine feedback from all passes
        strengths_set = set()
        development_set = set()

        for response in all_responses:
            parts = response.split('\n\n')
            for part in parts:
                if 'Strengths:' in part:
                    points = [p.strip() for p in part.split('\n') if p.strip().startswith('-')]
                    strengths_set.update(points)
                elif 'Areas for Development:' in part:
                    points = [p.strip() for p in part.split('\n') if p.strip().startswith('-')]
                    development_set.update(points)

        # Filter out duplicates and format combined feedback
        strengths_list = sorted(list(set(strengths_set)))[:3]  # Take top 3 unique strengths
        development_list = sorted(list(set(development_set)))[:3]  # Take top 3 unique areas

        # Remove any duplicate points between lists by comparing lowercase versions
        lower_strengths = [s.lower() for s in strengths_list]
        development_list = [d for d in development_list if d.lower() not in lower_strengths]

        # Format combined feedback
        combined_feedback = "Strengths:\n"
        combined_feedback += '\n'.join(strengths_list)
        combined_feedback += "\n\nAreas for Development:\n"
        combined_feedback += '\n'.join(development_list)

        # Initialize analysis structure
        analysis_parts = {
            'age': avg_age,
            'feedback': combined_feedback,
            'justification': '',
            'extracted_text': ''
        }

        # Record time taken and log it
        end_time = time.time()
        time_taken = end_time - start_time
        logger.debug(f"Analysis completed in {time_taken:.2f} seconds with age: {analysis_parts['age']}")

        return analysis_parts

    except Exception as e:
        logger.error(f"Error analyzing writing: {str(e)}")
        return {
            'age': 'Error occurred',
            'feedback': f'Error analyzing writing: {str(e)}',
            'justification': '',
            'extracted_text': ''
        }







client = OpenAI(api_key=os.getenv('OPENAI_API_KEY')) 
MODEL_NAME = "gpt-4o"

def evaluate_criteria(assignment: Assignment, writing_text: str) -> list[dict]:
    """
    Evaluate a writing sample against the criteria of a given assignment using OpenAI.
    
    Args:
        assignment (Assignment): The assignment object with criteria
        writing_text (str): The complete writing text from the student
    
    Returns:
        List[dict]: List of evaluations, each with `criterion`, `score`, and `justification`
    """
    if not assignment or not assignment.criteria:
        logger.warning("No assignment or criteria to evaluate.")
        return []
    
    if assignment:
     
        criteria_prompt = """You are an expert teacher evaluating a writing sample against specific success criteria.

        For each criterion, you must evaluate CONSISTENTLY using these specific scoring guidelines:

        Score 0 = Not met:
        - The required skill/element is completely absent
        - No evidence of attempting the criterion
        - Significant errors that impede understanding

        Score 1 = Partially met:
        - The skill/element is present but inconsistent
        - Basic or limited demonstration of the criterion
        - Some errors but meaning is generally clear

        Score 2 = Confidently used:
        - Consistent and effective use throughout
        - Clear evidence of mastery of the criterion
        - Minimal errors that don't impact understanding

        IMPORTANT SCORING RULES:
        1. Be consistent - similar writing should receive similar scores
        2. Focus on evidence - cite specific examples from the text
        3. Consider age-appropriate expectations
        4. Score each criterion independently
        5. Avoid being influenced by overall impression

        Criteria to evaluate:
        """
    

    criteria_prompt += "\nCriteria to evaluate:\n"
    for crit in assignment.criteria:
        criteria_prompt += f"- {crit.description.strip()}\n"

    criteria_prompt += """
    Analyze the text thoroughly and respond with a JSON object in this exact format:
    {
        "evaluations": [
            {
                "criterion": "exact criterion text",
                "score": number (0, 1, or 2),
                "justification": "MUST include specific examples from the text that justify this score"
            }
        ]
    }

    For each criterion, your justification MUST:
    1. Quote specific examples from the text
    2. Explain why these examples merit the given score
    3. Reference the scoring guidelines above"""

    try:
        logger.debug(f"Evaluating text against criteria for assignment {assignment.id}")
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": criteria_prompt},
                {"role": "user", "content": f"Please evaluate this writing sample against the provided criteria:\n\n{writing_text}"}
            ],
            temperature=0.2,
            max_tokens=1500
        )

        content = response.choices[0].message.content.strip()

        logger.debug(f"OpenAI response: {content[:250]}...")  
        result = json.loads(content)
        return result.get("evaluations", [])
    except Exception as e:
        logger.error(f"evaluate_criteria failed: {str(e)}")
        return []
