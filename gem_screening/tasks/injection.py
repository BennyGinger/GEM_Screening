from __future__ import annotations # Enable type annotation to be stored as string

import logging
from time import sleep
from typing import TYPE_CHECKING

from a1_manager import A1Manager, StageCoord
from a1_manager.microscope_hardware.nanopick.devices.injection_protocol import PickDevice
from a1_manager.microscope_hardware.nanopick.injection_factory import get_pick_device
from a1_manager.microscope_hardware.nanopick.devices.marZ import MarZ
from gem_screening.settings.models import InjectionSettings, PipelineSettings
from gem_screening.well_data.well_classes import Well

if TYPE_CHECKING:
    from pycromanager import Core


logger = logging.getLogger(__name__)

OFFSET_MAPPING = {
    '96well': 2000, '384well': 500}



class Injection():
    """ 
    Class to control the injection depending on the chosen device: nanopick head or quickpick valve control.
    Args:
        - injection_volume(float): injected volume in microliters
        - injection_time(int): injection time in milliseconds
        - nanopick_dish(str): name of the used dish (e.g.: "96-well")
    """
    
    __slots__ =  'arm', 'injection_device', 'a1_manager'
    
    def __init__(self,  arm: MarZ, injection_device: PickDevice, a1_manager: A1Manager) -> None: 
        
        self.arm = arm
        self.injection_device = injection_device
        self.a1_manager = a1_manager
                
    
    def _ul_to_nl_converter(self, volume_ul: float) -> float:
        """
        Convert volume from microliters to nanoliters.
        """
        return volume_ul*1000
    
    def arm_to_home(self)->None:
        """
        Move to the safe height above the plate.
        """
        return self.arm.to_home()
    
    def arm_to_liquid(self)->None:
        """
        Move to the position in the liquid safely above the cells.
        """
        return self.arm.to_liquid()
        
    def get_arm_position(self)-> float:
        """
        Get the current altitude of the head.
        """
        return self.arm._get_arm_position
    
    def move_to_position(self, well: Well, position: str)-> None:
        #def move_to_position(self, center: StageCoord, position: str)-> None:
        """
        Move the arm to the specified (x, y) coordinates.
        """
        dish_name = self.arm.dish
        offset = OFFSET_MAPPING.get(dish_name, 0)
        
        center = well.center
        
        if position.lower() == "top":
            center['xy'] = [center['xy'][0], center['xy'][1]-offset]
        elif position.lower() == "left":
            center['xy'] = [center['xy'][0]+offset, center['xy'][1]]
        elif position.lower() == "right":
            center['xy'] = [center['xy'][0]-offset, center['xy'][1]]
        elif position.lower() == "bottom":
            center['xy'] = [center['xy'][0], center['xy'][1]+offset]
        elif position.lower() == "middle":
            pass
        return self.a1_manager.set_stage_position(center)
      
    def inject(self, inject_vol_ul: float, injection_time_ms: float | None = None, mixing_cycles: int = 1) -> None:
        """ 
        Injection function to control the injection depending on the chosen device: nanopick head or quickpick valve control.

        Args:
            - injection_volume_ul(float): injected volume in microliters
            - injection_time_ms(float): injection time in milliseconds (only needed for nanopick head control)
            - mixing_cycles(int): number of mixing cycles during injection (default: 1 - meaning there is no mixing)
        """
        if self.injection_device == "nanopick":
                injection_volume = self._ul_to_nl_converter(inject_vol_ul)
        else:
                injection_volume = inject_vol_ul
        
        sleep(1) # wait a bit for the stage to move, adjust as needed     
        self.arm_to_liquid()
        self.injection_device.inject(injection_volume, injection_time_ms, mixing_cycles = mixing_cycles)    
        self.arm_to_home()
        sleep(2) # wait a bit for the stage to move, adjust as needed
    
    def dip_needle(self) -> None:
        """
        Dip the needle into the liquid without performing injection.
        """
        self.arm_to_liquid()
        self.arm_to_home()
        sleep(1) # wait a bit for the stage to move, adjust as needed
        

def init_injection(a1_manager: A1Manager, dish_name: str, injection_device: str, needle_size: int | None = None, pressure: float | None = None) -> Injection:
    """
    Factory function to create an Injection instance with the appropriate arm and injection device based on the specified type.
    Args:
        - core (Core): Micro-Manager Core instance for controlling the microscope hardware.
        - dish_name (str): Name of the dish being used (e.g., "96-well").
        - injection_device (str): Type of injection device ("nanopick" or "quickpick").
        - needle_size (int | None): Needle size for quickpick valve control (required if injection_device is "quickpick").
        - pressure (float | None): Pressure value for quickpick valve control (required if injection_device is "quickpick").
    Returns:
        - Injection: An instance of the Injection class with the appropriate arm and injection device.
    Raises:
        - ValueError: If an invalid injection device type is provided or if required parameters for quick
    """
    
    arm = MarZ(core=a1_manager.core, dish=dish_name) #type: ignore
    pick = get_pick_device(injection_device=injection_device, needle_size=needle_size, pressure=pressure)
    return Injection(arm=arm, injection_device=pick, a1_manager=a1_manager)


def setup_injection_device(a1_manager: A1Manager, settings: PipelineSettings) -> Injection | None:
    """
    Initialize the injection device if automated injection is enabled in the settings. Returns the initialized Injection object or None if injection is not enabled.
    """
    inj_device = None
    inj_sets = None
    if settings.injection_settings.enabled:
        inj_sets = settings.injection_settings
        inj_device = init_injection(a1_manager, 
                                        dish_name=settings.dish_settings.dish_name,
                                        injection_device=inj_sets.injection_device,
                                        needle_size=inj_sets.needle_size,
                                        pressure=inj_sets.pressure)
        logger.info(f"Initialized injection device: {inj_sets.injection_device}")
    return inj_device





if __name__ == "__main__":
    d= {"a":12, 2:5, "c":7}
    max_key = max(d)
    print(d.get(max_key))