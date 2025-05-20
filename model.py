from mesa.model import Model
from mesa.space import MultiGrid
from agents import MissileAgent, TargetAgent
from TargetReportingUnit import TargetReportingUnit

class NavalModel(Model):
    def __init__(self, width=250, height=60, num_missiles=25, seed=None):
        super().__init__(seed=seed)

        self.width = width
        self.height = height
        self.grid = MultiGrid(width, height, torus=False)

        # Create and add the Target agent
        print("Creating the Target...")
        target_pos = (width - 1, height // 2)
        target = TargetAgent(self, target_pos)  # Pass model (self) and position
        self.agents.add(target)  # unique_id assigned here
        self.grid.place_agent(target, target_pos)
        print(f"Target id {target.unique_id} has been created at {target.pos}")  # report details of creation

        # Create the TRU (Target Reporting Unit)
        tru_start_pos = (target_pos[0] - 65, target_pos[1])  # offset from target but within bounds
        tru = TargetReportingUnit(
            model=self,
            pos=tru_start_pos,
            direction=None,
            speed=1,
            holding_radius=10  # orbit radius
        )
        self.agents.add(tru)
        self.grid.place_agent(tru, tru_start_pos)
        print(f"TRU id {tru.unique_id} has been created at {tru.pos}")

        # Create and add Missile agents
        print("Creating missiles...")
        y_coords = [int(i * height / num_missiles) for i in range(num_missiles)]
        for y in y_coords:
            pos = (0, y)
            missile = MissileAgent(
                model=self,
                pos=pos,
                direction=None,
                speed=1,
                fuel=400,
                initial_target_estimate=[90, 15]
            )
            self.grid.place_agent(missile, pos)
            self.agents.add(missile)  # Add missile to the AgentSet
            print(f"Missile id {missile.unique_id} created with fuel: {missile.fuel} at {missile.pos}")  # report details of creation

    def step(self):
        # Step all agents (including TRUs and missiles)
        self.agents.shuffle_do("step")

        # Find all TRUs
        tru_agents = [agent for agent in self.agents if isinstance(agent, TargetReportingUnit)]
        # Find all missiles
        missile_agents = [agent for agent in self.agents if isinstance(agent, MissileAgent)]

        # For each TRU, get the latest estimate and update missiles
        for tru in tru_agents:
            if tru.latest_estimate is not None:
                for missile in missile_agents:
                    missile.update_target_estimate(tru.latest_estimate)
