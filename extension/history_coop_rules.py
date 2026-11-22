"""Campaign rules, independent of UI, character names and emulator addresses.

The native campaign adapter must supply event identities, authored enemy
identities and valid form destinations. This module never invents story events,
spawns a body, edits a save, or reports that a native command completed.
"""
from dataclasses import dataclass
from enum import Enum


FORMATIONS=('duo','time_x_time')


def campaign_participation_mask(native_mask, actor_count, formation='duo'):
    """Keep the story pair by default, or activate the whole authored roster.

    Physical slots alternate ally/enemy. Duo mode retains P1, P2, and every
    native enemy present in this chapter; Time x Time retains the full roster.
    """
    if formation not in FORMATIONS:
        raise ValueError('Unknown Dragon History formation')
    if (type(actor_count) is not int or actor_count not in (4,6,8,10,12) or
            type(native_mask) is not int or not 0 < native_mask < (1 << actor_count)):
        raise ValueError('Invalid native Dragon History roster')
    if not native_mask & 1:
        raise ValueError('Dragon History P1 must be present in the captured roster')
    enemies=sum(1<<physical for physical in range(1,actor_count,2))
    enemy_members=native_mask & enemies
    if not enemy_members:
        raise ValueError('Dragon History roster has no active enemy')
    players=0b000101  # P2 uses the reserved second ally slot if the story has only one ally.
    if formation=='time_x_time':
        return native_mask | players
    return players | enemy_members


class EventKind(str, Enum):
    REPLACE = 'replace'
    TRANSFORM = 'transform'


@dataclass(frozen=True)
class R3Decision:
    event: int
    kind: EventKind
    players: tuple[int, ...]


class R3Coordinator:
    """One claimed event at a time; completion belongs to the native adapter.

    The first observed R3 edge owns a replacement, even while resources load.
    Same-frame ties go to P1. A transformation requests both players together
    and is emitted only after both destinations are ready. Held R3 cannot
    activate a subsequent event until released and pressed again.
    """
    def __init__(self):
        self.event = 0
        self.kind = None
        self.claim = 0
        self.previous = 0
        self.inflight = False
        self.completed = False

    def arm(self, event, kind):
        if type(event) is not int or event <= 0:
            raise ValueError('A campaign event needs a positive sequence number')
        kind = EventKind(kind)
        if event < self.event:
            raise ValueError('Stale campaign event')
        if event == self.event:
            if kind != self.kind:
                raise ValueError('An armed event cannot change its meaning')
            return
        if self.inflight:
            raise RuntimeError('A native command is still completing')
        self.event, self.kind = event, kind
        self.claim, self.inflight, self.completed = 0, False, False

    def update(self, p1_r3, p2_r3, ready_players=3):
        if type(p1_r3) is not bool or type(p2_r3) is not bool:
            raise TypeError('R3 state must be boolean for each player')
        if type(ready_players) is not int or not 0 <= ready_players <= 3:
            raise ValueError('Ready-player mask must be 0..3')
        held = int(p1_r3) | (int(p2_r3) << 1)
        pressed, self.previous = held & ~self.previous, held
        if self.kind is None or self.completed or self.inflight:
            return None
        if not self.claim and pressed:
            self.claim = (3 if self.kind == EventKind.TRANSFORM else
                          1 if pressed & 1 else 2)
        if not self.claim or ready_players & self.claim != self.claim:
            return None
        self.inflight = True
        return R3Decision(self.event, self.kind,
                          tuple(player for player in (1, 2) if self.claim & (1 << (player-1))))

    def acknowledge(self, event, *, success):
        if event != self.event or not self.inflight:
            raise ValueError('Native acknowledgement does not match the active command')
        if type(success) is not bool:
            raise TypeError('Native completion must be explicit')
        self.inflight = False
        self.completed = success


@dataclass(frozen=True)
class StoryEnemy:
    identity: str
    forms: tuple[int, ...]

    def __post_init__(self):
        if not isinstance(self.identity, str) or not self.identity:
            raise ValueError('An authored enemy needs a stable identity')
        if not self.forms or any(type(form) is not int or not 0 <= form <= 160 for form in self.forms):
            raise ValueError('Enemy forms must be original BT3 character IDs')
        if len(set(self.forms)) != len(self.forms):
            raise ValueError('Repeated form in one authored enemy')


class EnemyWaves:
    """Distinct enemies enter in pairs; form changes retain their identity.

    Identical character IDs may belong to different enemies, such as two
    Saibamen. Display-name grouping must never merge those entities. A native
    story gate must release each next pair; defeat alone does not skip dialogue.
    """
    def __init__(self, enemies):
        self.enemies = tuple(enemies)
        if any(not isinstance(enemy, StoryEnemy) for enemy in self.enemies):
            raise TypeError('Expected authored enemy records')
        identities = [enemy.identity for enemy in self.enemies]
        if len(identities) != len(set(identities)):
            raise ValueError('Each distinct enemy needs its own identity')
        self.cursor = 0
        self.active = {}
        self.defeated = set()

    def release_next(self, *, story_ready):
        if type(story_ready) is not bool:
            raise TypeError('The native story gate must be explicit')
        if self.active or not story_ready:
            return ()
        group = self.enemies[self.cursor:self.cursor+2]
        self.cursor += len(group)
        self.active = {enemy.identity: enemy.forms[0] for enemy in group}
        return group

    def transform(self, identity, form):
        if identity not in self.active:
            raise ValueError('Cannot transform an enemy outside the current wave')
        enemy = next(enemy for enemy in self.enemies if enemy.identity == identity)
        if type(form) is not int or form not in enemy.forms:
            raise ValueError('This form was not authorized for that story enemy')
        self.active[identity] = form

    def defeat(self, identity):
        if identity in self.defeated:
            return
        if identity not in self.active:
            raise ValueError('Cannot defeat an enemy that has not entered')
        del self.active[identity]
        self.defeated.add(identity)

    @property
    def complete(self):
        return self.cursor == len(self.enemies) and not self.active


def enemy_health(original):
    if type(original) is not int or not 0 < original <= 1_000_000:
        raise ValueError('Invalid native maximum HP')
    return min(1_000_000, max(60_000, (original*3+1)//2))
