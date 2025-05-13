from mesa import Model
from mesa.space import MultiGrid
from agents import MissileAgent, TargetAgent

class NavalModel(Model):
    def __init__(self, width=100, height=20, num_missiles=25, seed=None):
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, torus=True)

        # Create and add the Target agent
        target_pos = (width - 1, height // 2)
        target = TargetAgent(self, target_pos)  # Pass model (self) and position
        self.agents.add(target)  # unique_id assigned here
        self.grid.place_agent(target, target_pos)

        # Create and add Missile agents
        y_coords = [int(i * height / num_missiles) for i in range(num_missiles)]
        for y in y_coords:
            pos = (0, y)
            direction = (1, 0)  # Missiles initially move right
            speed = 1
            fuel = 100
            missile = MissileAgent(self, pos, direction, speed, fuel)  # Don't need to manually pass ID
            self.grid.place_agent(missile, pos)
            self.agents.add(missile)  # Add missile to the AgentSet

    def step(self):
        self.agents.shuffle_do("step")  # Call step on all agents
        self.steps += 1  # Increment the simulation time
