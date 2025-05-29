import math
import random

from mesa import Agent

from sensor import Sensor


class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel, initial_target_estimate=None):
        super().__init__(model)

        self.speed = speed
        self.fuel = fuel
        self.exploded = False
        self.alive = True
        self.trail = [pos]
        self.sensor = Sensor(range=30, field_of_view_deg=90, noise_std=0.5)
        self.pos = pos
        self.float_pos = list(pos)
        self.direction = direction if direction is not None else (1, 0)

        # Target position estimate
        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        # Distance at which missile switches to own sensor
        self.sensor_switch_distance = 20.0

    def update_target_estimate(self, new_estimate):
        self.estimated_target_pos = list(new_estimate)
        print(f"Missile {self.unique_id} received TRU estimate: {self.estimated_target_pos}")

    def step(self):
        print(f"\nMissile {self.unique_id} stepping. Alive: {self.alive}, Fuel: {self.fuel}")

        if not self.alive:
            print(f"Missile {self.unique_id} is no longer active.")
            return

        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))

        # Calculate distance to actual target
        dx = target.pos[0] - self.pos[0]
        dy = target.pos[1] - self.pos[1]
        dist_to_target = math.hypot(dx, dy)
        print(f"Missile {self.unique_id} is {dist_to_target:.2f} units from target.")

        # Use onboard sensor if close enough
        if dist_to_target <= self.sensor_switch_distance:
            detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)
            if detected:
                dx, dy = noisy_rel
                new_est_x = self.pos[0] + dx
                new_est_y = self.pos[1] + dy
                self.estimated_target_pos = [new_est_x, new_est_y]
                print(f"Missile {self.unique_id} detected target using onboard sensor: {self.estimated_target_pos}")
            else:
                print(f"Missile {self.unique_id} sensor failed to detect target.")
        else:
            print(f"Missile {self.unique_id} relying on TRU estimate: {self.estimated_target_pos}")

        if self.estimated_target_pos:
            dx = self.estimated_target_pos[0] - self.float_pos[0]
            dy = self.estimated_target_pos[1] - self.float_pos[1]
            mag = math.hypot(dx, dy)
            if mag != 0:
                self.direction = (dx / mag, dy / mag)
            else:
                self.direction = (0, 0)

        if self.direction is None:
            raise ValueError(f"Missile {self.unique_id} has no direction.")

        self.fuel -= 1
        if self.fuel <= 0:
            self.alive = False
            print(f"Missile {self.unique_id} ran out of fuel.")
            return

        # Move missile
        self.float_pos[0] += self.direction[0] * self.speed
        self.float_pos[1] += self.direction[1] * self.speed

        new_x = int(round(self.float_pos[0])) % self.model.grid.width
        new_y = int(round(self.float_pos[1])) % self.model.grid.height
        new_pos = (new_x, new_y)

        if self.alive:
            self.trail.append(self.pos)

        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos
        print(f"Missile {self.unique_id} moved to {new_pos} with direction {self.direction}")

        # Check for target hit
        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                print(f"Missile {self.unique_id} hit the target at {new_pos}!")
                return

class TargetAgent(Agent):
    def __init__(self, model, pos, speed=1):
        super().__init__(model)
        self.pos = pos
        self.float_y = pos[1]  # for smooth movement
        self.speed = speed

        self.direction = 1  # 1 for up, -1 for down
        self.steps_remaining_in_phase = random.randint(5, 20)

    def step(self):
        # If we finished the current phase, pick a new one with opposite direction
        if self.steps_remaining_in_phase <= 0:
            self.direction *= -1
            self.steps_remaining_in_phase = random.randint(5, 20)

        # Move by `speed` in current direction
        self.float_y += self.direction * self.speed

        # Clamp to grid boundaries
        self.float_y = max(0, min(self.model.grid.height - 1, self.float_y))

        # Convert to int grid coordinates
        new_y = int(round(self.float_y))
        new_pos = (self.pos[0], new_y)

        if new_pos != self.pos:
            self.model.grid.move_agent(self, new_pos)
            self.pos = new_pos

        self.steps_remaining_in_phase -= 1

