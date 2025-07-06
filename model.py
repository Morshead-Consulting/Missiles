from mesa.model import Model
from mesa.space import MultiGrid

from base_agent import MissileAgent
from target_agent import TargetAgent
from TargetReportingUnit import TargetReportingUnit
from swarm_modes import SwarmMode, MissileType
from missile_rl_agent import MissileRLAgent
import math
import random


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

        self.missile_count = 0  # Total missiles launched so far
        self.NUM_WAVES = 3
        self.SCOUT_RATIO = 0.2

        # New: Pre-calculate the exact number of scouts and attackers
        if self.swarm_mode == SwarmMode.RECCE:
            self.total_scouts = max(2, int(self.num_missiles * self.SCOUT_RATIO)) # Ensure at least 2 scouts
            self.total_attackers = self.num_missiles - self.total_scouts
            if self.total_attackers < 0: # Ensure we don't have negative attackers if num_missiles is very small
                self.total_attackers = 0
                self.total_scouts = self.num_missiles # All become scouts if num_missiles <= 2
            print(f"Recce Mode: Planning to launch {self.total_scouts} scouts and {self.total_attackers} attackers.")
        else:
            self.total_scouts = 0 # Not relevant for other modes
            self.total_attackers = self.num_missiles


        # Counters for launched types (to enforce launch order)
        self.scouts_launched_count = 0
        self.attackers_launched_count = 0


        # Define sensor capabilities for different missile types
        self.ATTACKER_SENSOR_PARAMS = {
            'sensor_range': 30,
            'sensor_field_of_view_deg': 90,
            'sensor_noise_std': 0.5
        }
        self.SCOUT_SENSOR_PARAMS = {
            'sensor_range': 60,
            'sensor_field_of_view_deg': 120,
            'sensor_noise_std': 0.2
        }


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

        self.launch_platform_pos = (0, height // 2)

    def step(self):
        print(f"Step {self.steps} starting...")

        # --- Communication Phase ---
        for agent in self.agents:
            if isinstance(agent, MissileAgent):
                agent.incoming_messages = []

        missile_agents = [agent for agent in self.agents if isinstance(agent, MissileAgent)]
        for sender_missile in missile_agents:
            if not sender_missile.alive:
                continue

            message_to_send = {
                'sender_id': sender_missile.unique_id,
                'sender_pos': sender_missile.pos,
                'sender_target_estimate': sender_missile.estimated_target_pos,
                'sender_speed': sender_missile.speed,
                'sender_fuel': sender_missile.fuel,
                'sender_wave_id': sender_missile.wave_id,
                'sender_type': sender_missile.missile_type.value
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

        # 5. Step all agents
        self.agents.shuffle_do("step")
        print(f"Step {self.steps} completed.")

    def launch_missile(self):
        pos = self.launch_platform_pos
        DEFAULT_MIN_MISSILE_SPEED = 0.1
        DEFAULT_MAX_MISSILE_SPEED = 2.0
        
        current_wave_id = self.missile_count % self.NUM_WAVES

        assigned_missile_type = MissileType.ATTACKER # Default

        # New: Logic to enforce launch order (Scouts first, then Attackers)
        if self.swarm_mode == SwarmMode.RECCE:
            if self.scouts_launched_count < self.total_scouts:
                # Launch a scout
                assigned_missile_type = MissileType.SCOUT
                self.scouts_launched_count += 1
                sensor_params_for_missile = self.SCOUT_SENSOR_PARAMS
                print(f"Launching Scout {self.scouts_launched_count}/{self.total_scouts}...")
            elif self.attackers_launched_count < self.total_attackers:
                # Launch an attacker
                assigned_missile_type = MissileType.ATTACKER
                self.attackers_launched_count += 1
                sensor_params_for_missile = self.ATTACKER_SENSOR_PARAMS
                print(f"Launching Attacker {self.attackers_launched_count}/{self.total_attackers}...")
            else:
                # Should not happen if num_missiles limit is respected
                print("Warning: Attempted to launch missile beyond total_scouts + total_attackers count.")
                return # Do not launch
        else:
            # For non-Recce modes, use default attacker parameters for all missiles
            assigned_missile_type = MissileType.ATTACKER
            sensor_params_for_missile = self.ATTACKER_SENSOR_PARAMS

        # Choose the appropriate missile class
        if self.swarm_mode == SwarmMode.RL:
            missile_class = MissileRLAgent
        else:
            missile_class = MissileAgent

        missile = missile_class(
            model=self,
            pos=pos,
            direction=None,
            speed=1, # Base speed for launch
            fuel=400,
            initial_target_estimate=[90, 15],
            mode=self.swarm_mode,
            comms_range=50,
            min_speed=DEFAULT_MIN_MISSILE_SPEED,
            max_speed=DEFAULT_MAX_MISSILE_SPEED,
            wave_id=current_wave_id,
            missile_type=assigned_missile_type,
            **sensor_params_for_missile
        )
        self.grid.place_agent(missile, pos)
        self.agents.add(missile)
        self.missile_count += 1 # Increment total launched missiles
        print(f"Missile {missile.unique_id} (Type: {missile.missile_type.name}, Wave: {missile.wave_id}) launched at step {self.steps} from {missile.pos}")

