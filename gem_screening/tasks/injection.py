from __future__ import annotations # Enable type annotation to be stored as string

from typing import TYPE_CHECKING

from a1_manager.microscope_hardware.nanopick.devices.injection_protocol import PickDevice
from a1_manager.microscope_hardware.nanopick.injection_factory import get_pick_device
from a1_manager.microscope_hardware.nanopick.devices.marZ import MarZ

if TYPE_CHECKING:
    from pycromanager import Core


class Injection():
    """ 
    Class to control the injection depending on the chosen device: nanopick head or quickpick valve control.
    Args:
        - injection_volume(float): injected volume in microliters
        - injection_time(int): injection time in milliseconds
        - nanopick_dish(str): name of the used dish (e.g.: "96-well")
    """
    
    __slots__ =  'arm', 'injection_device'
    
    def __init__(self,  arm: MarZ, injection_device: PickDevice) -> None: 
        
        self.arm = arm
        self.injection_device = injection_device
                
    
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
        
    def inject(self,  inject_vol_ul: float, injection_time_ms: float | None = None, mixing_cycles: int = 1) -> None:
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
                
        self.arm_to_home()
        self.injection_device.inject(injection_volume, injection_time_ms, mixing_cycles = mixing_cycles)    
        self.arm_to_liquid()
        self.arm_to_home()
        

def init_injection(core: Core, dish_name: str, injection_device: str, needle_size: int | None = None, pressure: float | None = None) -> Injection:
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
    arm = MarZ(core=core, dish=dish_name)
    pick = get_pick_device(injection_device=injection_device, needle_size=needle_size, pressure=pressure)
    return Injection(arm=arm, injection_device=pick)