from mesa.model import Model
from mesa.space import MultiGrid

from agents import MissileAgent, TargetAgent
from TargetReportingUnit import TargetReportingUnit
from swarm_modes import SwarmMode # Import SwarmMode from the new file
import math # Import math for distance calculation


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

        # --- Communication Phase (Order matters for coordination) ---
        # 1. Clear incoming messages for all missiles from previous step
        for agent in self.agents:
            if isinstance(agent, MissileAgent):
                agent.incoming_messages = []

        # 2. Perform broadcast communication (missiles share info with neighbors)
        missile_agents = [agent for agent in self.agents if isinstance(agent, MissileAgent)]
        for sender_missile in missile_agents:
            if not sender_missile.alive:
                continue

            # Create the message to send
            message_to_send = {
                'sender_id': sender_missile.unique_id,
                'sender_pos': sender_missile.pos,
                'sender_target_estimate': sender_missile.estimated_target_pos,
                'sender_speed': sender_missile.speed, # Include sender's current speed
                'sender_fuel': sender_missile.fuel # Include sender's fuel
            }

            for receiver_missile in missile_agents:
                if sender_missile.unique_id == receiver_missile.unique_id or not receiver_missile.alive:
                    continue

                distance = math.hypot(sender_missile.pos[0] - receiver_missile.pos[0],
                                      sender_missile.pos[1] - receiver_missile.pos[1])

                if distance <= sender_missile.comms_range:
                    receiver_missile._receive_message(message_to_send)

        # 3. Missile launching
        if self.steps - self.last_launch_step >= self.launch_interval and self.missile_count < self.num_missiles:
            self.launch_missile()
            self.last_launch_step = self.steps
        print(f"Missiles now: {len([a for a in self.agents if isinstance(a, MissileAgent)])}")

        # 4. TRUs update all missiles with new estimates
        tru_agents = [agent for agent in self.agents if isinstance(agent, TargetReportingUnit)]
        missile_agents_still_alive = [agent for agent in self.agents if isinstance(agent, MissileAgent) and agent.alive]

        for tru in tru_agents:
            if tru.latest_estimate is not None:
                for missile in missile_agents_still_alive:
                    missile.update_target_estimate(tru.latest_estimate)

        # 5. Step all agents (Missiles will now process their newly received messages and adjust speed)
        self.agents.shuffle_do("step")
        print(f"Step {self.steps} completed.")

    def launch_missile(self):
        pos = self.launch_platform_pos
        # Define default min/max speeds for newly launched missiles
        DEFAULT_MIN_MISSILE_SPEED = 0.1
        DEFAULT_MAX_MISSILE_SPEED = 2.0
        
        missile = MissileAgent(
            model=self,
            pos=pos,
            direction=None,
            speed=1, # Base speed of 1
            fuel=400,
            initial_target_estimate=[90, 15],
            mode=self.swarm_mode,
            comms_range=50,
            min_speed=DEFAULT_MIN_MISSILE_SPEED, # Pass min_speed
            max_speed=DEFAULT_MAX_MISSILE_SPEED  # Pass max_speed
        )
        self.grid.place_agent(missile, pos)
        self.agents.add(missile)
        print(f"Missile {missile.unique_id} launched at step {self.steps} with pos {missile.pos}")
        self.missile_count += 1

