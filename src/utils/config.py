from dataclasses import dataclass

@dataclass
class ALNSConfig:
    weight_distance: float = 1.0
    weight_time: float = 0.0
    unassigned_penalty: float = 10000.0

    iterations:int = 5000
    stage1_iterations: int = 3000
    segment_length: int = 100
    sigma_1: float = 33.0
    sigma_2: float = 9.0
    sigma_3: float = 13.0
    reaction_factor: float = 0.1
    cooling_rate: float = 0.9985
    w_param: float = 0.05
    eta: float = 0.025
    policy_mode: str = "roulette"
    bandit_alpha: float = 0.8
    bandit_epsilon: float = 0.05
