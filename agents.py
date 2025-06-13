import math
import random

from mesa import Agent

from sensor import Sensor
from swarm_modes import SwarmMode, MissileType, RecceState


class MissileAgent(Agent):
    def __init__(self, model, pos, direction, speed, fuel, initial_target_estimate=None, mode=None, comms_range=50,
                 min_speed=0.1, max_speed=2.0, wave_id=0, missile_type=MissileType.ATTACKER,
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
        self.recce_state = RecceState.INITIAL_LOITER


        if initial_target_estimate is not None:
            self.estimated_target_pos = list(initial_target_estimate)
        else:
            self.estimated_target_pos = None

        self.sensor_switch_distance = 20.0

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
            # Generate a small random perturbation around the current direction
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
        """
        self.direction = self._get_direction_vector(self.estimated_target_pos)


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
            self.estimated_target_pos = [self.pos[0] + 1, self.pos[1]] # Fallback forward guess


        # 2. Synchronize Movement (Adjust speed based on swarm's average distance to target)
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
        if all_missile_distances_to_target:
            average_swarm_dist_to_target = sum(all_missile_distances_to_target) / len(all_missile_distances_to_target)

        LOITER_BUFFER = 5
        FINAL_ASSAULT_DISTANCE = 10

        if own_dist_to_target <= FINAL_ASSAULT_DISTANCE:
            self.speed = self.base_speed
            print(f"  [Missile {self.unique_id}] Overwhelm: Final Assault! Full speed.")
        elif own_dist_to_target < average_swarm_dist_to_target - LOITER_BUFFER:
            self.speed = self.base_speed * 0.2
            print(f"  [Missile {self.unique_id}] Overwhelm: Loitering. Calculated speed: {self.speed:.2f}")
        else:
            self.speed = self.base_speed

        self.direction = self._get_direction_vector(self.estimated_target_pos)

        self.incoming_messages = []


    def _wave_attack(self):
        """
        Guidance logic for the WAVE swarm mode ("Pulse Attack").
        Missiles self-organize into temporal waves to apply sustained pressure.
        """
        print(f"[Missile {self.unique_id}] Running WAVE attack for Wave ID: {self.wave_id}. Received {len(self.incoming_messages)} messages.")

        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        
        # 1. Fuse Target Estimates (same as Overwhelm)
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
            self.estimated_target_pos = [self.pos[0] + 1, self.pos[1]] # Fallback forward guess


        # 2. Wave Synchronization (Adjust speed based on wave's average distance and staggering)
        relevant_messages = [
            msg for msg in self.incoming_messages
            if msg.get('sender_wave_id') == self.wave_id
        ]

        all_missile_distances_in_wave = []
        
        own_dx_to_target = target.pos[0] - self.float_pos[0]
        own_dy_to_target = target.pos[1] - self.float_pos[1]
        own_dist_to_target = math.hypot(own_dx_to_target, own_dy_to_target)
        all_missile_distances_in_wave.append(own_dist_to_target)

        for message in relevant_messages:
            sender_pos = message.get('sender_pos')
            if sender_pos:
                sender_dx_to_target = target.pos[0] - sender_pos[0]
                sender_dy_to_target = target.pos[1] - sender_pos[1]
                sender_dist_to_target = math.hypot(sender_dx_to_target, sender_dy_to_target)
                all_missile_distances_in_wave.append(sender_dist_to_target)

        average_wave_dist_to_target = own_dist_to_target
        if all_missile_distances_in_wave:
            average_wave_dist_to_target = sum(all_missile_distances_in_wave) / len(all_missile_distances_in_wave)

        BASE_LOITER_BUFFER = 5
        BASE_FINAL_ASSAULT_DISTANCE = 10
        WAVE_STAGGER_INCREMENT = 15

        staggered_final_assault_distance = BASE_FINAL_ASSAULT_DISTANCE + (self.wave_id * WAVE_STAGGER_INCREMENT)
        staggered_loiter_buffer_target_dist = average_wave_dist_to_target - BASE_LOITER_BUFFER


        if own_dist_to_target <= staggered_final_assault_distance:
            self.speed = self.base_speed
            print(f"  [Missile {self.unique_id}] Wave {self.wave_id}: Final Assault! Full speed.")
        elif own_dist_to_target < staggered_loiter_buffer_target_dist:
            self.speed = self.base_speed * 0.2
            print(f"  [Missile {self.unique_id}] Wave {self.wave_id}: Loitering. Calculated speed: {self.speed:.2f}")
        else:
            self.speed = self.base_speed

        self.direction = self._get_direction_vector(self.estimated_target_pos)

        self.incoming_messages = []



    def _recce_logic(self):
        """
        RECCE mode: scouts explore and relay estimates; attackers act only on confirmed estimates.
        """
        print(f"[Missile {self.unique_id}] RECCE | Type: {self.missile_type.name} | State: {self.recce_state.name} | Messages: {len(self.incoming_messages)}")

        # TRU updates self.estimated_target_pos *before* this method runs in model.step.
        # So, self.estimated_target_pos at this point contains the latest TRU data.

        fresh_scout_estimates_from_comms = []
        # Collect NEW estimates from incoming scout messages only
        for message in self.incoming_messages:
            sender_type_val = message.get('sender_type')
            sender_type = MissileType(sender_type_val) if sender_type_val is not None else None
            if sender_type == MissileType.SCOUT:
                est = message.get('sender_target_estimate')
                if est:
                    fresh_scout_estimates_from_comms.append(est)
        
        # Priority for setting THIS STEP's estimated_target_pos:
        # 1. Fresh Scout Data (from comms this step)
        # 2. Missile's own TRU-fed estimate (from model.step) - this is the fallback.
        # 3. Simple Forward Guess (if absolutely no estimate exists from TRU either).
        
        if fresh_scout_estimates_from_comms:
            # If fresh scout estimates are available this step, fuse and use them.
            fused_x = sum(e[0] for e in fresh_scout_estimates_from_comms) / len(fresh_scout_estimates_from_comms)
            fused_y = sum(e[1] for e in fresh_scout_estimates_from_comms) / len(fresh_scout_estimates_from_comms)
            self.estimated_target_pos = [fused_x, fused_y]
            print(f"  [Missile {self.unique_id}] Recce: Target estimate updated from FRESH scouts.")
        elif self.estimated_target_pos is None:
            # If no fresh scouts AND missile currently has no estimate (e.g., very early in sim or TRU fails)
            self.estimated_target_pos = [self.float_pos[0] + 1, self.float_pos[1]]
            print(f"  [Missile {self.unique_id}] Recce: No estimates available. Guessing forward.")
        else:
            # Otherwise, retain the missile's current self.estimated_target_pos (from TRU or previous scout fusion).
            # This handles the case where TRU is providing the best, but not necessarily "fresh scout" data.
            print(f"  [Missile {self.unique_id}] Recce: Retaining current TRU/previous scout estimate.")


        # --- Role-Specific Behavior ---
        
        if self.missile_type == MissileType.SCOUT:
            self._recce_scout_behavior()
        elif self.missile_type == MissileType.ATTACKER:
            self._recce_attacker_behavior(fresh_scout_estimates_from_comms) # Pass for state transition check

        self.incoming_messages.clear()


    def _collect_scout_estimates(self):
        """Extract fresh estimates from incoming scout messages."""
        estimates = []
        for msg in self.incoming_messages:
            sender_type_val = msg.get('sender_type')
            sender_type = MissileType(sender_type_val) if sender_type_val is not None else None
            if sender_type == MissileType.SCOUT:
                est = msg.get('sender_target_estimate')
                if est:
                    estimates.append(est)
        return estimates

    def _recce_scout_behavior(self):
        """Scout behavior: move fast with lateral dispersion."""
        print(f"  [Missile {self.unique_id}] Recce: SCOUT behavior.")
        self.speed = self.base_speed
        base_dir = self._get_direction_vector(self.estimated_target_pos)

        # Apply wider lateral offset
        lateral_offset = random.uniform(-0.3, 0.3)
        offset_x = -base_dir[1] * lateral_offset
        offset_y = base_dir[0] * lateral_offset

        new_dir_x = base_dir[0] + offset_x
        new_dir_y = base_dir[1] + offset_y
        mag = math.hypot(new_dir_x, new_dir_y)

        self.direction = (new_dir_x / mag, new_dir_y / mag) if mag else (1, 0)

    def _recce_attacker_behavior(self, fresh_scout_estimates_from_comms):
        """Attacker behavior: loiter until confirmed, then engage and continue refining estimate."""
        print(f"  [Missile {self.unique_id}] Recce: ATTACKER | State: {self.recce_state.name}")

        if self.recce_state == RecceState.INITIAL_LOITER:
            self.speed = self.min_speed
            
            # Transition to CONFIRMED_ATTACK if *any* fresh scout estimate was received this step
            if fresh_scout_estimates_from_comms:
                self.recce_state = RecceState.CONFIRMED_ATTACK
                self.speed = self.base_speed # Accelerate to base speed for attack
                print(f"  [Missile {self.unique_id}] Recce: ATTACKER transitioned to CONFIRMED_ATTACK!")

            self.direction = self._get_direction_vector(self.estimated_target_pos)

        elif self.recce_state == RecceState.CONFIRMED_ATTACK:
            self.speed = self.base_speed
            
            # In CONFIRMED_ATTACK, the missile's own sensor is the highest priority for terminal guidance.
            target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
            detected, rel_pos = self.sensor.run_detection(self.float_pos, self.direction, target.pos)

            if detected and rel_pos:
                # Use missile's own sensor for direct terminal guidance
                sensed_x = self.float_pos[0] + rel_pos[0]
                sensed_y = self.float_pos[1] + rel_pos[1]
                self.estimated_target_pos = [sensed_x, sensed_y] # OVERRIDE with direct sensor data
                print(f"  [Missile {self.unique_id}] Recce: Using OWN SENSOR estimate for terminal phase.")
            else:
                # If own sensor doesn't detect, rely on self.estimated_target_pos (updated by TRU/scouts in _recce_logic)
                print(f"  [Missile {self.unique_id}] Recce: No local sensor. Relying on latest fused estimate.")
            
            self.direction = self._get_direction_vector(self.estimated_target_pos)       

    def _split_axis_approach(self):
        """
        Split-Axis: Missiles approach from different compass directions,
        then switch to direct attack when close to the target.
        """
        print(f"[Missile {self.unique_id}] SPLIT_AXIS: Starting maneuver.")

        # Assign a fixed approach direction based on unique ID
        approach_direction = self.unique_id % 4
        direction_names = ['EAST', 'WEST', 'NORTH', 'SOUTH']
        print(f"  [Missile {self.unique_id}] Approach Direction: {direction_names[approach_direction]}")

        # Get current target position estimate (using a simplified fusion for this mode)
        # Note: This mode's fusion logic is simpler than Recce mode's.
        current_target_estimate = list(self.estimated_target_pos) if self.estimated_target_pos else None
        all_estimates = []
        if current_target_estimate:
            all_estimates.append(current_target_estimate)
        for msg in self.incoming_messages:
            est = msg.get('sender_target_estimate')
            if est:
                all_estimates.append(est)
        if all_estimates:
            fused_x = sum(e[0] for e in all_estimates) / len(all_estimates)
            fused_y = sum(e[1] for e in all_estimates) / len(all_estimates)
            self.estimated_target_pos = [fused_x, fused_y]
        else:
            self.estimated_target_pos = [self.float_pos[0] + 1, self.float_pos[1]] # Fallback if no estimates


        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        
        # Distance to target (true target for decision, estimated for guidance until terminal phase)
        dx_to_true_target = target.pos[0] - self.float_pos[0]
        dy_to_true_target = target.pos[1] - self.float_pos[1]
        dist_to_true_target = math.hypot(dx_to_true_target, dy_to_true_target)
        TERMINAL_DISTANCE = 40

        # === Terminal Attack Phase ===
        if dist_to_true_target < TERMINAL_DISTANCE:
            print(f"  [Missile {self.unique_id}] SPLIT_AXIS: Switching to direct attack (terminal phase).")
            # In terminal phase, prioritize direct targeting to actual target
            self.direction = self._get_direction_vector(target.pos) # Direct to true target for final attack
            self.speed = self.base_speed
            return

        # === Approach Phase ===
        offset_distance = 50
        if approach_direction == 0:   # EAST (from right side)
            aim_point = [target.pos[0] + offset_distance, target.pos[1]]
        elif approach_direction == 1: # WEST (from left side)
            aim_point = [target.pos[0] - offset_distance, target.pos[1]]
        elif approach_direction == 2: # NORTH (from top side)
            aim_point = [target.pos[0], target.pos[1] - offset_distance]
        else:                         # SOUTH (from bottom side)
            aim_point = [target.pos[0], target.pos[1] + offset_distance]

        self.direction = self._get_direction_vector(aim_point)

        # === Speed Coordination (similar to Overwhelm/Wave for group cohesion) ===
        # Use relative distance to target for speed adjustments
        distances_to_target = [dist_to_true_target] # Start with own true distance
        for msg in self.incoming_messages:
            sender_pos = msg.get("sender_pos")
            if sender_pos:
                # Calculate sender's distance to target (true target for this coordination)
                dx2 = target.pos[0] - sender_pos[0]
                dy2 = target.pos[1] - sender_pos[1]
                distances_to_target.append(math.hypot(dx2, dy2))

        avg_dist_swarm = sum(distances_to_target) / len(distances_to_target)
        cohesion_buffer = 10 # How much buffer around the average to allow

        if dist_to_true_target < avg_dist_swarm - cohesion_buffer:
            self.speed = self.min_speed # Slow down if too far ahead of average
            print(f"  [Missile {self.unique_id}] SPLIT_AXIS: Loitering (ahead of group). Speed: {self.speed:.2f}")
        elif dist_to_true_target > avg_dist_swarm + cohesion_buffer:
            self.speed = self.max_speed # Speed up if too far behind
            print(f"  [Missile {self.unique_id}] SPLIT_AXIS: Accelerating (behind group). Speed: {self.speed:.2f}")
        else:
            self.speed = self.base_speed # Maintain base speed
            print(f"  [Missile {self.unique_id}] SPLIT_AXIS: Maintaining position. Speed: {self.speed:.2f}")

        self.incoming_messages.clear()


    def _fuse_target_estimates_with_messages(self):
        """
        Helper for other modes (not Recce), fuses own estimate with incoming messages.
        (Note: For Recce, _recce_logic handles fusion and has different priority).
        This helper is primarily for modes like OVERWHELM and WAVE.
        """
        estimates = [self.estimated_target_pos] if self.estimated_target_pos else []
        for msg in self.incoming_messages:
            est = msg.get('sender_target_estimate')
            if est:
                estimates.append(est)
        if estimates:
            avg_x = sum(e[0] for e in estimates) / len(estimates)
            avg_y = sum(e[1] for e in estimates) / len(estimates)
            self.estimated_target_pos = [avg_x, avg_y]

    def _decoy_behaviour(self):
        """
        DECOY behavior: Simulate attack profiles until a late phase, then diverge or self-destruct.
        Meant to cause defensive misallocation.
        """
        print(f"[Missile {self.unique_id}] DECOY: Starting behavior.")

        # Decoys primarily rely on their own estimated_target_pos (updated by TRU)
        # They DO NOT use scout estimates to avoid real-time refinement that might pull them to actual target.
        
        target = next(agent for agent in self.model.agents if isinstance(agent, TargetAgent))
        
        # Calculate distance to the actual target (to decide when to divert)
        dx_to_true_target = target.pos[0] - self.float_pos[0]
        dy_to_true_target = target.pos[1] - self.float_pos[1]
        dist_to_true_target = math.hypot(dx_to_true_target, dy_to_true_target)

        # Constants for decoy behavior
        DECOY_DIVERGE_DISTANCE = 80 # Distance from target at which decoys start to diverge
        DECOY_SELF_DESTRUCT_DISTANCE = 10 # Distance at which decoy self-destructs if it somehow gets too close

        if dist_to_true_target <= DECOY_SELF_DESTRUCT_DISTANCE:
            # If a decoy somehow gets critically close, self-destruct to ensure it doesn't hit
            self.exploded = True
            self.alive = False
            self.model.agents.remove(self)
            self.model.grid.remove_agent(self)
            print(f"  [Missile {self.unique_id}] DECOY: Too close to target ({dist_to_true_target:.2f} units). Self-destructed!")
            return

        elif dist_to_true_target <= DECOY_DIVERGE_DISTANCE:
            # Late phase: Diverge from target (e.g., dive early)
            print(f"  [Missile {self.unique_id}] DECOY: Diverging at {dist_to_true_target:.2f} units.")
            self.speed = self.base_speed # Maintain speed during dive

            # Calculate a new "divert" target that's significantly below or above the current target position
            # This makes them fly past or dive into the sea
            divert_x = self.estimated_target_pos[0]
            divert_y = self.estimated_target_pos[1] + random.uniform(50, 100) * random.choice([-1, 1]) # Divert vertically

            # Make them also turn slightly away horizontally
            divert_x += random.uniform(20, 50) * random.choice([-1, 1])

            self.direction = self._get_direction_vector([divert_x, divert_y])
            print(f"  [Missile {self.unique_id}] DECOY: New divert direction towards {divert_x:.2f},{divert_y:.2f}.")

        else:
            # Early phase: Act like a real missile, advance towards the estimated target
            print(f"  [Missile {self.unique_id}] DECOY: Simulating attack profile.")
            self.speed = self.base_speed # Advance at base speed
            self.direction = self._get_direction_vector(self.estimated_target_pos)

        self.incoming_messages.clear()


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

        if self.pos is None:
            print(f"[Step {self.model.steps}] Target {self.unique_id} - Skipping step: not on grid.")
            return  # Don't do anything if the agent is no longer on the grid

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

