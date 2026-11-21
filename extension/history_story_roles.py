"""Keep native story roles separate from simultaneously active player bodies.

Experimental USA-only adapter. An authored ChangeMember targeting a living
participant selects that body for subsequent script facade calls, without
reloading another copy of the character or changing either player's controls.
"""
import struct
from prototype import Assembler,ROOT,elf_reader
from native_map import A,elf_path
import fresh_team_combat as core

BASE,PHYSICAL,CHANGE0,CHANGE1,TRAMP0,TRAMP1,CONTROL,END=(
    0x06984000,0x06984000,0x06985000,0x06985800,0x06986000,0x06986100,0x06987000,0x06988000)
DEFER,DEFER_TRAMP=END,END+0x800
MAGIC=0x48535231
ENTRIES=(0x20ad50,)
FIND,PROMPT,R3,TRAMP_PROMPT=BASE+0x2400,BASE+0x2800,BASE+0x2c00,BASE+0x2200
STOP,TRAMP_STOP=BASE+0x1800,BASE+0x2300
EVENT_MAP=CONTROL+32
SCRIPTED_SKILL_MAP=CONTROL+0x100
REGS=tuple(range(8,16))


def save(a):
    a.addiu(29,29,-0x40)
    for i,r in enumerate(REGS):a.i(63,r,29,i*8)


def restore(a):
    for i,r in enumerate(REGS):a.i(55,r,29,i*8)
    a.addiu(29,29,0x40)


def scope(a,fail):
    a.li(8,CONTROL);a.lw(9,8);a.li(10,MAGIC);a.branch(5,9,10,fail)
    a.lw(9,8,4);a.lw(10,28,-22364);a.branch(5,9,10,fail)
    a.li(9,0x331dd0);a.lw(9,9);a.addiu(10,0,1);a.branch(5,9,10,fail)
    a.li(9,core.MODE);a.lw(10,9);a.branch(4,10,0,fail)
    a.lw(10,9,8);a.lw(11,8,4);a.branch(5,10,11,fail)
    a.lw(10,9,4);a.lw(11,9,12);a.branch(5,10,11,fail)
    a.i(11,10,4,2);a.branch(4,10,0,fail)


def physical_code(original):
    a=Assembler(PHYSICAL);save(a);scope(a,'native')
    a.lw(9,8,28);a.branch(5,9,0,'native')
    # General battle/AI/camera getters keep their physical indexes. Only the
    # original script facade sees the current story role (side 0 or side 1).
    a.li(10,0x20a000);a.r(0x2b,11,31,10);a.branch(5,11,0,'native')
    a.li(10,0x20b840);a.r(0x2b,11,31,10);a.branch(4,11,0,'native')
    a.r(0,9,0,4,2);a.r(0x21,8,8,9);a.lw(2,8,8)
    restore(a);a.jr()
    a.label('native');restore(a)
    for word in struct.unpack('<2I',original):a.emit(word)
    a.jump(core.PHYSICAL+8)
    return a.finish()


def change_code(address,trampoline):
    import team_participation as part
    a=Assembler(address);save(a);scope(a,'native')
    a.i(11,9,5,5);a.branch(4,9,0,'native')
    # A story finisher pairs ChangeMember with an authored skill action. Keep
    # that native member transition so the game applies the cinematic move's
    # scripted damage and can latch the chapter result. Ordinary duplicate
    # swaps still resolve to the living co-op body below.
    a.li(9,0x333f10);a.lw(9,9);a.branch(4,9,0,'lookup')
    a.lw(10,9,8);a.addiu(10,10,-10000);a.i(11,11,10,52);a.branch(4,11,0,'lookup')
    a.li(12,SCRIPTED_SKILL_MAP);a.r(0,13,0,10,2);a.r(0x21,12,12,13);a.lw(13,12)
    a.branch(5,13,0,'native')
    a.label('lookup')
    a.li(9,core.MODE);a.lw(10,9,4);a.move(11,4)
    a.li(12,core.POINTERS);a.li(13,part.PRESENT);a.lw(14,13,4);a.lw(13,13)
    a.r(0x27,14,14,0);a.r(0x24,13,13,14)
    a.label('scan');a.r(0x2b,9,11,10);a.branch(4,9,0,'native')
    a.addiu(14,0,1);a.r(4,14,11,14);a.r(0x24,14,14,13);a.branch(4,14,0,'next')
    a.r(0,14,0,11,2);a.r(0x21,14,12,14);a.lw(14,14)
    a.lw(15,14,0x994);a.branch(5,15,5,'next')
    # Current native roster row is present and alive, never revive a partner.
    a.li(9,0xa4);a.r(0x19,0,15,9);a.r(0x12,15,0,0)
    a.r(0x21,15,14,15);a.lw(15,15,0x9e4);a.branch(6,15,0,'next')
    a.r(0,9,0,4,2);a.r(0x21,8,8,9);a.sw(14,8,8)
    a.li(8,CONTROL);a.lw(9,8,16);a.addiu(9,9,1);a.sw(9,8,16)
    restore(a);a.move(2,0);a.jr()
    a.label('next');a.addiu(11,11,2);a.jump('scan')
    a.label('native');restore(a);a.jump(trampoline)
    result=a.finish();assert len(result)<0x800;return result


