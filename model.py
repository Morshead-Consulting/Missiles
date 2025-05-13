from mesa import Model
from mesa.space import MultiGrid
import random

from agents import MissileAgent, TargetAgent

class NavalModel(Model):
    def __init__(self, width=100, height=20, num_missiles=25, seed=None):
        super().__init__(seed=seed)  # Required in Mesa 3.0

        self.grid = MultiGrid(width, height, torus=True)
        self.width = width
        self.height = height

        # Create the target agent
        target_pos = (width - 1, height // 2)
        target = TargetAgent(self.next_id(), self, target_pos)
        self.grid.place_agent(target, target_pos)
        self.agents.append(target)  # New Mesa 3.0 agent storage

        # Create missile agents
        for i in range(num_missiles):
            y_pos = int(i * height / num_missiles)
            start_pos = (0, y_pos)
            direction = (1, 0)  # Move right
            speed = 1
            fuel = random.randint(10, 50)
            missile = MissileAgent(self.next_id(), self, start_pos, direction, speed, fuel)
            self.grid.place_agent(missile, start_pos)
            self.agents.append(missile)  # New Mesa 3.0 style

    def step(self):
        self.agents.shuffle_do("step")  # Replaces self.schedule.step()
