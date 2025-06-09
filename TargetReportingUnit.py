import math
from mesa import Agent

from agents import TargetAgent
from sensor import Sensor


class TargetReportingUnit(Agent):
    def __init__(self, model, pos, direction=None, speed=1, min_distance=150):
        super().__init__(model)

        self.pos = pos
        self.float_pos = list(pos)
        self.speed = speed
        self.min_distance = min_distance
        self.direction = direction or (0, 1)  # Initial y-axis movement
        self.moving_up = True

        self.trail = [pos]
        self.sensor = Sensor(range=100, field_of_view_deg=120, noise_std=0.3)

        self.estimated_target_pos = None
        self.latest_estimate = None

    def step(self):
        print(f"TRU {self.unique_id} stepping at pos {self.pos}")

        target = self._get_target()
        detected = self._detect_target(target)

        if not detected:
            self._rotate_search_direction()
        else:
            print(f"TRU {self.unique_id} sending new target estimate: {self.latest_estimate}")

        self._update_direction_if_estimate_exists()
        self._move_with_distance_check()
        self._finalize_position()

    def _get_target(self):
        return next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))

    def _detect_target(self, target):
        detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)
        if detected:
            estimate = [self.pos[0] + noisy_rel[0], self.pos[1] + noisy_rel[1]]
            self.estimated_target_pos = estimate
            self.latest_estimate = estimate

            self._set_direction_towards_vector(noisy_rel)
            print(f"TRU id {self.unique_id} detected target. New estimate: {estimate}")
        else:
            print(f"TRU id {self.unique_id} did NOT detect target at step {self.model.steps}")
        return detected

    def _rotate_search_direction(self, angle_deg=10):
        angle_rad = math.radians(angle_deg)
        x, y = self.direction
        cos_theta = math.cos(angle_rad)
        sin_theta = math.sin(angle_rad)
        new_direction = (x * cos_theta - y * sin_theta, x * sin_theta + y * cos_theta)
        mag = math.hypot(*new_direction)
        if mag > 0:
            self.direction = (new_direction[0] / mag, new_direction[1] / mag)
            print(f"TRU {self.unique_id} rotating search direction to {self.direction}")

    def _set_direction_towards_vector(self, vector):
        dx, dy = vector
        mag = math.hypot(dx, dy)
        if mag > 0:
            self.direction = (dx / mag, dy / mag)

    def _update_direction_if_estimate_exists(self):
        if self.estimated_target_pos:
            dx = self.estimated_target_pos[0] - self.pos[0]
            dy = self.estimated_target_pos[1] - self.pos[1]
            mag = math.hypot(dx, dy)
            if mag > 0:
                self.direction = (dx / mag, dy / mag)
                print(f"TRU {self.unique_id} updating direction based on estimate: {self.direction}")

    def _move_with_distance_check(self):
        next_y = self.float_pos[1] + (self.speed if self.moving_up else -self.speed)
        next_y %= self.model.grid.height  # Wrap around top/bottom

        proposed_pos = (self.float_pos[0], next_y)

        if self.estimated_target_pos:
            dist = math.dist(proposed_pos, self.estimated_target_pos)
            if dist < self.min_distance:
                self.moving_up = not self.moving_up
                print(f"TRU {self.unique_id} reversing direction due to proximity ({dist:.2f} < {self.min_distance})")
                next_y = self.float_pos[1] + (self.speed if self.moving_up else -self.speed)
                next_y %= self.model.grid.height

        self.float_pos[1] = next_y

    def _finalize_position(self):
        new_x = int(round(self.float_pos[0])) % self.model.grid.width
        new_y = int(round(self.float_pos[1])) % self.model.grid.height
        new_pos = (new_x, new_y)

        self.trail.append(self.pos)
        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos

        print(f"TRU {self.unique_id} moved to {new_pos}")
