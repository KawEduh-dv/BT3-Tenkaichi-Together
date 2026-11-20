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
    changes=[]
    for command in commands:
        if command['kind']==1 and command['opcode']==8 and len(command['args'])>=2:
            what=command['args'][0]['integer']
            operation=what&0xfff
            if 16<=operation<=20:
                changes.append(dict(side=(what>>15)&1,slot=operation-16,address=command['address']))
    return dict(label=label,commands=commands,replacements=changes)


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
