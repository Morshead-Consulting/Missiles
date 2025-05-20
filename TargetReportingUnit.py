from mesa import Agent
import math
import random

from sensor import Sensor
from agents import MissileAgent, TargetAgent

class TargetReportingUnit(Agent):
    def __init__(self, model, pos, direction=None, speed=1, min_distance=150):
        super().__init__(model)

        self.speed = speed
        self.pos = pos
        self.float_pos = list(pos)
        self.trail = [pos]

        self.min_distance = min_distance
        self.direction = (0, 1)  # only move along y-axis
        self.moving_up = True  # flag for direction of y movement

        self.sensor = Sensor(range=100, field_of_view_deg=120, noise_std=0.3)

        self.estimated_target_pos = None
        self.latest_estimate = None

    def step(self):
        print(f"TRU {self.unique_id} stepping at pos {self.pos}")

        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))

        # Always look toward the target (used for detection)
        dx = target.pos[0] - self.pos[0]
        dy = target.pos[1] - self.pos[1]
        mag = math.hypot(dx, dy)
        if mag > 0:
            self.direction = (dx / mag, dy / mag)

        # Sensor detection
        detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)
        if detected:
            dx, dy = noisy_rel
            new_est_x = self.pos[0] + dx
            new_est_y = self.pos[1] + dy
            self.estimated_target_pos = [new_est_x, new_est_y]
            self.latest_estimate = list(self.estimated_target_pos)
            print(f"TRU id {self.unique_id} detected target. New estimate: {self.estimated_target_pos}")
        else:
            print(f"TRU id {self.unique_id} did NOT detect target at step {self.model.steps}")

        # Move up or down along y-axis
        next_y = self.float_pos[1] + (self.speed if self.moving_up else -self.speed)
        next_y %= self.model.grid.height  # wrap around if necessary

        # Check if moving would violate min distance constraint
        proposed_pos = (self.float_pos[0], next_y)
        dist_to_target = math.dist(proposed_pos, target.pos)
        if dist_to_target < self.min_distance:
            # Reverse direction
            self.moving_up = not self.moving_up
            # Update next_y accordingly
            next_y = self.float_pos[1] + (self.speed if self.moving_up else -self.speed)
            next_y %= self.model.grid.height

        self.float_pos[1] = next_y
        new_x = int(round(self.float_pos[0])) % self.model.grid.width
        new_y = int(round(self.float_pos[1])) % self.model.grid.height
        new_pos = (new_x, new_y)

        self.trail.append(self.pos)
        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos

        print(f"TRU {self.unique_id} moved to {new_pos}")
