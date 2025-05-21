def prompt_to_continue(prompt: str) -> bool:
    """
    Prompt the user for a yes or quit response.
    Returns True for any answer other than 'q' (case insensitive).
    Args:
        prompt (str): The prompt message to display to the user.
    Returns:
        bool: True if the user does not want to quit, False if they do.
    """
    
    resp = input(prompt)
    return resp.strip().lower() != 'q'


# Prompt shown just before you begin scanning
FOCUS_PROMPT = (
    "\nDid you focus on the cells? "
    "Press Enter to continue or 'q' and Enter to quit: "
)

ADD_LIGAND_PROMPT = (
    "\nDid you add the ligand? "
    "Press Enter to continue or 'q' and Enter to quit: "
)