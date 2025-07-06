import math
import random
from mesa import Agent

from sensor import Sensor
from swarm_modes import SwarmMode # Import SwarmMode for dispatching
from target_agent import TargetAgent

class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel, initial_target_estimate=None, mode=None, comms_range=50,
                 min_speed=0.1, max_speed=2.0, wave_id=0, missile_type=None,
                 sensor_range=30, sensor_field_of_view_deg=90, sensor_noise_std=0.5):
        super().__init__(model)

        self.base_speed = speed
        self.speed = speed
        self.min_speed = min_speed
        self.max_speed = max_speed
        self.fuel = fuel
        self.exploded = False
        self.alive = True
        self.trail = [pos]
        self.sensor = Sensor(range=sensor_range, field_of_view_deg=sensor_field_of_view_deg, noise_std=sensor_noise_std)
        self.pos = pos
        self.float_pos = list(pos)
        self.direction = direction if direction is not None else (1, 0)
        self.mode = mode
        self.wave_id = wave_id
        self.comms_range = comms_range
        self.incoming_messages = []

        self.missile_type = missile_type
        self.recce_state = None

        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        self.sensor_switch_distance = 20.0

    def update_target_estimate(self, new_estimate):
        self.estimated_target_pos = list(new_estimate)

    def _receive_message(self, message):
        self.incoming_messages.append(message)

    def _get_direction_vector(self, target_coord):
        if target_coord is None:
            return (1, 0)

        dx = target_coord[0] - self.float_pos[0]
        dy = target_coord[1] - self.float_pos[1]
        
        distance = math.hypot(dx, dy)

        if distance < 1e-6:
            perturb_x = random.uniform(-0.1, 0.1)
            perturb_y = random.uniform(-0.1, 0.1)
            
            new_dir_x = self.direction[0] + perturb_x
            new_dir_y = self.direction[1] + perturb_y
            
            new_mag = math.hypot(new_dir_x, new_dir_y)
            if new_mag > 0:
                return (new_dir_x / new_mag, new_dir_y / new_mag)
            else:
                return (1, 0)

        return (dx / distance, dy / distance)

    def perform_guidance(self):
        """
        Chooses the missile's direction based on its swarm mode.
        For RL mode, this method does nothing as the RL agent will set its own direction.
        """
        self.speed = self.base_speed # Reset speed for guidance, can be modified by guidance logic

        if self.mode == SwarmMode.SIMPLE:
            from guidance_strategies import simple_guidance
            simple_guidance(self)
        elif self.mode == SwarmMode.OVERWHELM:
            from guidance_strategies import overwhelm_guidance
            overwhelm_guidance(self)
        elif self.mode == SwarmMode.WAVE:
            from guidance_strategies import wave_attack
            wave_attack(self)
        elif self.mode == SwarmMode.RECCE:
            from guidance_strategies import recce_logic
            recce_logic(self)
        elif self.mode == SwarmMode.SPLIT_AXIS:
            from guidance_strategies import split_axis_approach
            split_axis_approach(self)
        elif self.mode == SwarmMode.DECOY:
            from guidance_strategies import decoy_behaviour
            decoy_behaviour(self)
        elif self.mode == SwarmMode.RL:
            # For RL mode, the RL agent will handle direction and speed
            pass
        else:
            print(f"[Missile {self.unique_id}] Warning: Unknown swarm mode '{self.mode}'. Falling back to simple guidance.")
            from guidance_strategies import simple_guidance
            simple_guidance(self)
        
        # Apply Speed Constraints after guidance might have changed speed
        self.speed = max(self.min_speed, min(self.speed, self.max_speed))


    def move_and_check_hit(self):
        """
        Applies speed, consumes fuel, moves the missile, and checks for hits.
        """
        if self.direction is None:
            print(f"[Missile {self.unique_id}] ERROR: No direction set. Stopping missile.")
            self.alive = False
            self.model.agents.remove(self)
            self.model.grid.remove_agent(self)
            return

        self.fuel -= 1
        if self.fuel <= 0:
            self.alive = False
            self.model.agents.remove(self)
            self.model.grid.remove_agent(self)
            print(f"[Missile {self.unique_id}] Ran out of fuel and is now inactive.")
            return

        self.float_pos[0] += self.direction[0] * self.speed
        self.float_pos[1] += self.direction[1] * self.speed

        new_x = int(round(self.float_pos[0]))
        new_y = int(round(self.float_pos[1]))

        new_x = max(0, min(new_x, self.model.grid.width - 1))
        new_y = max(0, min(new_y, self.model.grid.height - 1))
        new_pos = (new_x, new_y)

        if self.alive:
            self.trail.append(self.pos)

        if new_pos != self.pos:
            self.model.grid.move_agent(self, new_pos)
            self.pos = new_pos

        print(f"[Missile {self.unique_id}] Moved to {new_pos} | Direction: {self.direction} | Fuel left: {self.fuel} | Current Speed: {self.speed}")

        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                self.model.agents.remove(self)
                self.model.grid.remove_agent(self)
                print(f"[Missile {self.unique_id}] HIT! Target destroyed at {new_pos}.")
                return

    def step(self):
        """
        Advances the missile's state by one step.
        Calls perform_guidance() and then move_and_check_hit().
        """
        print(f"[Step {self.model.steps}] Missile {self.unique_id} - Starting step. Pos: {self.pos}, Fuel: {self.fuel}, Alive: {self.alive}, Mode: {self.mode}, Type: {self.missile_type.name}")

        if not self.alive:
            print(f"[Missile {self.unique_id}] Inactive. Skipping step.")
            return
        
        self.perform_guidance()
        self.move_and_check_hit()

        print(f"[Step {self.model.steps}] Missile {self.unique_id} - End step. Pos: {self.pos}, Dir: {self.direction}, Estimate: {self.estimated_target_pos}, Exploded: {self.exploded}")