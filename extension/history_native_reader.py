"""Read original USA Dragon History rosters without changing the running game.

This is the data boundary for the cooperative campaign adapter. It deliberately
does not infer story entities from character names: only an authored event map
can say whether two roster rows are forms of one enemy or distinct opponents.
"""
from dataclasses import dataclass
import struct


MANAGER = 0x2FEB14
SCENE_MANAGER = 0x2FF10C
SETUP = 0x331DC8
MODEL_TABLE = 0x31C640
PADS = 0x333800
PENDING_EVENT = 0x333F10
NATIVE_RAM = 0x2000000
ACTOR_SIZE = 0x1600
ROW_SIZE = 0xA4


class HistoryReadError(ValueError):
    pass


def pointer(address, size):
    if type(address) is not int or address & 3 or not 0x100000 <= address <= NATIVE_RAM-size:
        raise HistoryReadError('Original campaign pointer is outside aligned retail RAM')
    return address


@dataclass(frozen=True)
class NativeMember:
    side: int
    slot: int
    character: int
    costume: int
    hp: int
    maximum_hp: int
    native_row: bytes


@dataclass(frozen=True)
class NativeTeam:
    actor: int
    model: int
    active_slot: int
    members: tuple[NativeMember, ...]


@dataclass(frozen=True)
class NativeStoryEvent:
    address: int
    record_type: int
    condition: int
    label: int
    payload: int
    payload_flags: int


@dataclass(frozen=True)
class HistorySnapshot:
    manager: int
    scene_manager: int
    teams: tuple[NativeTeam, NativeTeam]
    r3_held: tuple[bool, bool]
    pending_event: NativeStoryEvent | None = None

    @property
    def world(self):
        return self.manager, tuple(team.actor for team in self.teams)


def capture(client):
    """Read one bounded snapshot; reject a scene/world changed during the read.

    The caller must first bind its PINE client to SLUS-21678 / 428113C2.
    Only native two-actor rosters are accepted here. Prepared actors live in
    their own tables and must be read by the cooperative runtime instead.
    """
    client.require_game(serial='SLUS-21678',crc='428113C2')
    u = client.read_u32
    scene = pointer(u(SCENE_MANAGER), 0x20)
    manager = pointer(u(MANAGER), 0x280)
    if u(scene+0x18) != 8 or u(SETUP+8) != 1:
        raise HistoryReadError('No original Dragon History battle is active')
    if u(manager) != 2:
        raise HistoryReadError('Original campaign capture requires two native actors')
    array = pointer(u(manager+4), 2*ACTOR_SIZE)
    teams = []
    for side in range(2):
        actor = array + side*ACTOR_SIZE
        if u(actor) != side or u(actor+8) != side:
            raise HistoryReadError('Native actor side identity changed')
        active, count = u(actor+0x994), u(actor+0x998)
        if not 1 <= count <= 5 or not 0 <= active < count:
            raise HistoryReadError('Invalid original campaign roster')
        members = []
        for slot in range(count):
            raw = bytes(client.read(actor+0x9A4+slot*ROW_SIZE, ROW_SIZE))
            if len(raw) != ROW_SIZE:
                raise HistoryReadError('Truncated native campaign row')
            character, costume, present = struct.unpack_from('<3I', raw)
            hp, maximum = struct.unpack_from('<2I', raw, 64)
            if character > 160 or costume > 3 or present != 1 or not 0 <= hp <= maximum <= 1_000_000:
                raise HistoryReadError('Campaign row is incomplete or changed during capture')
            if maximum == 0:
                raise HistoryReadError('Campaign row has no maximum HP')
            members.append(NativeMember(side,slot,character,costume,hp,maximum,raw))
        mid = u(actor+12)
        if mid != side:
            raise HistoryReadError('Native leader no longer uses its original model slot')
        model = pointer(u(MODEL_TABLE+4*mid), 0x1670)
        if u(model+4) != 1 or u(model+16) != mid or u(model+12) != members[active].character:
            raise HistoryReadError('An original story replacement is still loading')
        teams.append(NativeTeam(actor,model,active,tuple(members)))
    r3 = tuple(bool(u(PADS+port*0x1C0+0x148)&4) for port in range(2))
    event_address = u(PENDING_EVENT)
    event = None
    if event_address:
        pointer(event_address,16)
        raw = bytes(client.read(event_address,16))
        if len(raw)!=16:
            raise HistoryReadError('Truncated original story event')
        record_type,condition,label,payload = struct.unpack('<4I',raw)
        if record_type not in (1,2) or not 0x100000 <= payload < NATIVE_RAM:
            raise HistoryReadError('Invalid original story event descriptor')
        flags = bytes(client.read(payload,1))
        if len(flags)!=1:
            raise HistoryReadError('Truncated original story event payload')
        event = NativeStoryEvent(event_address,record_type,condition,label,payload,flags[0])
    if (u(MANAGER),u(SCENE_MANAGER),u(scene+0x18),u(SETUP+8),u(manager+4)) != (manager,scene,8,1,array):
        raise HistoryReadError('Campaign world changed during the non-atomic PINE read')
    for team in teams:
        if u(team.actor+0x994) != team.active_slot or u(team.actor+0x998) != len(team.members):
            raise HistoryReadError('Campaign roster changed during capture')
    if u(PENDING_EVENT)!=event_address:
        raise HistoryReadError('The original story event changed during capture')
    if event is not None and bytes(client.read(event.address,16))!=raw:
        raise HistoryReadError('The original event descriptor changed during capture')
    return HistorySnapshot(manager,scene,tuple(teams),r3,event)
