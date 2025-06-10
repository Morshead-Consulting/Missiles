import math
import random

from mesa import Agent

from sensor import Sensor
from swarm_modes import SwarmMode


class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel, initial_target_estimate=None, mode=None, comms_range=50,
                 min_speed=0.1, max_speed=2.0): # Added min_speed and max_speed
        super().__init__(model)

        self.base_speed = speed      # Store the original speed from launch
        self.speed = speed           # Current effective speed, can be adjusted
        self.min_speed = min_speed   # Minimum allowable speed
        self.max_speed = max_speed   # Maximum allowable speed
        self.fuel = fuel
        self.exploded = False
        self.alive = True
        self.trail = [pos]
        self.sensor = Sensor(range=30, field_of_view_deg=90, noise_std=0.5)
        self.pos = pos
        self.float_pos = list(pos)
        self.direction = direction if direction is not None else (1, 0)
        self.mode = mode

        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        self.sensor_switch_distance = 20.0
        self.comms_range = comms_range
        self.incoming_messages = []

    def update_target_estimate(self, new_estimate):
        """Updates the missile's internal estimate of the target's position."""
        self.estimated_target_pos = list(new_estimate)

    def _receive_message(self, message):
        """Adds an incoming message to the missile's buffer."""
        self.incoming_messages.append(message)

    def step(self):
        """
        Advances the missile's state by one step.
        Dispatches to different guidance logics based on the swarm mode.
        Handles common aspects like fuel consumption, movement, and hit detection.
        """
        print(f"[Step {self.model.steps}] Missile {self.unique_id} - Starting step. Pos: {self.pos}, Fuel: {self.fuel}, Alive: {self.alive}, Mode: {self.mode}")

        if not self.alive:
            print(f"[Missile {self.unique_id}] Inactive. Skipping step.")
            return

        # Reset speed to base at the start of each step, then adjust if needed by guidance.
        # Speed will be clamped to min/max *after* guidance logic.
        self.speed = self.base_speed

        # --- Swarm Mode Specific Guidance Logic ---
        if self.mode == SwarmMode.SIMPLE:
            self._simple_guidance()
        elif self.mode == SwarmMode.OVERWHELM:
            self._overwhelm_guidance()
        elif self.mode == SwarmMode.WAVE:
            self._wave_attack()
        elif self.mode == SwarmMode.RECCE:
            self._recce_logic()
        elif self.mode == SwarmMode.SPLIT_AXIS:
            self._split_axis_approach()
        elif self.mode == SwarmMode.DECOY:
            self._decoy_behaviour()
        else:
            print(f"[Missile {self.unique_id}] Warning: Unknown swarm mode '{self.mode}'. Falling back to simple guidance.")
            self._simple_guidance()

        # --- Apply Speed Constraints ---
        self.speed = max(self.min_speed, min(self.speed, self.max_speed))
        print(f"  [Missile {self.unique_id}] Clamped speed to {self.speed:.2f} (min={self.min_speed}, max={self.max_speed})")


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

        # Move missile based on the direction determined by the guidance mode and current effective speed
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

        # Check for hit after moving to the new position
        cellmates = self.model.grid.get_cell_list_contents([new_pos])
        for other in cellmates:
            if isinstance(other, TargetAgent):
                self.exploded = True
                self.alive = False
                self.model.agents.remove(self)
                self.model.grid.remove_agent(self)
                print(f"[Missile {self.unique_id}] HIT! Target destroyed at {new_pos}.")
                return

        print(f"[Step {self.model.steps}] Missile {self.unique_id} - End step. Pos: {self.pos}, Dir: {self.direction}, Estimate: {self.estimated_target_pos}, Exploded: {self.exploded}")


    def _simple_guidance(self):
        """
        Guidance logic for the SIMPLE swarm mode.
        Each missile independently navigates to the target using the last known target location.
        Missiles do not coordinate or communicate.
        (They do not process incoming_messages in this mode)
        """
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        dx = target.pos[0] - self.pos[0]
        dy = target.pos[1] - self.pos[1]
        dist_to_target = math.hypot(dx, dy)

        if dist_to_target <= self.sensor_switch_distance:
            detected, noisy_rel = self.sensor.run_detection(self.pos, self.direction, target.pos)
            if detected:
                dx_sensor, dy_sensor = noisy_rel
                self.estimated_target_pos = [self.pos[0] + dx_sensor, self.pos[1] + dy_sensor]
            else:
                pass # Use TRU estimate if sensor fails or is out of range

        if self.estimated_target_pos:
            dx_est = self.estimated_target_pos[0] - self.float_pos[0]
            dy_est = self.estimated_target_pos[1] - self.float_pos[1]
            mag_est = math.hypot(dx_est, dy_est)
            self.direction = (dx_est / mag_est, dy_est / mag_est) if mag_est != 0 else (0, 0)
        else:
            self.direction = (1, 0) # Default to forward if no estimate


    def _overwhelm_guidance(self):
        """
        Guidance logic for the OVERWHELM swarm mode ("Saturation Strike").
        Missiles coordinate timing to synchronize arrival, aiming to overload the target's defenses.
        """
        print(f"[Missile {self.unique_id}] Running OVERWHELM guidance. Received {len(self.incoming_messages)} messages.")

        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        
        # 1. Fuse Target Estimates (including own and received from others)
        current_target_estimate = list(self.estimated_target_pos) if self.estimated_target_pos else None
        all_target_estimates = []

        if current_target_estimate:
            all_target_estimates.append(current_target_estimate)

        for message in self.incoming_messages:
            sender_target_estimate = message.get('sender_target_estimate')
            if sender_target_estimate:
                all_target_estimates.append(sender_target_estimate)

        if all_target_estimates:
            fused_x = sum(e[0] for e in all_target_estimates) / len(all_target_estimates)
            fused_y = sum(e[1] for e in all_target_estimates) / len(all_target_estimates)
            self.estimated_target_pos = [fused_x, fused_y]
        else:
            self.estimated_target_pos = target.pos # Default to true target pos for robustness


        # 2. Synchronize Movement (Adjust speed based on swarm's average distance to target)
        # Collect distances to target for all communicating missiles (including self)
        all_missile_distances_to_target = []
        
        own_dx_to_target = target.pos[0] - self.float_pos[0]
        own_dy_to_target = target.pos[1] - self.float_pos[1]
        own_dist_to_target = math.hypot(own_dx_to_target, own_dy_to_target)
        all_missile_distances_to_target.append(own_dist_to_target)

        for message in self.incoming_messages:
            sender_pos = message.get('sender_pos')
            if sender_pos:
                sender_dx_to_target = target.pos[0] - sender_pos[0]
                sender_dy_to_target = target.pos[1] - sender_pos[1]
                sender_dist_to_target = math.hypot(sender_dx_to_target, sender_dy_to_target)
                all_missile_distances_to_target.append(sender_dist_to_target)

        average_swarm_dist_to_target = own_dist_to_target
        if all_missile_distances_to_target: # Ensure there are distances to average
            average_swarm_dist_to_target = sum(all_missile_distances_to_target) / len(all_missile_distances_to_target)

        # Define thresholds for behavior
        # SYNCHRONIZATION_THRESHOLD = 50 # Not explicitly used for action, but context for loiter buffer
        LOITER_BUFFER = 5           # How much closer can a missile be before slowing down
        FINAL_ASSAULT_DISTANCE = 10 # Distance for final full-speed rush

        if own_dist_to_target <= FINAL_ASSAULT_DISTANCE:
            self.speed = self.base_speed # Final assault: full speed ahead
            print(f"  [Missile {self.unique_id}] Overwhelm: Final Assault! Full speed.")
        elif own_dist_to_target < average_swarm_dist_to_target - LOITER_BUFFER:
            # If too far ahead of the average, slow down (loiter)
            # This speed will be clamped by min_speed
            self.speed = self.base_speed * 0.2
            print(f"  [Missile {self.unique_id}] Overwhelm: Loitering. Calculated speed: {self.speed:.2f}")
        else:
            self.speed = self.base_speed # Otherwise, maintain base speed

        # 3. Adjust Direction (Always towards the fused estimated target position)
        if self.estimated_target_pos:
            dx_est = self.estimated_target_pos[0] - self.float_pos[0]
            dy_est = self.estimated_target_pos[1] - self.float_pos[1]
            mag_est = math.hypot(dx_est, dy_est)
            self.direction = (dx_est / mag_est, dy_est / mag_est) if mag_est != 0 else (0, 0)
        else:
            self.direction = (1, 0) # Fallback direction (shouldn't happen with robust fusion)

        # Crucial: Clear messages after processing for the current step
        self.incoming_messages = []


    def _wave_attack(self):
        """Placeholder for WAVE attack logic."""
        print(f"[Missile {self.unique_id}] Running WAVE attack (placeholder).")
        self._simple_guidance() # Fallback

    def _recce_logic(self):
        """Placeholder for RECCE logic."""
        print(f"[Missile {self.unique_id}] Running RECCE logic (placeholder).")
        self._simple_guidance() # Fallback

    def _split_axis_approach(self):
        """Placeholder for SPLIT_AXIS approach logic."""
        print(f"[Missile {self.unique_id}] Running SPLIT_AXIS approach (placeholder).")
        self._simple_guidance() # Fallback

    def _decoy_behaviour(self):
        """Placeholder for DECOY behaviour logic."""
        print(f"[Missile {self.unique_id}] Running DECOY behaviour (placeholder).")
        self._simple_guidance() # Fallback


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

