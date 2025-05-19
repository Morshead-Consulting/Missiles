from mesa import Agent
import math
import random

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

        # Handle estimated position
        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        # Set direction: use provided, or default to (1, 0)
        self.direction = direction if direction is not None else (1, 0)


    def update_target_estimate(self, new_estimate):
        """External method to inject a new estimate of target position."""
        self.estimated_target_pos = list(new_estimate)

    def step(self):
        print(f"Missile {self.unique_id} stepping. Alive: {self.alive}, Fuel: {self.fuel}")
        
        if not self.alive:
            return

        # Attempt to detect target with the missile's sensor
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)

        if detected:
            dx, dy = noisy_rel
            new_est_x = self.pos[0] + dx
            new_est_y = self.pos[1] + dy
            self.estimated_target_pos = [new_est_x, new_est_y]
            print(f"Missile {self.unique_id} detected target at noisy position {self.estimated_target_pos}")

        # If we have an estimate of the target's position, update direction towards it
        if self.estimated_target_pos:
            # Ensure float_pos exists for sub-grid tracking
            if not hasattr(self, "float_pos"):
                self.float_pos = list(self.pos)

            dx = self.estimated_target_pos[0] - self.float_pos[0]
            dy = self.estimated_target_pos[1] - self.float_pos[1]
            mag = math.hypot(dx, dy)

            if mag != 0:
                self.direction = (dx / mag, dy / mag)
            else:
                self.direction = (0, 0)

        # Defensive check: ensure direction is valid
        if self.direction is None:
            raise ValueError(f"Missile {self.unique_id} has no valid direction before movement.")

        # Decrease fuel and check for burnout
        self.fuel -= 1
        if self.fuel <= 0:
            self.alive = False
            return

        # Move based on direction and speed
        self.float_pos[0] += self.direction[0] * self.speed
        self.float_pos[1] += self.direction[1] * self.speed
        new_x = int(round(self.float_pos[0])) % self.model.grid.width
        new_y = int(round(self.float_pos[1])) % self.model.grid.height
        new_pos = (new_x, new_y)

        # Record trail for visualisation
        if self.alive:
            self.trail.append(self.pos)

        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos

        print(f"Missile {self.unique_id} moved to {new_pos}")

        # Check for target hit at the new position
        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                return


class TargetAgent(Agent):
    def __init__(self, model, pos):
        super().__init__(model)
        self.pos = pos
        self.start_step = 0
        self.end_step = 95
        self.start_y = pos[1]
        self.end_y = model.grid.height - 1  # or whatever you prefer
        self.current_step = 0

    def step(self):
        self.current_step += 1

        if self.start_step <= self.current_step <= self.end_step:
            remaining_steps = self.end_step - self.current_step + 1
            current_y = self.pos[1]
            distance_left = self.end_y - current_y

            if remaining_steps <= 0:
                return  # Movement complete

            # Compute max possible movement this step without overshooting
            max_step = distance_left / remaining_steps

            # Add randomness: vary move by ±50% (bounded)
            min_step = max(0, max_step * 0.5)
            max_step = max_step * 1.5
            move_y = random.uniform(min_step, max_step)

            new_y = current_y + move_y
            new_y = min(self.model.grid.height - 1, int(round(new_y)))

            new_pos = (self.pos[0], new_y)

            if new_pos != self.pos:
                self.model.grid.move_agent(self, new_pos)
                self.pos = new_pos
