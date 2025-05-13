from mesa import Model
from mesa.space import MultiGrid

from agents import MissileAgent, TargetAgent

class NavalModel(Model):
    def __init__(self, width=100, height=20, num_missiles=25, seed=None):
        super().__init__(seed=seed)  # Required in Mesa 3.0

        self.width = width
        self.height = height

        self.grid = MultiGrid(width, height, torus=True)

        # Create the Target agent
        target_pos = (width - 1, height // 2)
        target = TargetAgent(self, target_pos)  # Pass model (self) and position
        self.grid.place_agent(target, target_pos)
        self.agents.add(target)  # Add target to the AgentSet

        # Create the Missile agents
        y_coords = [int(i * height / num_missiles) for i in range(num_missiles)]

        for y in y_coords:
            pos = (0, y)
            direction = (1, 0)  # Missiles moving to the right
            speed = 1
            fuel = 100
            missile = MissileAgent(self, pos, direction, speed, fuel)
            self.grid.place_agent(missile, pos)

    def step(self):
        # Randomly shuffle the agents and then call their step() method
        self.agents.shuffle_do("step")