def stop_code(count,present_mask):
    a=Assembler(STOP);save(a);a.addiu(29,29,-0x20)
    a.i(63,31,29,0);a.i(63,4,29,8)
    scope(a,'native');a.branch(5,4,0,'native')
    # EndEvent stops native sides 0/1. With two allied bodies, stop the
    # scripted motion on each living ally before giving controls back.
    a.addiu(9,0,1);a.sw(9,8,28)
    for physical in range(0,count,2):
        if not present_mask&(1<<physical):continue
        a.li(8,core.POINTERS+physical*4);a.lw(8,8);a.lw(9,8,0x994)
        a.li(10,0xa4);a.r(0x19,0,9,10);a.r(0x12,9,0,0)
        a.r(0x21,9,9,8);a.lw(9,9,0x9e4);a.branch(6,9,0,f'next_{physical}')
        a.addiu(4,0,physical);a.call(TRAMP_STOP)
        a.label(f'next_{physical}')
    a.li(8,CONTROL);a.sw(0,8,28)
    a.i(55,31,29,0);a.i(55,4,29,8);a.addiu(29,29,0x20);restore(a);a.jr()
    a.label('native');a.i(55,31,29,0);a.i(55,4,29,8)
    a.addiu(29,29,0x20);restore(a);a.jump(TRAMP_STOP)
    result=a.finish();assert len(result)<0x800;return result


def redundant_event_code():
    import team_participation as part
    a=Assembler(FIND);a.move(4,0);scope(a,'no')
    a.li(9,0x333f10);a.lw(9,9)
    a.li(10,0x334464);a.r(0x2b,11,9,10);a.branch(5,11,0,'no')
    a.li(10,0x334784);a.r(0x2b,11,9,10);a.branch(4,11,0,'no')
    a.lw(10,9);a.addiu(11,0,2);a.branch(5,10,11,'no')
    a.lw(10,9,8);a.addiu(10,10,-10000);a.i(11,11,10,52);a.branch(4,11,0,'no')
    a.li(11,0x333d0c);a.r(0x21,11,11,10);a.lw(12,9,12);a.branch(5,11,12,'no')
    a.li(11,EVENT_MAP);a.r(0,10,0,10,2);a.r(0x21,11,11,10);a.lw(11,11)
    a.addiu(12,0,-1);a.branch(4,11,12,'no')
    a.i(12,5,11,7);a.r(2,4,0,11,3)
    a.li(12,core.POINTERS);a.li(13,part.PRESENT);a.lw(14,13,4);a.lw(13,13)
    a.r(0x27,14,14,0);a.r(0x24,13,13,14)
    a.li(9,core.MODE);a.lw(10,9,4);a.move(11,4)
    a.label('scan');a.r(0x2b,9,11,10);a.branch(4,9,0,'no')
    a.addiu(14,0,1);a.r(4,14,11,14);a.r(0x24,14,14,13);a.branch(4,14,0,'next')
    a.r(0,14,0,11,2);a.r(0x21,14,12,14);a.lw(14,14)
    a.lw(15,14,0x994);a.branch(5,15,5,'next')
    a.li(9,0xa4);a.r(0x19,0,15,9);a.r(0x12,15,0,0)
    a.r(0x21,15,14,15);a.lw(15,15,0x9e4);a.branch(6,15,0,'next')
    a.move(2,14);a.jr()
    a.label('next');a.addiu(11,11,2);a.jump('scan')
    a.label('no');a.move(2,0);a.jr()
    result=a.finish();assert len(result)<PROMPT-FIND;return result


