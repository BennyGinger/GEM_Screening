import time
import requests
import logging


logger = logging.getLogger(__name__)

def make_request_with_retry(url: str, payload: dict, operation_name: str, 
                           max_retries: int = 3, base_timeout: int = 30, 
                           timeout_increment: int = 15) -> requests.Response:
    """
    Make a POST request with retry logic and progressive timeouts.
    
    Args:
        url: The URL to make the request to
        payload: The JSON payload to send
        operation_name: Human-readable name for logging (e.g., "process", "background subtraction")
        max_retries: Maximum number of retry attempts
        base_timeout: Base timeout in seconds
        timeout_increment: Additional timeout per retry attempt
        
    Returns:
        requests.Response: The successful response
        
    Raises:
        requests.exceptions.RequestException: If all retries fail
    """
    timeout = base_timeout  # Ensure timeout is always defined
    for attempt in range(max_retries):
        try:
            timeout = base_timeout + (attempt * timeout_increment)
            resp = requests.post(url, json=payload, timeout=timeout)
            resp.raise_for_status()
            return resp
        except requests.exceptions.ReadTimeout:
            if attempt == max_retries - 1:
                logger.error(f"{operation_name} request timed out after {max_retries} attempts "
                           f"(final timeout: {timeout}s)")
                raise
            else:
                wait_time = 2 ** attempt
                logger.warning(f"{operation_name} request timed out (attempt {attempt + 1}/{max_retries}, "
                             f"timeout: {timeout}s). Retrying in {wait_time}s...")
                time.sleep(wait_time)
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                logger.error(f"{operation_name} request failed after {max_retries} attempts: {e}")
                raise
            else:
                wait_time = 2 ** attempt
                logger.warning(f"{operation_name} request failed (attempt {attempt + 1}/{max_retries}): {e}. "
                             f"Retrying in {wait_time}s...")
                time.sleep(wait_time)
    raise requests.exceptions.RequestException(f"{operation_name} failed after {max_retries} attempts.")