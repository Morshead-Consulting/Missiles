import random
from mesa import Agent


class TargetAgent(Agent):
    def __init__(self, model, pos, speed=1):
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
