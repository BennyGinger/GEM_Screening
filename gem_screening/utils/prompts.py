from gem_screening.utils.prompt_gui import prompt_gui_with_fallback, PipelineQuit


def prompt_to_continue(prompt: str) -> bool:
    """
    Prompt the user for a yes or quit response using GUI or terminal.
    Returns True for continue, raises PipelineQuit for quit.
    Args:
        prompt (str): The prompt message to display to the user.
    Returns:
        bool: True if the user wants to continue.
    Raises:
        PipelineQuit: If the user chooses to quit.
    """
    return prompt_gui_with_fallback(prompt, use_gui=True)


# Prompt shown just before you begin scanning
FOCUS_PROMPT = "Did you focus on the cells?"

ADD_LIGAND_PROMPT = "Did you add the ligand?"