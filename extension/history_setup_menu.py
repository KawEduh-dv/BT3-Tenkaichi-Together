"""Controller-operated setup at the original Dragon History chapter screen.

The input lease is scoped to the captured scene-6 manager. It never edits
chapter selections, mission IDs or progress. A draining state consumes the
confirmation release so the same press cannot also choose a native chapter.
"""
import struct
import input_binding
import mod_settings
from prototype import Assembler
from native_map import A

CODE,CONTROL,END=0x06982000,0x06982f00,0x06983000
MAGIC=0x48534d31
PAD,MANAGER=A(0x333800),A(0x2ff10c)
_M=input_binding.MASKS
UP,DOWN,LEFT,RIGHT,CROSS,TRIANGLE=(_M[k] for k in ('up','down','left','right','cross','triangle'))


def input_code():
    a=Assembler(CODE);a.li(8,CONTROL);a.lw(9,8);a.li(10,MAGIC)
    a.branch(5,9,10,'no');a.lw(9,8,4);a.branch(4,9,0,'no')
    a.lw(10,8,8);a.branch(4,10,0,'expire');a.addiu(10,10,-1);a.sw(10,8,8)
    a.li(10,MANAGER);a.lw(10,10);a.lw(11,8,20);a.branch(5,10,11,'expire')
    a.li(11,0x100000);a.r(0x2b,11,10,11);a.branch(5,11,0,'expire')
    a.li(11,0x1fff000);a.r(0x2b,11,10,11);a.branch(4,11,0,'expire')
    a.lw(10,10,0x18);a.addiu(11,0,6);a.branch(5,10,11,'expire')
    a.li(10,PAD);a.lw(11,10,0x148);a.lw(12,10,0x1c0+0x148)
    a.r(0x25,11,11,12);a.sw(11,8,24)
    a.addiu(12,0,2);a.branch(5,9,12,'capture')
    a.branch(5,11,0,'consume');a.sw(0,8,4);a.jump('consume')
    a.label('capture')
    for port,previous in ((0,16),(0x1c0,28)):
        a.lw(11,10,port+0x150);a.lw(12,8,previous);a.sw(11,8,previous)
        a.i(14,12,12,0xffff);a.r(0x24,11,11,12)
        a.lw(12,8,12);a.r(0x25,11,11,12);a.sw(11,8,12)
    a.label('consume')
    for port in (0,0x1c0):
        for field in (0x150,0x18c,0x190):a.sw(0,10,port+field)
    a.addiu(2,0,1);a.jr()
    a.label('expire');a.sw(0,8,4);a.sw(0,8,12)
    a.label('no');a.move(2,0);a.jr()
    result=a.finish();assert len(result)<CONTROL-CODE;return result


def code_pieces():return [(CODE,input_code())]


