import os
import logging
import requests
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MailchimpClient:
    def __init__(self):
        self.api_key = os.environ.get('MAILCHIMP_API_KEY')
        self.list_id = os.environ.get('MAILCHIMP_LIST_ID')
        self.dc = os.environ.get('MAILCHIMP_DC')

        # Log configuration (without exposing sensitive data)
        logger.info("Initializing MailchimpClient")
        logger.debug(f"Using data center: {self.dc}")
        logger.debug(f"Using list ID: {self.list_id}")
        logger.debug(f"API key present: {bool(self.api_key)}")

        if not all([self.api_key, self.list_id, self.dc]):
            missing = []
            if not self.api_key: missing.append('MAILCHIMP_API_KEY')
            if not self.list_id: missing.append('MAILCHIMP_LIST_ID')
            if not self.dc: missing.append('MAILCHIMP_DC')
            logger.error(f"Missing environment variables: {', '.join(missing)}")
            raise ValueError("Missing required Mailchimp configuration")

        self.base_url = f"https://{self.dc}.api.mailchimp.com/3.0"
        self.headers = {
            "Authorization": f"apikey {self.api_key}",
            "Content-Type": "application/json"
        }

    def _get_member_hash(self, email: str) -> str:
        """Get MD5 hash of lowercase email address for Mailchimp API."""
        return hashlib.md5(email.lower().encode()).hexdigest()

    def add_subscriber(self, email: str, first_name: str, last_name: str = "") -> bool:
        """Add a new subscriber to the Mailchimp audience with their first and last name."""
        try:
            # Prepare subscriber data with separate first and last name fields
            subscriber_data = {
                "email_address": email,
                "status": "subscribed",
                "merge_fields": {
                    "FNAME": first_name.strip(),
                    "LNAME": last_name.strip()
                },
                "tags": ["Scribl"]  # Add Scribl tag during subscription
            }

            # Add or update subscriber
            member_hash = self._get_member_hash(email)
            url = f"{self.base_url}/lists/{self.list_id}/members/{member_hash}"

            logger.info(f"Adding/updating subscriber {email} ({first_name} {last_name}) with Scribl tag")
            response = requests.put(url, headers=self.headers, json=subscriber_data)

            if response.status_code in (200, 201):
                logger.info(f"Successfully added/updated {email} with name: {first_name} {last_name}")
                return True
            else:
                try:
                    error_data = response.json()
                    logger.error(f"Failed to add subscriber. Status: {response.status_code}")
                    logger.error(f"Error response: {error_data}")
                except ValueError:
                    logger.error(f"Failed to add subscriber. Non-JSON response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error adding subscriber {email}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                logger.error(f"Error response content: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding subscriber {email}: {str(e)}")
            return False

    def add_scribl_used_tag(self, email: str) -> bool:
        """Add 'Scribl Used' tag to a member when they first use image processing."""
        try:
            member_hash = self._get_member_hash(email)
            url = f"{self.base_url}/lists/{self.list_id}/members/{member_hash}/tags"

            tag_data = {
                "tags": [{
                    "name": "Scribl Used",
                    "status": "active"
                }]
            }

            logger.info(f"Adding 'Scribl Used' tag to {email}")
            response = requests.post(url, headers=self.headers, json=tag_data)

            if response.status_code == 204:  # Mailchimp returns 204 for successful tag operations
                logger.info(f"Successfully added 'Scribl Used' tag to {email}")
                return True
            else:
                try:
                    error_data = response.json()
                    logger.error(f"Failed to add tag. Status: {response.status_code}")
                    logger.error(f"Error response: {error_data}")
                except ValueError:
                    logger.error(f"Failed to add tag. Non-JSON response: {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error adding tag to {email}: {str(e)}")
            if hasattr(e, 'response') and e.response is not None and hasattr(e.response, 'text'):
                logger.error(f"Error response content: {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error adding tag to {email}: {str(e)}")
            return False

def add_user_to_mailchimp(email: str, first_name: str, last_name: str = "") -> bool:
    """Add a new user to Mailchimp audience when they sign up."""
    try:
        client = MailchimpClient()
        return client.add_subscriber(email, first_name, last_name)
    except Exception as e:
        logger.error(f"Failed to initialize Mailchimp client: {str(e)}")
        return False

def tag_user_first_analysis(email: str) -> bool:
    """Tag a user with 'Scribl Used' when they perform their first analysis."""
    try:
        client = MailchimpClient()
        return client.add_scribl_used_tag(email)
    except Exception as e:
        logger.error(f"Failed to initialize Mailchimp client: {str(e)}")
        return False