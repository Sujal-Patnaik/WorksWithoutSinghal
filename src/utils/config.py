from dataclasses import dataclass

@dataclass
class ALNSConfig:
    weight_distance: float = 1.0
    weight_time: float = 1.0
    unassigned_penalty: float = 1000.0

    iterations:int = 10000
    segment_length: int = 100
    sigma_1: float = 33
    sigma_2: float = 9
    sigma_3: float = 13
    reaction_factor: float = 0.1
    cooling_rate: float = 0.9995
    w_param: float = 0.05
    eta=0.025
