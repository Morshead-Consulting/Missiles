from mesa import Agent
import math
import random

from sensor import Sensor
from agents import MissileAgent, TargetAgent

class TargetReportingUnit(Agent):
    def __init__(self, model, pos, direction=None, speed=1, holding_radius=10):
        super().__init__(model)

        self.speed = speed
        self.pos = pos
        self.float_pos = list(pos)
        self.trail = [pos]

        self.holding_radius = holding_radius  # how far from target it circles
        self.angle = 0  # for holding pattern movement
        self.direction = direction if direction is not None else (1, 0)

        # Longer-range sensor
        self.sensor = Sensor(range=50, field_of_view_deg=120, noise_std=0.3)

        self.estimated_target_pos = None

    def step(self):
        print(f"TRU {self.unique_id} stepping at pos {self.pos}")

        # Detect target using sensor
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)

        if detected:
            dx, dy = noisy_rel
            new_est_x = self.pos[0] + dx
            new_est_y = self.pos[1] + dy
            self.estimated_target_pos = [new_est_x, new_est_y]
            print(f"TRU id {self.unique_id} estimated target at {self.estimated_target_pos}")

        # Move in holding pattern (circular or oscillating motion)
        self.angle += math.radians(10)  # adjust to control speed of rotation

        # Holding around the actual target position (can swap to estimate if preferred)
        center_x, center_y = target.pos
        offset_x = self.holding_radius * math.cos(self.angle)
        offset_y = self.holding_radius * math.sin(self.angle)

        self.float_pos = [center_x + offset_x, center_y + offset_y]

        new_x = int(round(self.float_pos[0])) % self.model.grid.width
        new_y = int(round(self.float_pos[1])) % self.model.grid.height
        new_pos = (new_x, new_y)

        self.trail.append(self.pos)
        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos

        print(f"TRU {self.unique_id} moved to {new_pos}")
