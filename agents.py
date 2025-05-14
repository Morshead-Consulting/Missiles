from mesa import Agent
import math

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

        # Always compute direction to the current target position
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
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

        self.float_pos[0] += self.direction[0] * self.speed
        self.float_pos[1] += self.direction[1] * self.speed

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
        self.start_step = 35
        self.end_step = 75
        self.start_y = pos[1]
        self.end_y = model.grid.height - 1

    def step(self):
        current_step = self.model.steps

        # Only move if we're between start and end step
        if self.start_step <= current_step <= self.end_step:
            # Compute how far along the movement is (from 0.0 to 1.0)
            progress = (current_step - self.start_step) / (self.end_step - self.start_step)

            # Compute new Y position by interpolating
            new_y = round(self.start_y + (self.end_y - self.start_y) * progress)
            new_pos = (self.model.grid.width - 1, new_y)

            if new_pos != self.pos:
                self.model.grid.move_agent(self, new_pos)
                self.pos = new_pos
