import math
import random

from mesa import Agent

from agents import MissileAgent, TargetAgent
from sensor import Sensor


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

    @staticmethod
    def rotate_vector(vector, angle_rad):
        x, y = vector
        cos_theta = math.cos(angle_rad)
        sin_theta = math.sin(angle_rad)
        return (
            x * cos_theta - y * sin_theta,
            x * sin_theta + y * cos_theta
        )

    def step(self):
        print(f"TRU {self.unique_id} stepping at pos {self.pos}")

        # Get target object (ok to find the object — but don't use .pos directly!)
        target = next((agent for agent in self.model.agents if isinstance(agent, TargetAgent)), None)

        # Sensor detection
        detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)
        
        if detected:
            dx, dy = noisy_rel
            new_est_x = self.pos[0] + dx
            new_est_y = self.pos[1] + dy
            self.estimated_target_pos = [new_est_x, new_est_y]
            self.latest_estimate = list(self.estimated_target_pos)

            # Re-orient toward new estimate
            vec_to_target = (dx, dy)
            mag = math.hypot(*vec_to_target)
            if mag > 0:
                self.direction = (vec_to_target[0] / mag, vec_to_target[1] / mag)

            print(f"TRU id {self.unique_id} detected target. New estimate: {self.estimated_target_pos}")

        else:
            print(f"TRU id {self.unique_id} did NOT detect target at step {self.model.steps}")

        # Rotate direction clockwise by 10 degrees if no detection
        angle_deg = 10
        angle_rad = math.radians(angle_deg)
        self.direction = self.rotate_vector(self.direction, angle_rad)

        # Re-normalize direction vector
        mag = math.hypot(*self.direction)
        if mag > 0:
            self.direction = (self.direction[0] / mag, self.direction[1] / mag)

        # Update direction *only* if target was detected
        if self.estimated_target_pos:
            dx = self.estimated_target_pos[0] - self.pos[0]
            dy = self.estimated_target_pos[1] - self.pos[1]
            mag = math.hypot(dx, dy)
            if mag > 0:
                self.direction = (dx / mag, dy / mag)

        # Movement: try to maintain min distance from *estimated* target pos
        next_y = self.float_pos[1] + (self.speed if self.moving_up else -self.speed)
        next_y %= self.model.grid.height  # wrap around

        proposed_pos = (self.float_pos[0], next_y)

        # Use estimated target position for distance calculation
        if self.estimated_target_pos:
            dist_to_estimated_target = math.dist(proposed_pos, self.estimated_target_pos)
            if dist_to_estimated_target < self.min_distance:
                # Reverse direction
                self.moving_up = not self.moving_up
                # Update next_y again
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

