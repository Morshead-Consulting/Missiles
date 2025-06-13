import math
import random
from swarm_modes import SwarmMode, MissileType, RecceState
from target_agent import TargetAgent # Import TargetAgent as it's used in some strategies


def _fuse_estimates(estimates_list):
    """Helper to average a list of estimated target positions."""
    if not estimates_list:
        return None
    
    avg_x = sum(e[0] for e in estimates_list) / len(estimates_list)
    avg_y = sum(e[1] for e in estimates_list) / len(estimates_list)
    return [avg_x, avg_y]


def simple_guidance(missile):
    """
    Guidance logic for the SIMPLE swarm mode.
    Each missile independently navigates to the target using the last known target location.
    Missiles do not coordinate or communicate.
    """
    missile.direction = missile._get_direction_vector(missile.estimated_target_pos)
    print(f"  [Missile {missile.unique_id}] Simple: Guiding to {missile.estimated_target_pos}")


def overwhelm_guidance(missile):
    """
    Guidance logic for the OVERWHELM swarm mode ("Saturation Strike").
    Missiles coordinate timing to synchronize arrival, aiming to overload the target's defenses.
    """
    print(f"[Missile {missile.unique_id}] Running OVERWHELM guidance. Received {len(missile.incoming_messages)} messages.")

    target = next(agent for agent in missile.model.agents if isinstance(agent, TargetAgent))
    
    # 1. Fuse Target Estimates (including own and received from others)
    all_target_estimates = []
    if missile.estimated_target_pos:
        all_target_estimates.append(missile.estimated_target_pos)

    for message in missile.incoming_messages:
        sender_target_estimate = message.get('sender_target_estimate')
        if sender_target_estimate:
            all_target_estimates.append(sender_target_estimate)

    if all_target_estimates:
        missile.estimated_target_pos = _fuse_estimates(all_target_estimates)
    else:
        missile.estimated_target_pos = [missile.pos[0] + 1, missile.pos[1]] # Fallback forward guess


    # 2. Synchronize Movement (Adjust speed based on swarm's average distance to target)
    all_missile_distances_to_target = []
    
    own_dx_to_target = target.pos[0] - missile.float_pos[0]
    own_dy_to_target = target.pos[1] - missile.float_pos[1]
    own_dist_to_target = math.hypot(own_dx_to_target, own_dy_to_target)
    all_missile_distances_to_target.append(own_dist_to_target)

    for message in missile.incoming_messages:
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
        missile.speed = missile.base_speed
        print(f"  [Missile {missile.unique_id}] Overwhelm: Final Assault! Full speed.")
    elif own_dist_to_target < average_swarm_dist_to_target - LOITER_BUFFER:
        missile.speed = missile.base_speed * 0.2
        print(f"  [Missile {missile.unique_id}] Overwhelm: Loitering. Calculated speed: {missile.speed:.2f}")
    else:
        missile.speed = missile.base_speed

    missile.direction = missile._get_direction_vector(missile.estimated_target_pos)


