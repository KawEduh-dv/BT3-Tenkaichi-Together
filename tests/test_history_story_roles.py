"""Execute the emitted role checks over sparse synthetic EE memory."""
import struct
import unittest
import fresh_team_combat as core
import history_story_roles as roles
import team_participation as part


class EE:
    def __init__(self,code,memory):
        self.code={address+i:word for address,data in code for i,word in
                   ((n,struct.unpack_from('<I',data,n)[0]) for n in range(0,len(data),4))}
        self.mem=dict(memory);self.r=[0]*32;self.lo=0
        self.r[29]=0x7fef000;self.r[28]=0x304270;self.r[31]=0x100000
        for i in range(8,16):self.r[i]=0x1000+i

    def run(self,pc,a0=0,a1=0,ra=None):
        self.r[4:6]=a0,a1
        if ra is not None:self.r[31]=ra
        for _ in range(2000):
            if pc not in self.code:return pc
            word=self.code[pc];op=word>>26;rs=(word>>21)&31;rt=(word>>16)&31
            rd=(word>>11)&31;imm=word&65535;signed=imm if imm<32768 else imm-65536
            following=pc+4
            if op in (2,3,4,5,6) or (op==0 and word&63==8):
                if self.code.get(pc+4)!=0:raise AssertionError('Unmodelled branch delay instruction')
                following=pc+8
            if op==15:self.r[rt]=imm<<16
            elif op==13:self.r[rt]=self.r[rs]|imm
            elif op==14:self.r[rt]=self.r[rs]^imm
            elif op==12:self.r[rt]=self.r[rs]&imm
            elif op==9:self.r[rt]=(self.r[rs]+signed)&0xffffffff
            elif op==11:self.r[rt]=int(self.r[rs]<(signed&0xffffffff))
            elif op in (35,55):self.r[rt]=self.mem.get((self.r[rs]+signed)&0xffffffff,0)
            elif op in (43,63):self.mem[(self.r[rs]+signed)&0xffffffff]=self.r[rt]
            elif op in (2,3):
                if op==3:self.r[31]=pc+8
                following=(pc&0xf0000000)|((word&0x3ffffff)<<2)
            elif op in (4,5,6):
                take=(self.r[rs]==self.r[rt]) if op==4 else (self.r[rs]!=self.r[rt]) if op==5 else (self.r[rs]==0 or self.r[rs]&0x80000000)
                if take:following=pc+4+signed*4
            elif op==0:
                fn=word&63;shift=(word>>6)&31
                if fn==0:self.r[rd]=(self.r[rt]<<shift)&0xffffffff
                elif fn==2:self.r[rd]=self.r[rt]>>shift
                elif fn==4:self.r[rd]=(self.r[rt]<<(self.r[rs]&31))&0xffffffff
                elif fn==8:following=self.r[rs]
                elif fn==0x19:self.lo=(self.r[rs]*self.r[rt])&0xffffffff
                elif fn==0x12:self.r[rd]=self.lo
                elif fn in (0x21,0x2d):self.r[rd]=(self.r[rs]+self.r[rt])&0xffffffff
                elif fn==0x24:self.r[rd]=self.r[rs]&self.r[rt]
                elif fn==0x25:self.r[rd]=self.r[rs]|self.r[rt]
                elif fn==0x27:self.r[rd]=~(self.r[rs]|self.r[rt])&0xffffffff
                elif fn==0x2b:self.r[rd]=int(self.r[rs]<self.r[rt])
                else:raise AssertionError(hex(word))
            else:raise AssertionError(hex(word))
            self.r[0]=0;pc=following
        raise AssertionError('Role hook failed to terminate')


