from enum import Enum


class SwarmMode(Enum):
    SIMPLE = 1
    OVERWHELM = 2
    WAVE = 3
    RECCE = 4
    SPLIT_AXIS = 5
    DECOY = 6


class MissileType(Enum):
    """Defines the role of a missile in certain swarm modes (e.g., Recce Mode)."""
    ATTACKER = 1
    SCOUT = 2


class RecceState(Enum):
    """Defines the state of an ATTACKER missile in Recce Mode."""
    INITIAL_LOITER = 1      # Attacker is waiting for scout confirmation
    CONFIRMED_ATTACK = 2    # Attacker has received confirmation and is proceeding to attack