def wave_attack(missile):
    """
    Guidance logic for the WAVE swarm mode ("Pulse Attack").
    Missiles self-organize into temporal waves to apply sustained pressure.
    """
    print(f"[Missile {missile.unique_id}] Running WAVE attack for Wave ID: {missile.wave_id}. Received {len(missile.incoming_messages)} messages.")

    target = next(agent for agent in missile.model.agents if isinstance(agent, TargetAgent))
    
    # 1. Fuse Target Estimates
    all_target_estimates = []
    if missile.estimated_target_pos:
        all_target_estimates.append(missile.estimated_target_pos)

    for message in missile.incoming_messages:
        sender_target_estimate = message.get('sender_target_estimate')
        if sender_target_estimate:
            all_target_estimates.append(sender_target_estimate)

    if all_target_estimates:
        missile.estimated_target_pos = _fuse_estimates(all_target_estimates)
    else:
        missile.estimated_target_pos = [missile.pos[0] + 1, missile.pos[1]] # Fallback forward guess


    # 2. Wave Synchronization (Adjust speed based on wave's average distance and staggering)
    relevant_messages = [
        msg for msg in missile.incoming_messages
        if msg.get('sender_wave_id') == missile.wave_id
    ]

    all_missile_distances_in_wave = []
    
    own_dx_to_target = target.pos[0] - missile.float_pos[0]
    own_dy_to_target = target.pos[1] - missile.float_pos[1]
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

    staggered_final_assault_distance = BASE_FINAL_ASSAULT_DISTANCE + (missile.wave_id * WAVE_STAGGER_INCREMENT)
    staggered_loiter_buffer_target_dist = average_wave_dist_to_target - BASE_LOITER_BUFFER


    if own_dist_to_target <= staggered_final_assault_distance:
        missile.speed = missile.base_speed
        print(f"  [Missile {missile.unique_id}] Wave {missile.wave_id}: Final Assault! Full speed. Target dist: {own_dist_to_target:.2f}")
    elif own_dist_to_target < staggered_loiter_buffer_target_dist:
        missile.speed = missile.base_speed * 0.2
        print(f"  [Missile {missile.unique_id}] Wave {missile.wave_id}: Loitering. Calculated speed: {missile.speed:.2f}")
    else:
        missile.speed = missile.base_speed

    missile.direction = missile._get_direction_vector(missile.estimated_target_pos)


def recce_logic(missile):
    """
    RECCE mode: scouts explore and relay estimates; attackers act only on confirmed estimates.
    """
    print(f"[Missile {missile.unique_id}] RECCE | Type: {missile.missile_type.name} | State: {missile.recce_state.name if missile.recce_state else 'N/A'} | Messages: {len(missile.incoming_messages)}")

    # TRU updates missile.estimated_target_pos *before* this method runs in model.step.
    # So, missile.estimated_target_pos at this point contains the latest TRU data.

    fresh_scout_estimates_from_comms = []
    # Collect NEW estimates from incoming scout messages only
    for message in missile.incoming_messages:
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
        missile.estimated_target_pos = _fuse_estimates(fresh_scout_estimates_from_comms)
        print(f"  [Missile {missile.unique_id}] Recce: Target estimate updated from FRESH scouts.")
    elif missile.estimated_target_pos is None:
        # If no fresh scouts AND missile currently has no estimate (e.g., very early in sim or TRU fails)
        missile.estimated_target_pos = [missile.float_pos[0] + 1, missile.float_pos[1]]
        print(f"  [Missile {missile.unique_id}] Recce: No estimates available. Guessing forward.")
    else:
        # Otherwise, retain the missile's current missile.estimated_target_pos (from TRU or previous scout fusion).
        # This handles the case where TRU is providing the best, but not necessarily "fresh scout" data.
        print(f"  [Missile {missile.unique_id}] Recce: Retaining current TRU/previous scout estimate.")


    # --- Role-Specific Behavior ---
    
    if missile.missile_type == MissileType.SCOUT:
        _recce_scout_behavior(missile)
    elif missile.missile_type == MissileType.ATTACKER:
        _recce_attacker_behavior(missile, fresh_scout_estimates_from_comms)

def _recce_scout_behavior(missile):
    """Scout behavior: move fast with lateral dispersion."""
    print(f"  [Missile {missile.unique_id}] Recce: SCOUT behavior.")
    missile.speed = missile.base_speed
    base_dir = missile._get_direction_vector(missile.estimated_target_pos)

    # Apply wider lateral offset
    lateral_offset = random.uniform(-0.3, 0.3)
    offset_x = -base_dir[1] * lateral_offset
    offset_y = base_dir[0] * lateral_offset

    new_dir_x = base_dir[0] + offset_x
    new_dir_y = base_dir[1] + offset_y
    mag = math.hypot(new_dir_x, new_dir_y)

    missile.direction = (new_dir_x / mag, new_dir_y / mag) if mag else (1, 0)

