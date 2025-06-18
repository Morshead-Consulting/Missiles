import math
import random
from mesa import Agent

from sensor import Sensor
from swarm_modes import SwarmMode # Import SwarmMode for dispatching
from target_agent import TargetAgent

class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel, initial_target_estimate=None, mode=None, comms_range=50,
                 min_speed=0.1, max_speed=2.0, wave_id=0, missile_type=None, # missile_type is from swarm_modes, not here
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

        # MissileType and RecceState remain properties of MissileAgent
        # but RecceState is only relevant for attackers in Recce mode
        self.missile_type = missile_type
        self.recce_state = None # Will be set to RecceState.INITIAL_LOITER if mode is RECCE and type is ATTACKER


        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        self.sensor_switch_distance = 20.0 # Distance for missile's own sensor to activate

    def update_target_estimate(self, new_estimate):
        """Updates the missile's internal estimate of the target's position."""
        self.estimated_target_pos = list(new_estimate)

    def _receive_message(self, message):
        """Adds an incoming message to the missile's buffer."""
        self.incoming_messages.append(message)

    def _get_direction_vector(self, target_coord):
        """
        Calculates a normalized direction vector from the missile's current position
        towards a target coordinate. Ensures the vector is never (0,0) to prevent stalling.
        """
        if target_coord is None:
            return (1, 0) # Default to forward if no target specified

        dx = target_coord[0] - self.float_pos[0]
        dy = target_coord[1] - self.float_pos[1]
        
        distance = math.hypot(dx, dy)

        # If the distance is extremely small, add a slight random perturbation
        if distance < 1e-6: # Using a very small epsilon (e.g., 0.000001)
            perturb_x = random.uniform(-0.1, 0.1)
            perturb_y = random.uniform(-0.1, 0.1)
            
            new_dir_x = self.direction[0] + perturb_x
            new_dir_y = self.direction[1] + perturb_y
            
            new_mag = math.hypot(new_dir_x, new_dir_y)
            if new_mag > 0:
                return (new_dir_x / new_mag, new_dir_y / new_mag)
            else:
                return (1, 0) # Fallback if perturbation results in zero vector

        return (dx / distance, dy / distance)

    def step(self):
        """
        Advances the missile's state by one step.
        Dispatches to different guidance logics based on the swarm mode.
        Handles common aspects like fuel consumption, movement, and hit detection.
        """
        print(f"[Step {self.model.steps}] Missile {self.unique_id} - Starting step. Pos: {self.pos}, Fuel: {self.fuel}, Alive: {self.alive}, Mode: {self.mode}, Type: {self.missile_type.name}")

        if not self.alive:
            print(f"[Missile {self.unique_id}] Inactive. Skipping step.")
            return

        self.speed = self.base_speed

        # --- Dispatch to external guidance strategies ---
       
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
        else:
            print(f"[Missile {self.unique_id}] Warning: Unknown swarm mode '{self.mode}'. Falling back to simple guidance.")
            from guidance_strategies import simple_guidance
            simple_guidance(self)

        # --- Apply Speed Constraints ---
        self.speed = max(self.min_speed, min(self.speed, self.max_speed))


        # --- Common Post-Guidance Logic (Fuel, Movement, Hit Detection) ---
        if self.direction is None:
            print(f"[Missile {self.unique_id}] ERROR: No direction set after guidance for mode {self.mode}. Stopping missile.")
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
            if isinstance(other, TargetAgent): # TargetAgent will be imported from target_agent.py
                self.exploded = True
                self.alive = False
                self.model.agents.remove(self)
                self.model.grid.remove_agent(self)
                print(f"[Missile {self.unique_id}] HIT! Target destroyed at {new_pos}.")
                return

        print(f"[Step {self.model.steps}] Missile {self.unique_id} - End step. Pos: {self.pos}, Dir: {self.direction}, Estimate: {self.estimated_target_pos}, Exploded: {self.exploded}")