def prompt_code(address,*,input_query):
    a=Assembler(address);save(a);a.addiu(29,29,-0x20)
    for register,offset in ((31,0),(4,8),(5,16)):a.i(63,register,29,offset)
    a.call(FIND);a.move(3,2)
    for register,offset in ((31,0),(4,8),(5,16)):a.i(55,register,29,offset)
    a.addiu(29,29,0x20);restore(a)
    a.branch(4,3,0,'native')
    if input_query:
        # The native event still waits for its own ready/combat conditions.
        # Its redundant body-change trigger then runs without an R3 prompt.
        a.addiu(2,0,1);a.jr()
    else:a.jump(0x22d9b0)
    a.label('native');a.jump(0x129728 if input_query else TRAMP_PROMPT)
    return a.finish()


def build_memory(ram, *, source='<story-role-probe>'):
    if A(0x20ad50)!=0x20ad50:raise ValueError('Story roles require the reviewed USA executable')
    u=lambda address:struct.unpack_from('<I',ram,address)[0]
    if len(ram)!=0x8000000 or u(0x331dd0)!=1 or u(core.MODE)!=1:
        raise ValueError('Story roles require a prepared native campaign')
    if any(ram[BASE:END]):raise ValueError('Story role reservation is occupied')
    expected=core.getter_code(core.PHYSICAL,A(0x1dc178))
    if ram[core.PHYSICAL:core.PHYSICAL+len(expected)]!=expected:
        raise ValueError('Prepared physical getter changed')
    read=elf_reader(elf_path(ROOT))[2]
    pieces=[(PHYSICAL,physical_code(expected[:8])),
            (core.PHYSICAL,struct.pack('<2I',(2<<26)|(PHYSICAL>>2),0)),
            (CONTROL,struct.pack('<5I',MAGIC,u(core.ACTORS),u(core.POINTERS),u(core.POINTERS+4),0))]
    from history_script_metadata import loaded_events
    events=loaded_events(ram)
    event_map=[0xffffffff]*52
    scripted_skill_map=[0]*52
    for label,event in events.items():
        if len(event['replacements'])==1:
            change=event['replacements'][0]
            event_map[label-10000]=change['side']*8+change['slot']
            if any(command['kind']==1 and command['opcode']==1603 for command in event['commands']):
                scripted_skill_map[label-10000]=1
    original=read(0x259d90,8)
    if ram[0x259d90:0x259d98]!=original or u(0x259cd0)!=((3<<26)|(0x129728>>2)):
        raise ValueError('Original story prompt and R3 call changed')
    pieces.extend(((EVENT_MAP,struct.pack('<52I',*event_map)),
        (SCRIPTED_SKILL_MAP,struct.pack('<52I',*scripted_skill_map)),(FIND,redundant_event_code()),
        (PROMPT,prompt_code(PROMPT,input_query=False)),(R3,prompt_code(R3,input_query=True)),
        (TRAMP_PROMPT,original+struct.pack('<2I',(2<<26)|(0x259d98>>2),0)),
        (0x259d90,struct.pack('<2I',(2<<26)|(PROMPT>>2),0)),
        (0x259cd0,struct.pack('<I',(3<<26)|(R3>>2)))))
    import team_participation as part
    original=read(0x20a2e0,8)
    if ram[0x20a2e0:0x20a2e8]!=original:raise ValueError('Original StopMotion prologue changed')
    pieces.extend(((STOP,stop_code(u(core.MODE+4),u(part.PRESENT))),
        (TRAMP_STOP,original+struct.pack('<2I',(2<<26)|(0x20a2e8>>2),0)),
        (0x20a2e0,struct.pack('<2I',(2<<26)|(STOP>>2),0))))
    deferred=defer_memory(ram,validate=False)
    for entry,wrapper,trampoline in zip(ENTRIES,(CHANGE0,CHANGE1),(TRAMP0,TRAMP1)):
        original=read(entry,8)
        if ram[entry:entry+8]==original:
            pass
        elif entry==ENTRIES[0] and ram[entry:entry+8]==deferred['entry'] and \
                ram[DEFER:DEFER+len(deferred['code'])]==deferred['code'] and \
                ram[DEFER_TRAMP:DEFER_TRAMP+len(deferred['trampoline'])]==deferred['trampoline']:
            # The temporary history-only hold prevents an authored ChangeMember
            # from replacing Goku while the second body is still being loaded.
            # Replace it atomically with the full role adapter before releasing
            # the first playable frame.
            pieces.extend(((DEFER,b'\0'*len(deferred['code'])),
                           (DEFER_TRAMP,b'\0'*len(deferred['trampoline']))))
        else:raise ValueError('Native ChangeMember prologue changed')
        pieces.extend(((trampoline,original+struct.pack('<2I',(2<<26)|((entry+8)>>2),0)),
                       (wrapper,change_code(wrapper,trampoline)),
                       (entry,struct.pack('<2I',(2<<26)|(wrapper>>2),0))))
    return dict(serial='SLUS-21678',crc='428113C2',source=str(source),blocks=[
        dict(address=address,expected_hex=ram[address:address+len(data)].hex(),data_hex=data.hex())
        for address,data in pieces])