def _recce_attacker_behavior(missile, fresh_scout_estimates_from_comms):
    """Attacker behavior: loiter until confirmed, then engage and continue refining estimate."""
    print(f"  [Missile {missile.unique_id}] Recce: ATTACKER | State: {missile.recce_state.name}")

    if missile.recce_state == RecceState.INITIAL_LOITER:
        missile.speed = missile.min_speed
        
        # Transition to CONFIRMED_ATTACK if *any* fresh scout estimate was received this step
        if fresh_scout_estimates_from_comms:
            missile.recce_state = RecceState.CONFIRMED_ATTACK
            missile.speed = missile.base_speed # Accelerate to base speed for attack
            print(f"  [Missile {missile.unique_id}] Recce: ATTACKER transitioned to CONFIRMED_ATTACK!")

        missile.direction = missile._get_direction_vector(missile.estimated_target_pos)

    elif missile.recce_state == RecceState.CONFIRMED_ATTACK:
        missile.speed = missile.base_speed
        
        # In CONFIRMED_ATTACK, the missile's own sensor is the highest priority for terminal guidance.
        target = next(agent for agent in missile.model.agents if isinstance(agent, TargetAgent))
        detected, rel_pos = missile.sensor.run_detection(missile.float_pos, missile.direction, target.pos)

        if detected and rel_pos:
            # Use missile's own sensor for direct terminal guidance
            sensed_x = missile.float_pos[0] + rel_pos[0]
            sensed_y = missile.float_pos[1] + rel_pos[1]
            missile.estimated_target_pos = [sensed_x, sensed_y] # OVERRIDE with direct sensor data
            print(f"  [Missile {missile.unique_id}] Recce: Using OWN SENSOR estimate for terminal phase.")
        else:
            # If own sensor doesn't detect, rely on missile.estimated_target_pos (updated by TRU/scouts in recce_logic)
            print(f"  [Missile {missile.unique_id}] Recce: No local sensor. Relying on latest fused estimate.")
        
        missile.direction = missile._get_direction_vector(missile.estimated_target_pos)       

def split_axis_approach(missile):
    """
    Split-Axis: Missiles approach from different compass directions,
    then switch to direct attack when close to the target.
    """
    print(f"[Missile {missile.unique_id}] SPLIT_AXIS: Starting maneuver.")

    # Assign a fixed approach direction based on unique ID
    approach_direction = missile.unique_id % 4
    direction_names = ['EAST', 'WEST', 'NORTH', 'SOUTH']
    print(f"  [Missile {missile.unique_id}] Approach Direction: {direction_names[approach_direction]}")

    # Get current target position estimate (using a simplified fusion for this mode)
    current_target_estimate = list(missile.estimated_target_pos) if missile.estimated_target_pos else None
    all_estimates = []
    if current_target_estimate:
        all_estimates.append(current_target_estimate)
    for msg in missile.incoming_messages:
        est = msg.get('sender_target_estimate')
        if est:
            all_estimates.append(est)
    if all_estimates:
        missile.estimated_target_pos = _fuse_estimates(all_estimates)
    else:
        missile.estimated_target_pos = [missile.float_pos[0] + 1, missile.float_pos[1]] # Fallback if no estimates


    target = next(agent for agent in missile.model.agents if isinstance(agent, TargetAgent))
    
    # Distance to target (true target for decision, estimated for guidance until terminal phase)
    dx_to_true_target = target.pos[0] - missile.float_pos[0]
    dy_to_true_target = target.pos[1] - missile.float_pos[1]
    dist_to_true_target = math.hypot(dx_to_true_target, dy_to_true_target)
    TERMINAL_DISTANCE = 40

    # === Terminal Attack Phase ===
    if dist_to_true_target < TERMINAL_DISTANCE:
        print(f"  [Missile {missile.unique_id}] SPLIT_AXIS: Switching to direct attack (terminal phase).")
        # In terminal phase, prioritize direct targeting to actual target
        missile.direction = missile._get_direction_vector(target.pos) # Direct to true target for final attack
        missile.speed = missile.base_speed
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

    missile.direction = missile._get_direction_vector(aim_point)

    # === Speed Coordination (similar to Overwhelm/Wave for group cohesion) ===
    # Use relative distance to target for speed adjustments
    distances_to_target = [dist_to_true_target] # Start with own true distance
    for msg in missile.incoming_messages:
        sender_pos = msg.get("sender_pos")
        if sender_pos:
            # Calculate sender's distance to target (true target for this coordination)
            dx2 = target.pos[0] - sender_pos[0]
            dy2 = target.pos[1] - sender_pos[1]
            distances_to_target.append(math.hypot(dx2, dy2))

    avg_dist_swarm = sum(distances_to_target) / len(distances_to_target)
    cohesion_buffer = 10 # How much buffer around the average to allow

    if dist_to_true_target < avg_dist_swarm - cohesion_buffer:
        missile.speed = missile.min_speed # Slow down if too far ahead of average
        print(f"  [Missile {missile.unique_id}] SPLIT_AXIS: Loitering (ahead of group). Speed: {missile.speed:.2f}")
    elif dist_to_true_target > avg_dist_swarm + cohesion_buffer:
        missile.speed = missile.max_speed # Speed up if too far behind
        print(f"  [Missile {missile.unique_id}] SPLIT_AXIS: Accelerating (behind group). Speed: {missile.speed:.2f}")
    else:
        missile.speed = missile.base_speed # Maintain base speed
        print(f"  [Missile {missile.unique_id}] SPLIT_AXIS: Maintaining position. Speed: {missile.speed:.2f}")