class Controller:
    def __init__(self,settings=None):
        self.settings=dict(settings or {})
        self.active=False;self.session=False;self.players=1;self.page='players';self.row=0
        self.screen=None;self.dirty=True;self.input_ready=False;self.result=None
        self.ally_hp=125;self.enemy_hp=150;self.enemy_bonus=25;self.formation='duo';self.presented_once=False

    def picture(self):
        from PIL import Image,ImageDraw
        import fullcoop_loading_art as art
        # Keep the native Dragon History scenery and its Scenario/Difficulty
        # choices visible.  This keyed panel adds only the coop controls.
        key=(255,0,255)
        image=Image.new('RGB',(512,448),key);draw=ImageDraw.Draw(image)
        if self.page=='players':
            draw.rounded_rectangle((70,245,442,303),radius=5,fill=(9,34,63),outline=(239,174,42),width=2)
            draw.line((76,248,436,248),fill=(255,207,77),width=1)
            art.label(draw,'JOGADORES NA CAMPANHA',(82,253),210,13,True)
            value='1 JOGADOR' if self.players==1 else '2 JOGADORES'
            art.label(draw,value,(300,253),128,15,True,fill=art.GOLD)
            art.label(draw,'ESQUERDA / DIREITA: ALTERAR  -  X: CONFIGURAR',(82,276),348,10,True)
            art.label(draw,'TRIANGULO: JOGAR SOZINHO',(82,290),348,9,fill=art.DIM)
        else:
            # Keep configuration compact in the empty band between the native
            # scenario choices and dialogue box. The earlier full-height card
            # hid the game's art/text and made the overlay feel like a separate
            # app instead of a Dragon History option.
            draw.rounded_rectangle((56,210,456,344),radius=5,fill=(8,31,58),outline=(239,174,42),width=2)
            draw.line((64,234,448,234),fill=(67,113,155),width=1)
            art.label(draw,'REGRAS DA CAMPANHA',(70,216),210,13,True,fill=art.GOLD)
            art.label(draw,'L/R AJUSTA  ·  X CONFIRMA  ·  △ VOLTA',(252,219),190,8,True,fill=art.DIM)
            rows=(('Vida dos aliados',str(self.ally_hp)+'%'),
                  ('Vida dos inimigos',str(self.enemy_hp)+'%'),
                  ('Bônus inimigo por aliado',f'+{self.enemy_bonus}%'),
                  ('Formação', 'Dupla (P1 + P2)' if self.formation=='duo' else 'Time x Time'),
                  ('Iniciar campanha coop','2 jogadores'))
            for i,(title,value) in enumerate(rows):
                y=236+i*19
                draw.rounded_rectangle((70,y,442,y+18),radius=3,
                    fill=(17,61,101) if self.row==i else (11,43,74),
                    outline=(255,193,54) if self.row==i else (54,101,142),width=2 if self.row==i else 1)
                art.label(draw,title,(82,y+3),250,9,True)
                art.label(draw,value,(330,y+2),102,9,True,fill=art.GOLD)
            art.label(draw,'CIMA / BAIXO: ESCOLHER  ·  L/R: AJUSTAR',(82,332),350,8,True,fill=art.DIM)
        return image

    def press(self,edges):
        self.dirty=True
        if self.page=='players':
            if edges&(LEFT|RIGHT):self.players=3-self.players
            if edges&TRIANGLE:self.players=1;return self.commit()
            if edges&CROSS:
                if self.players==1:return self.commit()
                self.page='rules';self.row=0
        else:
            if edges&TRIANGLE:self.page='players';return None
            if edges&(UP|DOWN):self.row=(self.row+(1 if edges&DOWN else -1))%5
            if self.row==3 and edges&(LEFT|RIGHT):
                self.formation='time_x_time' if self.formation=='duo' else 'duo'
            if self.row<3 and edges&(LEFT|RIGHT):
                key=('ally_hp','enemy_hp','enemy_bonus')[self.row]
                low=0 if self.row==2 else 25
                high=100 if self.row==2 else 400
                setattr(self,key,max(low,min(high,getattr(self,key)+(25 if edges&RIGHT else -25))))
            if edges&CROSS and self.row==4:return self.commit()
        return None

    def commit(self):
        self.result=dict(mode='coop' if self.players==2 else 'teams',humans=self.players,history=True,
                         health=dict(history_ally_hp_percent=self.ally_hp,history_enemy_hp_percent=self.enemy_hp,
                                     history_enemy_hp_per_ally_bonus=self.enemy_bonus,
                                     history_formation=self.formation))
        return self.result

    def open(self,p,owner):
        from guest_loading_screen import GuestLoadingScreen
        if p.read(CODE,len(input_code()))!=input_code():raise ValueError('Story setup input hook is not installed')
        magic=p.read_u32(CONTROL)
        if magic not in (0,MAGIC):raise ValueError('Story setup control reservation is occupied')
        self.active=True;self.page='players';self.row=0;self.dirty=True;self.result=None
        self.input_ready=False;self.presented_once=False
        # Upgrade the old 100% default while respecting any value the player
        # deliberately raised above the new baseline.
        self.ally_hp=max(125,self.settings.get('history_ally_hp_percent',125))
        self.enemy_hp=self.settings.get('history_enemy_hp_percent',150)
        self.enemy_bonus=self.settings.get('history_enemy_hp_per_ally_bonus',25)
        self.formation=self.settings.get('history_formation','duo')
        self.screen=GuestLoadingScreen()
        p.write(CONTROL,struct.pack('<8I',MAGIC,1,180,0,p.read_u32(PAD+0x150),owner,0,
                                     p.read_u32(PAD+0x1c0+0x150)))

    def close(self,p,*,drain=True):
        p.write_u32(CONTROL+4,2 if drain else 0);p.write_u32(CONTROL+12,0)
        if self.screen:self.screen.hide(client=p)
        self.screen=None;self.active=False

    def tick(self,p):
        manager=p.read_u32(MANAGER)
        scene=p.read_u32(manager+0x18) if 0x100000<=manager<0x1fff000 else None
        if scene==4:self.session=False
        if scene!=6:
            if self.active:self.close(p,drain=False)
            return None
        if not self.settings.get('fullcoop_interface'):return None
        if not self.active:
            if self.session:return None
            self.open(p,manager)
        p.write_u32(CONTROL+8,180)
        if p.read_u32(CONTROL+4)!=1:
            self.close(p,drain=False);return None
        edges=p.read_u32(CONTROL+12)&0xffff
        if edges:p.write_u32(CONTROL+12,0)
        if self.dirty:
            self.screen.show_picture(self.picture(),surface='owned',client=p,
                                     transparent_key=(255,0,255),texture_overlay=True)
            self.dirty=False
        else:self.screen.sync(client=p)
        if not self.screen.presented(p):return None
        self.presented_once=True
        if not self.input_ready:
            self.input_ready=p.read_u32(CONTROL+24)==0
            return None
        if edges:self.press(edges)
        if self.result is not None:
            result=self.result;self.result=None;self.session=True
            self.close(p);return result
        return None