def defer_code(address=DEFER):
    """Hold authored member swaps only while a Dragon History co-op is being prepared.

    The complete story role adapter replaces this hook before the loading gate
    releases. Returning the native 'already active' result leaves the authored
    event pending for that adapter and prevents the leader model from changing
    while resources and the second body are created.
    """
    import native_preparation as prep
    a=Assembler(address);a.li(8,prep.CONTROL);a.lw(9,8);a.li(10,prep.MAGIC)
    a.branch(5,9,10,'native')
    a.li(8,prep.ACCEPTED_MODE);a.lw(8,8);a.addiu(9,0,1);a.branch(5,8,9,'native')
    a.li(8,A(0x331DD0));a.lw(8,8);a.addiu(9,0,1);a.branch(5,8,9,'native')
    a.move(2,0);a.jr()
    a.label('native');a.jump(DEFER_TRAMP)
    return a.finish()


def defer_memory(ram, *, source='<history-coop-prepare>', validate=True):
    """Patch ChangeMember before resource loading, confined to the armed history mode."""
    import native_preparation as prep
    entry=ENTRIES[0]
    original=elf_reader(elf_path(ROOT))[2](entry,8)
    code=defer_code()
    trampoline=original+struct.pack('<2I',(2<<26)|((entry+8)>>2),0)
    if len(ram)!=0x8000000:raise ValueError('Story swap hold needs a full EE RAM snapshot')
    if validate:
        if ram[entry:entry+8]!=original:raise ValueError('Native ChangeMember prologue changed before history preparation')
        if any(ram[DEFER:DEFER+0x1000]):raise ValueError('Temporary story swap reservation is occupied')
        if ram[prep.CONTROL:prep.CONTROL+4]!=struct.pack('<I',prep.MAGIC):
            raise ValueError('The Dragon History preparation gate is not armed')
        if struct.unpack_from('<I',ram,prep.ACCEPTED_MODE)[0]!=1 or struct.unpack_from('<I',ram,A(0x331DD0))[0]!=1:
            raise ValueError('The native Dragon History co-op mode is not selected')
    blocks=[(DEFER,code),(DEFER_TRAMP,trampoline),(entry,struct.pack('<2I',(2<<26)|(DEFER>>2),0))]
    return dict(serial='SLUS-21678',crc='428113C2',source=str(source),
        blocks=[dict(address=address,expected_hex=ram[address:address+len(data)].hex(),data_hex=data.hex())
                for address,data in blocks],entry=blocks[2][1],code=code,trampoline=trampoline)
