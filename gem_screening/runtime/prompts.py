from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from gem_screening.runtime.prompt_gui import PipelineQuit, prompt_gui_with_fallback

if TYPE_CHECKING:
    from gem_screening.runtime.interaction import PipelineInteraction


logger = logging.getLogger(__name__)

def prompt_to_continue(
    prompt: str,
    interaction: PipelineInteraction | None = None,
) -> bool:
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
    if interaction is not None:
        if interaction.confirm(prompt):
            return True
        raise PipelineQuit("User chose to quit the pipeline")
    return prompt_gui_with_fallback(prompt, use_gui=True)


# Prompt shown just before you begin scanning
FOCUS_PROMPT = "Did you focus on the cells?"

ADD_LIGAND_PROMPT = "Add the ligand"

def get_ligand_prompt(list_type):
    """
    Generate the ligand addition prompt based on the well grouping type.
    Args:
        list_type (str): The well grouping type ('col', 'row', or 'all').
    Returns:
        str: The prompt message for ligand addition.
    """
    grouping_map = {
            'col': f'{ADD_LIGAND_PROMPT} to column: ',
            'row': f'{ADD_LIGAND_PROMPT} to row: ',
            'well': f'{ADD_LIGAND_PROMPT} to well: ',
            'all': f'{ADD_LIGAND_PROMPT} to all wells'
        }
    prompt_message = grouping_map.get(list_type, f'{ADD_LIGAND_PROMPT} to all wells')
    if list_type not in grouping_map:
        logger.warning(f"Unknown well grouping type: {list_type}. Defaulting to 'all'.")
    return prompt_message
