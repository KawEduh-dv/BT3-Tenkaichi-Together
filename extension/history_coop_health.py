"""Scale original campaign enemy HP once, before the prepared start is released."""
import struct

from history_coop_rules import enemy_health
import fresh_team_combat as core


def build_memory(ram, *, source='<campaign>', present_mask):
    if len(ram)!=0x8000000:
        raise ValueError('Campaign health requires 128 MiB captured RAM')
    u=lambda address:struct.unpack_from('<I',ram,address)[0]
    valid=lambda address,size:0x100000<=address<=len(ram)-size and address%4==0
    scene=u(0x2ff10c)
    if not valid(scene,0x20) or u(scene+0x18)!=8 or u(0x331dd0)!=1:
        raise ValueError('Only an original Dragon History battle may receive campaign HP')
    manager=u(core.ACTORS)
    count=u(core.MODE+4)
    if (not valid(manager,16) or u(manager)!=2 or count not in (4,6,8,10,12)
            or (u(core.MODE),u(core.MODE+8),u(core.MODE+12))!=(1,manager,count)):
        raise ValueError('Prepared campaign ownership changed')
    if type(present_mask) is not int or not 0<present_mask<(1<<count):
        raise ValueError('Campaign participation mask is invalid')
    blocks=[]
    seen=set()
    for physical in range(1,count,2):
        if not present_mask&(1<<physical):continue
        actor=u(core.POINTERS+physical*4)
        if not valid(actor,0x1600) or actor in seen or u(actor)!=physical or u(actor+8)!=1:
            raise ValueError('Campaign enemy identity changed')
        seen.add(actor)
        members=u(actor+0x998)
        if not 1<=members<=5 or u(actor+0x994)>=members:
            raise ValueError('Campaign enemy roster is invalid')
        for slot in range(members):
            row=actor+0x9a4+slot*0xa4
            if u(row+8)!=1:continue
            hp,maximum=u(row+64),u(row+68)
            if not 0<=hp<=maximum<=1_000_000 or not maximum:
                raise ValueError('Campaign enemy health is invalid')
            target=enemy_health(maximum)
            scaled=min(target,(hp*target+maximum-1)//maximum)
            old=ram[row+64:row+72]
            new=struct.pack('<2I',scaled,target)
            if old!=new:
                blocks.append(dict(address=row+64,expected_hex=old.hex(),data_hex=new.hex(),
                    purpose='Original campaign enemy HP at 150 percent, minimum 60000'))
    if not seen:raise ValueError('Campaign has no participating opponent')
    return dict(serial='SLUS-21678',crc='428113C2',source=str(source),blocks=blocks)
