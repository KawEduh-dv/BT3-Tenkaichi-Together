"""Read GSC actions and constant references without modifying game bytecode.

Format reference: z3xox/Tenkaichi3Decomp/docs/systems/script.md.
Only numeric metadata is returned; no dialogue or game assets are exported.
"""
import struct


def chunk(ram,address,tag):
    if type(address) is not int or address<0 or address+16>len(ram):
        raise ValueError('GSC chunk header is outside captured memory')
    actual,offset,size,label=struct.unpack_from('<4s3I',ram,address)
    if actual!=tag or offset<16 or offset%4 or size%4 or address+offset+size>len(ram):
        raise ValueError('Invalid GSC chunk')
    return address+offset,address+offset+size,label


def action(ram,address,pool_address):
    start,end,label=chunk(ram,address,b'GSAC')
    pool,pool_end,_=chunk(ram,pool_address,b'GSDT')
    u=lambda at:struct.unpack_from('<I',ram,at)[0]
    def operands(position,count):
        if position+count*4>end:raise ValueError('Truncated GSC argument list')
        result=[]
        for at in range(position,position+count*4,4):
            encoded=u(at)
            if encoded&15!=10:raise ValueError('Invalid GSC constant reference')
            index=encoded>>8
            target=pool+index*4
            if target+4>pool_end:raise ValueError('GSC constant index outside pool')
            result.append(dict(index=index,integer=struct.unpack_from('<i',ram,target)[0],
                               bits=u(target),kind=(encoded>>4)&15))
        return result
    commands=[]
    position=start
    while position<end:
        header=u(position);kind=header&15
        if not header:break
        if kind not in (1,2,3):raise ValueError('Unsupported GSC instruction type')
        count=(header>>8)&255 if kind==1 else 0
        args=operands(position+4,count)
        opcode=header>>16
        if kind in (2,3) and opcode&0x8000:opcode-=0x10000
        command=dict(address=position,kind=kind,opcode=opcode,args=args,options=[])
        position+=4+count*4
        while position<end and u(position)&15==8:
            option=u(position);count=option>>16
            values=operands(position+4,count)
            command['options'].append(dict(flag=chr((option>>8)&255),args=values))
            position+=4+count*4
        commands.append(command)
    return dict(label=label,commands=commands,replacements=change_members(commands))


def change_members(commands):
    """Decode authored ChangeMember commands from an action or flattened call graph."""
    changes=[]
    for command in commands:
        if command['kind']==1 and command['opcode']==8 and len(command['args'])>=2:
            what=command['args'][0]['integer']
            operation=what&0xfff
            if 16<=operation<=20:
                changes.append(dict(side=(what>>15)&1,slot=operation-16,address=command['address']))
    return changes


def story_role_targets(commands):
    """Return story actors explicitly targeted by a following scripted action.

    Battle command 8 encodes ChangeMember (16..20), transformations (21/22),
    fusion (23), and forced actions (25..29). Status commands 13/14 may set a
    named member's HP directly, including scripted KOs. Track the most recent
    authored member for each side so an action's identity is independent of the
    controller that happened to trigger its event.

    The command meanings are from the matching retail script handler table;
    unknown or underspecified actions deliberately produce no inferred role.
    Some finishers do not ChangeMember in their own action. For these, require
    the same explicit member in both a scene command (901) and a cue (1603).
    """
    active = {}
    targets = []
    scene_members = set()
    cue_members = set()

    def integer(argument):
        if not isinstance(argument, dict) or type(argument.get('integer')) is not int:
            raise ValueError('Story role command has no integer operand')
        return argument['integer']

    def member(argument):
        value = integer(argument) & 0xffffffff
        side, slot = (value >> 15) & 1, value & 0x7fff
        return (side, slot) if slot < 5 else None

    for command in commands:
        if not isinstance(command, dict) or command.get('kind') != 1:
            continue
        opcode = command.get('opcode')
        args = command.get('args', ())
        if opcode in (901, 1603) and args:
            try:
                selected = member(args[0])
            except (ValueError, TypeError):
                selected = None
            if selected is not None:
                (scene_members if opcode == 901 else cue_members).add(selected)
        if opcode == 8 and len(args) >= 2:
            try:
                what = integer(args[0]) & 0xffffffff
                action = what & 0xfff
                side = (what >> 15) & 1
            except (ValueError, TypeError):
                continue
            if 16 <= action <= 20:
                active[side] = action - 16
            elif action in (21, 22, 23, 25, 26, 27, 28, 29):
                if side in active:
                    targets.append(dict(side=side, slot=active[side], kind='technique'))
                elif action in (25, 26, 27, 28, 29):
                    candidates={slot for found_side,slot in cue_members if found_side == side}
                    if len(candidates)==1:
                        slot=next(iter(candidates))
                        if (side,slot) in scene_members:
                            targets.append(dict(side=side,slot=slot,kind='technique'))
        elif opcode in (13, 14):
            side = opcode - 13
            options = command.get('options', ())
            named_member = None
            hp_values = []
            try:
                for option in options:
                    if not isinstance(option, dict):
                        continue
                    letter = option.get('flag')
                    values = option.get('args', ())
                    if letter == 'C' and values:
                        named_member = integer(values[0])
                    elif letter == 'h' and values:
                        hp_values.append(integer(values[0]))
            except (ValueError, TypeError):
                continue
            # In command 13/14, -h <= 0 lowers HP to zero and fires the native
            # KO triggers. Positive -h heals; -H adds HP and is not a death.
            # Multiple writes in a single status command may include setup and
            # cleanup values. Treat them as ambiguous instead of calling a KO
            # scripted based on one intermediate nonpositive value.
            if len(hp_values)==1 and hp_values[0] <= 0:
                slot = named_member if named_member is not None else active.get(side)
                if type(slot) is int and 0 <= slot < 5:
                    targets.append(dict(side=side, slot=slot, kind='scripted_ko'))
    return tuple(targets)


def replacement_prompt(flags):
    """BtlScript event kind 1 means ChangeMember; kind 2 means UseSkill."""
    return type(flags) is int and flags&1==1 and flags&0xc0==0x40


def available_replacement(event,active_slots):
    """Do not offer a body that is already participating on the same side."""
    changes=event['replacements']
    return any(change['slot'] not in active_slots.get(change['side'],()) for change in changes)


def loaded_events(ram, *, include_setup=False):
    """Find one structurally complete loaded action container and its pool."""
    found=[];cursor=0
    while True:
        cursor=ram.find(b'GSCD',cursor)
        if cursor<0:break
        address=cursor;cursor+=4
        try:
            position,end,_=chunk(ram,address,b'GSCD')
            pool=end+16
            chunk(ram,pool,b'GSDT')
            events={}
            while position<end:
                _,action_end,label=chunk(ram,position,b'GSAC')
                event=action(ram,position,pool)
                if 10000<=label<10052 or include_setup:
                    if label in events:raise ValueError('Duplicate event action')
                    events[label]=event
                position=action_end+16
            if position!=end or not events:continue
            found.append(events)
        except (ValueError,struct.error):continue
    if len(found)!=1:raise ValueError('Expected one complete loaded story action container')
    return found[0]


def flatten_action(actions,label,trail=()):
    label&=0xffffffff
    if label in trail or len(trail)>=32:raise ValueError('Recursive GSC action graph')
    if label not in actions:raise ValueError('GSC called action is missing')
    result=[]
    for command in actions[label]['commands']:
        if command['kind'] in (2,3):
            result.extend(flatten_action(actions,command['opcode'],trail+(label,)))
        else:result.append(command)
    return result
