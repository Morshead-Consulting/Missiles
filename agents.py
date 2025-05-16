from mesa import Agent
import math
import random

class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel):
        super().__init__(model)
        #self.pos = pos
        self.direction = direction
        self.speed = speed
        self.fuel = fuel
        self.exploded = False
        self.alive = True
        self.trail = [pos]
    
    def step(self):
        print(f"Missile {self.unique_id} stepping. Alive: {self.alive}, Fuel: {self.fuel}")
        if not self.alive:
            return

        # Compute direction to the current target position
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        # Direction is calculated each tick as a unit vector
        # Unit vector points from the missile’s current location to the target
        dx = target.pos[0] - self.pos[0]
        dy = target.pos[1] - self.pos[1]
        magnitude = math.hypot(dx, dy)
        self.direction = (dx / magnitude, dy / magnitude) if magnitude != 0 else (0, 0)

        self.fuel -= 1
        if self.fuel <= 0:
            self.alive = False
            return

        if not hasattr(self, "float_pos"):
            self.float_pos = list(self.pos)

        # speed is a scalar (e.g. 1.2 or 0.5), interpreted as distance units per tick
        # In each tick, the missile travels speed * direction
        # self.float_pos tracks the true floating-point position for accuracy
        self.float_pos[0] += self.direction[0] * self.speed
        self.float_pos[1] += self.direction[1] * self.speed

        # Update to self.pos (as the grid is discrete)
        new_x = int(round(self.float_pos[0])) % self.model.grid.width
        new_y = int(round(self.float_pos[1])) % self.model.grid.height
        new_pos = (new_x, new_y)

        if self.alive:
            self.trail.append(self.pos)  # Record trail for visualisation

        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos

        print(f"Missile {self.unique_id} moved to {new_pos}")

        # Check whether the missile has hit its target after moving
        cellmates = self.model.grid.get_cell_list_contents([new_pos]) # retrieves all agents at the missile’s new positio
        for other in cellmates:
            if isinstance(other, TargetAgent): # Check if any of the agents in the cell is a TargetAgent
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
