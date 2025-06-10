from enum import Enum

from mesa.model import Model
from mesa.space import MultiGrid

from agents import MissileAgent, TargetAgent
from TargetReportingUnit import TargetReportingUnit


class SwarmMode(Enum):
    SIMPLE = 1
    OVERWHELM = 2
    WAVE = 3
    RECCE = 4
    SPLIT_AXIS = 5
    DECOY = 6


class NavalModel(Model):
    def __init__(self, swarm_mode=SwarmMode.SIMPLE, launch_interval=30, width=250, height=60, num_missiles=25, seed=None):
        super().__init__(seed=seed)

        self.swarm_mode = swarm_mode
        self.launch_interval = launch_interval
        self.last_launch_step = -launch_interval
        self.width = width
        self.height = height
        self.num_missiles = num_missiles
        self.grid = MultiGrid(width, height, torus=False)

        self.missile_count = 0  # How many missiles launched so far

        # Create and add the Target agent
        print("Creating the Target...")
        target_pos = (width - 1, height // 2)
        target = TargetAgent(model=self, pos=target_pos, speed=0.5)
        self.grid.place_agent(target, target_pos)
        self.agents.add(target)
        print(f"Target id {target.unique_id} has been created at {target.pos}")

        # Create and add the TRU
        tru_pos = (target_pos[0] - 65, target_pos[1])
        tru = TargetReportingUnit(model=self, pos=tru_pos, direction=None, speed=1)
        self.grid.place_agent(tru, tru_pos)
        self.agents.add(tru)
        print(f"TRU id {tru.unique_id} has been created at {tru.pos}")

        self.launch_platform_pos = (0, height // 2)  # Single launch point in centre-left

    def step(self):
        print(f"Step {self.steps} starting...")
        # 1. Missile launching
        if self.steps - self.last_launch_step >= self.launch_interval and self.missile_count < self.num_missiles:
            self.launch_missile()
            self.last_launch_step = self.steps
        # Access agents via model.agents (Mesa 3.0)
        print(f"Missiles now: {len([a for a in self.agents if isinstance(a, MissileAgent)])}")

        # 2. TRUs update all missiles with new estimates
        # Access agents via model.agents (Mesa 3.0)
        tru_agents = [agent for agent in self.agents if isinstance(agent, TargetReportingUnit)]
        missile_agents = [agent for agent in self.agents if isinstance(agent, MissileAgent)]

        for tru in tru_agents:
            if tru.latest_estimate is not None:
                for missile in missile_agents:
                    missile.update_target_estimate(tru.latest_estimate)

        # 3. Step all agents using model.agents.shuffle_do (Mesa 3.0)
        self.agents.shuffle_do("step") # Use model.agents.shuffle_do for Mesa 3.0
        print(f"Step {self.steps} completed.") # Model.steps increments automatically

    def launch_missile(self):
        pos = self.launch_platform_pos
        missile = MissileAgent(
            model=self,
            pos=pos,
            direction=None,
            speed=1,
            fuel=400,
            initial_target_estimate=[90, 15],
            mode=self.swarm_mode
        )
        self.grid.place_agent(missile, pos)
        self.agents.add(missile)
        print(f"Missile {missile.unique_id} launched at step {self.steps} with pos {missile.pos}")
        self.missile_count += 1
