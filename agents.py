from mesa import Agent
import math

class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel):
        super().__init__(model)
        self.pos = pos
        self.direction = direction
        self.speed = speed
        self.fuel = fuel
        self.exploded = False
        self.alive = True
        print(f"Missile {self.unique_id} created with fuel: {self.fuel}")

    
    def step(self):
        print(f"Missile {self.unique_id} stepping. Alive: {self.alive}, Fuel: {self.fuel}")
        if not self.alive:
            return

        if self.direction is None:
            # Compute direction to target
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

        self.model.grid.move_agent(self, new_pos)
        self.pos = new_pos

        print(f"Missile {self.unique_id} moved to {new_pos}")

        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                return


class TargetAgent(Agent):
    def __init__(self, model, pos):
        super().__init__(model)  # Pass model to the base class (Mesa)
        self.pos = pos  # Initialize position

    def step(self):
        pass  # No action for the target