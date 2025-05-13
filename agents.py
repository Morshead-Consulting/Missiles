from mesa import Agent

class MissileAgent(Agent):
    def __init__(self, unique_id, model, pos, direction, speed, fuel):
        super().__init__(unique_id, model)
        self.pos = pos
        self.direction = direction  # e.g., (dx, dy)
        self.speed = speed  # cells per step
        self.fuel = fuel
        self.exploded = False
        self.alive = True

    def step(self):
        if not self.alive:
            return

        # Use up fuel
        self.fuel -= 1
        if self.fuel <= 0:
            self.alive = False
            return

        # Compute next position
        new_x = (self.pos[0] + self.direction[0] * self.speed) % self.model.grid.width
        new_y = (self.pos[1] + self.direction[1] * self.speed) % self.model.grid.height
        new_pos = (new_x, new_y)

        # Move to the new position
        self.model.grid.move_agent(self, new_pos)

        # Check for collision with target
        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                return


class TargetAgent(Agent):
    def __init__(self, unique_id, model, pos):
        super().__init__(unique_id, model)
        self.pos = pos

    def step(self):
        pass  # Target is stationary and does not act