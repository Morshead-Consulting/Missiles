import math
import random

class Sensor:
    """
    Simple directional sensor model for agents.

    - Detects a target within a specified angular field of view and range.
    - Returns boolean detection result and a noisy estimate of target position.
    - Uses forward direction of the sensing agent to determine if target is in view.
    """
    def __init__(self, range, field_of_view_deg, noise_std=0.0, is_active=False):
        """
        :param range: Max detection distance (units)
        :param field_of_view_deg: Angular width of the field of view (degrees)
        :param noise_std: Standard deviation of Gaussian noise on distance measurement
        :param is_active: Whether the sensor is active (affects observability, unused for now)
        """
        self.range = range
        self.field_of_view_deg = field_of_view_deg
        self.noise_std = noise_std
        self.is_active = is_active

    def run_detection(self, missile_pos, missile_direction, target_pos):
        """
        Determines whether the target is detected.

        :returns: Tuple (detected: bool, noisy_relative_position: tuple or None)
        """
        dx = target_pos[0] - missile_pos[0]
        dy = target_pos[1] - missile_pos[1]
        distance = math.hypot(dx, dy)

        if distance > self.range:
            return False, None  # Out of range

        # Normalize missile direction and vector to target
        dir_x, dir_y = missile_direction
        missile_angle = math.atan2(dir_y, dir_x)
        target_angle = math.atan2(dy, dx)

        # Compute angle difference and normalize to [-π, π]
        angle_diff = (target_angle - missile_angle + math.pi) % (2 * math.pi) - math.pi
        angle_diff_deg = math.degrees(abs(angle_diff))

        if angle_diff_deg > self.field_of_view_deg / 2:
            return False, None  # Outside field of view

        # Add noise to sensed position (optional)
        noisy_dx = dx + random.gauss(0, self.noise_std)
        noisy_dy = dy + random.gauss(0, self.noise_std)
        noisy_rel_pos = (noisy_dx, noisy_dy)

        return True, noisy_rel_pos
