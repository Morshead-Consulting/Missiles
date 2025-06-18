import math
import random

from mesa import Agent
from sensor import Sensor
from target_agent import TargetAgent


class TargetReportingUnit(Agent):
    """
    A fixed agent that acts as a target reporting unit.
    It periodically senses the target and updates its latest estimate.
    """
    def __init__(self, model, pos, direction, speed=0): # TRU is stationary, speed is 0
        super().__init__(model)
        self.pos = pos
        self.direction = direction if direction is not None else (1, 0) # Direction might be used for FOV orientation
        self.speed = speed
        self.latest_estimate = None # Stores the latest known position of the target

        # The TRU's sensor capability
        self.sensor = Sensor(range=150, field_of_view_deg=180, noise_std=0.7) # Wider FOV, less noise

        # How often the TRU updates its estimate
        self.update_interval = 5 # Update every 5 steps
        self.last_update_step = -self.update_interval

        print(f"TRU {self.unique_id} initialized at {self.pos} with sensor range {self.sensor.range}.")

    def _get_target(self):
        """Helper to find the TargetAgent in the model."""
        target_agents = [agent for agent in self.model.agents if isinstance(agent, TargetAgent)]
        if not target_agents:
            return None # Return None if no target is found
        return target_agents[0]


    def step(self):
        """
        The TRU's step function. Senses the target and updates its estimate.
        """
        # Find the target agent in the model
        target = self._get_target() # Use the helper method

        if target is None:
            # print(f"TRU {self.unique_id}: No target found.")
            self.latest_estimate = None
            return

        if self.model.steps - self.last_update_step >= self.update_interval:
            # Run the sensor detection
            detected, noisy_relative_pos = self.sensor.run_detection(
                self.pos, self.direction, target.pos
            )

            if detected:
                # Calculate absolute estimated position
                estimated_x = self.pos[0] + noisy_relative_pos[0]
                estimated_y = self.pos[1] + noisy_relative_pos[1]
                self.latest_estimate = [estimated_x, estimated_y]
                print(f"TRU {self.unique_id}: Detected target at {target.pos}. New estimate: [{estimated_x:.2f}, {estimated_y:.2f}] (Noisy Relative: [{noisy_relative_pos[0]:.2f}, {noisy_relative_pos[1]:.2f}])")
            else:
                self.latest_estimate = None # Lost sight of target
                print(f"TRU {self.unique_id}: Target out of sensor range or FOV. No estimate.")
            
            self.last_update_step = self.model.steps

