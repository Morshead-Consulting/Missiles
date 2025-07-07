import numpy as np
import math
import random
from base_agent import MissileAgent

class MissileRLAgent(MissileAgent):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_distance_to_target = self._distance_to(self.estimated_target_pos)
        self.reward = 0
        self.action = None  # Store current action

    def step(self):
        if not self.alive:
            return
        
        # Observation space
        obs = self.get_observation()
        
        # Policy selects action
        # This is where your RL model integration would go.
        # For now, it uses the placeholder random action.
        self.action = self.select_action(obs)
        
        # ACTION SPACE: Apply the selected action
        self.apply_action(self.action)

        # Run common movement logic and target check from base class
        # We call move_and_check_hit directly, bypassing base_agent's perform_guidance
        # because the RL agent's apply_action already sets speed and direction.
        super().move_and_check_hit()

        # Reward signal
        self.reward = self.get_reward()
        
        # Save distance to use in the next reward calculation
        self.last_distance_to_target = self._distance_to(self.estimated_target_pos)

    # Observation space: encodes the current state of the agent
    def get_observation(self):
        dx = self.estimated_target_pos[0] - self.float_pos[0]
        dy = self.estimated_target_pos[1] - self.float_pos[1]
        norm_dx = dx / self.model.width
        norm_dy = dy / self.model.height
        norm_fuel = self.fuel / 400.0
        norm_pos_x = self.float_pos[0] / self.model.width
        norm_pos_y = self.float_pos[1] / self.model.height
        missile_type_val = self.missile_type.value / 2.0  # Normalized (0, 1)

        return np.array([
            norm_pos_x,
            norm_pos_y,
            norm_dx,
            norm_dy,
            norm_fuel,
            missile_type_val
        ], dtype=np.float32)

    # ACTION SPACE: Discrete actions for the RL agent
    def apply_action(self, action):
        """Discrete actions:
        0 = forward, 1 = left, 2 = right, 3 = slow down, 4 = speed up
        """
        if action == 0:
            pass  # Maintain current direction and speed
        elif action == 1:
            self.direction = self._rotate_vector(self.direction, -0.2)
        elif action == 2:
            self.direction = self._rotate_vector(self.direction, 0.2)
        elif action == 3:
            self.speed = max(self.min_speed, self.speed - 0.1)
        elif action == 4:
            self.speed = min(self.max_speed, self.speed + 0.1)

    # REWARD SIGNAL: Calculate reward after applying action
    def get_reward(self):
        if self.exploded:
            return 100.0
        elif not self.alive:
            return -50.0
        else:
            current_dist = self._distance_to(self.estimated_target_pos)
            improvement = self.last_distance_to_target - current_dist
            return improvement * 10 - 1  # Reward distance improvement, small penalty per step

    # Utility: Euclidean distance to a point
    def _distance_to(self, pos):
        dx = pos[0] - self.float_pos[0]
        dy = pos[1] - self.float_pos[1]
        return math.hypot(dx, dy)

    # Utility: Rotate the direction vector by an angle in radians
    def _rotate_vector(self, vec, angle_rad):
        cos_theta = math.cos(angle_rad)
        sin_theta = math.sin(angle_rad)
        x, y = vec
        return (
            x * cos_theta - y * sin_theta,
            x * sin_theta + y * cos_theta
        )

    # Policy stub: replace with actual RL agent during training
    def select_action(self, observation):
        # Placeholder: random for now
        return random.choice([0, 1, 2, 3, 4])