def decoy_behaviour(missile):
    """
    DECOY behavior: Simulate attack profiles until a late phase, then diverge or self-destruct.
    Meant to cause defensive misallocation.
    """
    print(f"[Missile {missile.unique_id}] DECOY: Starting behavior.")

    target = next(agent for agent in missile.model.agents if isinstance(agent, TargetAgent))
    
    # Calculate distance to the actual target (to decide when to divert)
    dx_to_true_target = target.pos[0] - missile.float_pos[0]
    dy_to_true_target = target.pos[1] - missile.float_pos[1]
    dist_to_true_target = math.hypot(dx_to_true_target, dy_to_true_target)

    DECOY_DIVERGE_DISTANCE = 80 # Distance from target at which decoys start to diverge
    DECOY_SELF_DESTRUCT_DISTANCE = 10 # Distance at which decoy self-destructs if it somehow gets too close

    if dist_to_true_target <= DECOY_SELF_DESTRUCT_DISTANCE:
        missile.exploded = True
        missile.alive = False
        missile.model.agents.remove(missile)
        missile.model.grid.remove_agent(missile)
        print(f"  [Missile {missile.unique_id}] DECOY: Too close to target ({dist_to_true_target:.2f} units). Self-destructed!")
        return

    elif dist_to_true_target <= DECOY_DIVERGE_DISTANCE:
        print(f"  [Missile {missile.unique_id}] DECOY: Diverging at {dist_to_true_target:.2f} units.")
        missile.speed = missile.base_speed

        divert_x = missile.estimated_target_pos[0]
        divert_y = missile.estimated_target_pos[1] + random.uniform(50, 100) * random.choice([-1, 1])
        divert_x += random.uniform(20, 50) * random.choice([-1, 1])

        missile.direction = missile._get_direction_vector([divert_x, divert_y])
        print(f"  [Missile {missile.unique_id}] DECOY: New divert direction towards {divert_x:.2f},{divert_y:.2f}.")

    else:
        print(f"  [Missile {missile.unique_id}] DECOY: Simulating attack profile.")
        missile.speed = missile.base_speed
        missile.direction = missile._get_direction_vector(missile.estimated_target_pos)