class StoryRoleTests(unittest.TestCase):
    def test_coop_story_adapter_accepts_chapter_rosters_with_extra_enemies(self):
        self.assertTrue(roles.supports_coop_roster(4,0b000111))
        self.assertTrue(roles.supports_coop_roster(6,0b111111))
        self.assertTrue(roles.supports_coop_roster(10,0b1111111111))
        self.assertFalse(roles.supports_coop_roster(4,0b000011)) # P2 body absent
        self.assertFalse(roles.supports_coop_roster(4,0b000101)) # no opponent
        self.assertFalse(roles.supports_coop_roster(3,0b000101)) # invalid capacity
        self.assertFalse(roles.supports_coop_roster(4,True))

    def setUp(self):
        self.manager=0x180000;self.goku=0x190000;self.piccolo=0x1a0000
        self.memory={roles.CONTROL:roles.MAGIC,roles.CONTROL+4:self.manager,
            roles.CONTROL+8:self.goku,roles.CONTROL+12:0x1b0000,
            0x304270-22364:self.manager,0x331dd0:1,
            core.MODE:1,core.MODE+4:4,core.MODE+8:self.manager,core.MODE+12:4,
            part.PRESENT:7,part.CONSUMED:0,
            core.POINTERS:self.goku,core.POINTERS+8:self.piccolo,
            self.goku+0x994:0,self.goku+0x9e4:40000,
            self.piccolo+0x994:1,self.piccolo+0x9e4+0xa4:40000}

    def change(self,slot=1):
        cpu=EE([(roles.CHANGE0,roles.change_code(roles.CHANGE0,roles.TRAMP0))],self.memory)
        registers=cpu.r[8:16].copy()
        exit_at=cpu.run(roles.CHANGE0,0,slot)
        self.assertEqual(cpu.r[8:16],registers)
        self.assertEqual(cpu.r[4:6],[0,slot])
        return cpu,exit_at

    def test_active_partner_becomes_story_role_without_replacing_or_disabling_a_body(self):
        cpu,exit_at=self.change()
        self.assertEqual(exit_at,0x100000)
        self.assertEqual(cpu.mem[roles.CONTROL+8],self.piccolo)
        self.assertEqual(cpu.mem[self.piccolo+0x994],1)
        self.assertEqual(cpu.mem[self.goku+0x994],0)
        self.assertEqual(cpu.r[2],0) # no new native wait for a tag animation

    def test_reserve_keeps_native_change_member_and_its_arguments(self):
        cpu,exit_at=self.change(2)
        self.assertEqual(exit_at,roles.TRAMP0)
        self.assertEqual(cpu.mem[roles.CONTROL+8],self.goku)

    def test_authored_skill_uses_the_living_character_already_controlled_by_p2(self):
        request=0x1b0000
        self.memory.update({0x333f10:request,request+8:10005})
        cpu,exit_at=self.change(1)
        self.assertEqual(exit_at,0x100000)
        self.assertEqual(cpu.mem[roles.CONTROL+8],self.piccolo)

    def test_authored_skill_keeps_native_change_when_target_is_not_in_arena(self):
        request=0x1b0000
        self.memory.update({0x333f10:request,request+8:10005,part.PRESENT:1})
        _,exit_at=self.change(1)
        self.assertEqual(exit_at,roles.TRAMP0)
        self.assertEqual(self.memory[roles.CONTROL+8],self.goku)

    def test_story_role_classifies_skills_inside_called_actions(self):
        from history_script_metadata import flatten_action
        action={'kind':1,'opcode':1603,'args':[]}
        events={10005:{'commands':[{'kind':2,'opcode':9999,'args':[]}]},
                9999:{'commands':[action]}}
        self.assertEqual(flatten_action(events,10005),[action])

    def test_story_event_map_finds_replacements_through_nested_calls(self):
        change={'kind':1,'opcode':8,'args':[{'integer':17},{'integer':22}],
                'address':0x1234}
        skill={'kind':1,'opcode':1603,'args':[],'address':0x1238}
        events={10002:{'commands':[{'kind':2,'opcode':9000,'args':[]}]},
                9000:{'commands':[{'kind':3,'opcode':9001,'args':[]}]},
                9001:{'commands':[change,skill]},
                10003:{'commands':[{'kind':2,'opcode':9002,'args':[]}]},
                9002:{'commands':[skill]}}
        mapped=roles.story_event_map(events)
        self.assertEqual(mapped[2],1) # side 0, reserve slot 1
        self.assertEqual(mapped[3],0xffffffff) # a skill-only event is not a swap

    def test_story_event_map_leaves_incomplete_or_ambiguous_graphs_native(self):
        a={'kind':1,'opcode':8,'args':[{'integer':16},{'integer':1}], 'address':1}
        b={'kind':1,'opcode':8,'args':[{'integer':17},{'integer':1}], 'address':2}
        events={10000:{'commands':[{'kind':2,'opcode':9999,'args':[]}]},
                10001:{'commands':[a,b]}}
        mapped=roles.story_event_map(events)
        self.assertEqual(mapped[0],0xffffffff) # missing call target
        self.assertEqual(mapped[1],0xffffffff) # multiple authored replacements

    def test_absent_defeated_and_consumed_partners_are_not_selected(self):
        for address,value in ((part.PRESENT,3),(part.CONSUMED,4),(self.piccolo+0x9e4+0xa4,0)):
            with self.subTest(address=address):
                previous=self.memory[address];self.memory[address]=value
                _,exit_at=self.change();self.assertEqual(exit_at,roles.TRAMP0)
                self.memory[address]=previous

    def test_other_native_modes_are_unchanged(self):
        self.memory[0x331dd0]=0
        _,exit_at=self.change();self.assertEqual(exit_at,roles.TRAMP0)

    def test_preparation_defers_authored_swap_only_for_armed_history_coop(self):
        import native_preparation as prep
        self.memory.update({prep.CONTROL:prep.MAGIC,prep.ACCEPTED_MODE:1,0x331dd0:1})
        code=roles.defer_code()
        cpu=EE([(roles.DEFER,code)],self.memory)
        self.assertEqual(cpu.run(roles.DEFER,0,1),0x100000)
        self.assertEqual(cpu.r[2],0)
        for address,value in ((prep.ACCEPTED_MODE,0),(0x331dd0,0),(prep.CONTROL,0)):
            with self.subTest(address=address,value=value):
                self.memory[address]=value
                cpu=EE([(roles.DEFER,code)],self.memory)
                self.assertEqual(cpu.run(roles.DEFER,0,1),roles.DEFER_TRAMP)
        self.memory.update({prep.CONTROL:prep.MAGIC,prep.ACCEPTED_MODE:1,0x331dd0:1})

    def detect(self,label=10001):
        request=0x334464
        self.memory.update({0x333f10:request,request:2,request+8:label,
            request+12:0x333d0c+label-10000,roles.EVENT_MAP+(label-10000)*4:1})
        cpu=EE([(roles.FIND,roles.redundant_event_code())],self.memory)
        self.assertEqual(cpu.run(roles.FIND),0x100000)
        return cpu.r[2]

    def test_redundant_prompt_is_detected_only_for_an_active_living_destination(self):
        self.assertEqual(self.detect(),self.piccolo)
        self.memory[self.piccolo+0x9e4+0xa4]=0
        self.assertEqual(self.detect(),0)

    def test_dialogue_without_replacement_still_requires_native_input(self):
        self.detect()
        self.memory[roles.EVENT_MAP+4]=0xffffffff
        cpu=EE([(roles.FIND,roles.redundant_event_code())],self.memory)
        cpu.run(roles.FIND);self.assertEqual(cpu.r[2],0)

    def test_only_script_facade_gets_story_role_and_native_bypass_is_respected(self):
        self.memory[roles.CONTROL+8]=self.piccolo
        original=struct.pack('<2I',0x27bdffe0,0xffa80000)
        code=[(roles.PHYSICAL,roles.physical_code(original))]
        cpu=EE(code,self.memory);registers=cpu.r[8:16].copy()
        self.assertEqual(cpu.run(roles.PHYSICAL,0,ra=0x20a104),0x20a104)
        self.assertEqual(cpu.r[2],self.piccolo)
        self.assertEqual(cpu.r[8:16],registers)
        for ra,bypass in ((0x120000,0),(0x20a104,1)):
            with self.subTest(ra=ra,bypass=bypass):
                self.memory[roles.CONTROL+28]=bypass
                cpu=EE(code,self.memory)
                self.assertEqual(cpu.run(roles.PHYSICAL,0,ra=ra),core.PHYSICAL+8)


if __name__=='__main__':unittest.main()
