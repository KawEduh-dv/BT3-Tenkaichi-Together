"""Translate native campaign data into two human seats and paired enemy waves.

Planning is not native execution. Entity/form maps must come from the original
mission's events, and the native runtime must acknowledge every applied plan.
"""
from dataclasses import dataclass
from history_coop_rules import EnemyWaves, StoryEnemy, enemy_health
from history_native_reader import HistorySnapshot, NativeMember


@dataclass(frozen=True)
class EnemyIdentity:
    identity: str
    slots: tuple[int, ...]


@dataclass(frozen=True)
class HumanSeat:
    player: int
    native_member: NativeMember
    costume: int
    duplicated: bool


@dataclass(frozen=True)
class CampaignPlan:
    world: tuple
    humans: tuple[HumanSeat, HumanSeat]
    bench: tuple[NativeMember, ...]
    enemies: tuple[StoryEnemy, ...]
    enemy_maximum_hp: tuple[tuple[str, int], ...]

    def waves(self):
        return EnemyWaves(self.enemies)


def build(snapshot, identities, *, verified_costumes):
    """Preserve authored allies; duplicate only when no second ally exists.

    verified_costumes maps original character IDs to the structurally verified
    costume IDs in that user's disc. No external appearance asset is accepted.
    Enemy identity slots must cover the native enemy roster exactly once.
    """
    if not isinstance(snapshot, HistorySnapshot):
        raise TypeError('Expected an original native campaign snapshot')
    allies, opponents = (team.members for team in snapshot.teams)
    if not allies or not opponents:
        raise ValueError('Campaign plan requires native allies and opponents')
    if snapshot.teams[0].active_slot != 0 or snapshot.teams[1].active_slot != 0:
        raise ValueError('Prepare the campaign at its initial roster, before a native replacement')
    if any(member.hp <= 0 for member in allies+opponents):
        raise ValueError('A defeated original roster cannot become a fresh cooperative mission')
    def costume(member, *, alternate=False):
        choices = tuple(verified_costumes.get(member.character, ()))
        if member.costume not in choices:
            raise ValueError('Native costume is not verified against this disc')
        alternatives = [value for value in choices if type(value) is int and 0 <= value <= 3 and value != member.costume]
        return min(alternatives) if alternate and alternatives else member.costume
    first = allies[0]
    second = allies[1] if len(allies)>1 else first
    humans = (HumanSeat(1,first,costume(first),False),
              HumanSeat(2,second,costume(second,alternate=second.character==first.character),len(allies)==1))
    definitions = tuple(identities)
    if any(not isinstance(item,EnemyIdentity) for item in definitions):
        raise TypeError('Native enemy identities must be explicitly mapped')
    covered = [slot for item in definitions for slot in item.slots]
    if any(type(slot) is not int for slot in covered) or sorted(covered) != list(range(len(opponents))):
        raise ValueError('Enemy entity/form map must cover every native slot exactly once')
    if len({item.identity for item in definitions}) != len(definitions):
        raise ValueError('Different enemies cannot share a story identity')
    enemies, health = [], []
    for item in definitions:
        if not item.slots:
            raise ValueError('A native story enemy needs at least one roster slot')
        members = tuple(opponents[slot] for slot in item.slots)
        forms = tuple(dict.fromkeys(member.character for member in members))
        enemies.append(StoryEnemy(item.identity,forms))
        health.append((item.identity,enemy_health(max(member.maximum_hp for member in members))))
    return CampaignPlan(snapshot.world,humans,allies[2:],tuple(enemies),tuple(health))
