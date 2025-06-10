import math
import random

from mesa import Agent

from sensor import Sensor # Assuming this file exists and is correct


class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel, initial_target_estimate=None, mode=None):
        # Corrected: Call super().__init__ only with 'model'.
        # unique_id is automatically assigned by Mesa 3.0 when the agent is added to model.agents.
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
        self.mode = mode # <--- ADDED: Store the 'mode' passed from the model

        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        self.sensor_switch_distance = 20.0

    def update_target_estimate(self, new_estimate):
        self.estimated_target_pos = list(new_estimate)

    def step(self):
        print(f"[Step {self.model.steps}] Missile {self.unique_id} - Starting step. Pos: {self.pos}, Fuel: {self.fuel}, Alive: {self.alive}")

        if not self.alive:
            print(f"[Missile {self.unique_id}] Inactive. Skipping step.")
            return

        # Get target agent (assumes only one target). Access via model.agents for Mesa 3.0
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        dx = target.pos[0] - self.pos[0]
        dy = target.pos[1] - self.pos[1]
        dist_to_target = math.hypot(dx, dy)

        # Use onboard sensor if close enough
        if dist_to_target <= self.sensor_switch_distance:
            detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)
            if detected:
                dx, dy = noisy_rel
                self.estimated_target_pos = [self.pos[0] + dx, self.pos[1] + dy]
                print(f"[Missile {self.unique_id}] Detected target with onboard sensor. New estimate: {self.estimated_target_pos}")
            else:
                print(f"[Missile {self.unique_id}] Onboard sensor failed to detect target.")
        else:
            print(f"[Missile {self.unique_id}] Using TRU estimate: {self.estimated_target_pos}")

        # Adjust direction based on estimated position
        if self.estimated_target_pos:
            dx = self.estimated_target_pos[0] - self.float_pos[0]
            dy = self.estimated_target_pos[1] - self.float_pos[1]
            mag = math.hypot(dx, dy)
            self.direction = (dx / mag, dy / mag) if mag != 0 else (0, 0)

        if self.direction is None:
            raise ValueError(f"[Missile {self.unique_id}] ERROR: No direction set.")

        self.fuel -= 1
        if self.fuel <= 0:
            self.alive = False
            # Remove agent from model.agents when it runs out of fuel
            self.model.agents.remove(self)
            # Remove agent from grid
            self.model.grid.remove_agent(self)
            print(f"[Missile {self.unique_id}] Ran out of fuel and is now inactive.")
            return

        # Move missile
        self.float_pos[0] += self.direction[0] * self.speed
        self.float_pos[1] += self.direction[1] * self.speed

        # Ensure new_x and new_y stay within grid boundaries
        new_x = int(round(self.float_pos[0]))
        new_y = int(round(self.float_pos[1]))

        # Clamp positions to grid boundaries (important for non-toroidal grids)
        new_x = max(0, min(new_x, self.model.grid.width - 1))
        new_y = max(0, min(new_y, self.model.grid.height - 1))

        new_pos = (new_x, new_y)

        if self.alive:
            self.trail.append(self.pos)

        # Only move if the position has actually changed to avoid unnecessary grid updates
        if new_pos != self.pos:
            self.model.grid.move_agent(self, new_pos)
            self.pos = new_pos

        print(f"[Missile {self.unique_id}] Moved to {new_pos} | Direction: {self.direction} | Fuel left: {self.fuel}")

        # Check for hit
        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                # Remove agent from model.agents when it hits target
                self.model.agents.remove(self)
                # Remove agent from grid
                self.model.grid.remove_agent(self)
                print(f"[Missile {self.unique_id}] HIT! Target destroyed at {new_pos}.")
                return

        print(f"[Step {self.model.steps}] Missile {self.unique_id} - End step. Pos: {self.pos}, Dir: {self.direction}, Estimate: {self.estimated_target_pos}, Exploded: {self.exploded}")


class TargetAgent(Agent):
    def __init__(self, model, pos, speed=1):
        # Corrected: Call super().__init__ only with 'model'.
        # unique_id is automatically assigned by Mesa 3.0 when the agent is added to model.agents.
        super().__init__(model)
        self.pos = pos
        self.float_y = pos[1]
        self.speed = speed

        self.direction = 1
        self.steps_remaining_in_phase = random.randint(5, 20)

    def step(self):
        print(f"[Step {self.model.steps}] Target {self.unique_id} - Starting step. Pos: {self.pos}")

        if self.steps_remaining_in_phase <= 0:
            self.direction *= -1
            self.steps_remaining_in_phase = random.randint(5, 20)

        self.float_y += self.direction * self.speed
        self.float_y = max(0, min(self.model.grid.height - 1, self.float_y))

        new_y = int(round(self.float_y))
        new_pos = (self.pos[0], new_y)

        if new_pos != self.pos:
            self.model.grid.move_agent(self, new_pos)
            self.pos = new_pos

        self.steps_remaining_in_phase -= 1
        print(f"[Step {self.model.steps}] Target {self.unique_id} - End step. Pos: {self.pos}")

