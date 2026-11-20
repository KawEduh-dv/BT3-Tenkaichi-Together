"""Apresentação local com desenho próprio e retratos extraídos da ISO.

Nenhuma imagem ou identidade visual fornecida pelo Tag Team Mod é carregada.
As fontes usadas no Windows pertencem ao sistema operacional.
"""
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw
import fonts
import character_names

BLUE = (17, 76, 137)
GOLD = (255, 193, 54)
WHITE = (243, 248, 255)
DIM = (161, 192, 220)


@lru_cache(maxsize=24)
def font(size, bold=False):
    return fonts.truetype('sans-bold' if bold else 'sans', size)


def fitted(draw, text, width, size=14, bold=False):
    text=str(text).replace('\n',' ')
    face=font(size,bold)
    if draw.textlength(text,font=face)<=width:
        return text
    while text and draw.textlength(text+'…',font=face)>width:
        text=text[:-1]
    return text+'…' if text else ''


def label(draw, text, xy, width, size=14, bold=False, fill=WHITE):
    draw.text(xy,fitted(draw,text,width,size,bold),font=font(size,bold),fill=fill)


def panel(draw, box, selected=False):
    draw.rounded_rectangle(box,radius=8,fill=(11,43,78),
                           outline=GOLD if selected else (61,116,164),width=2 if selected else 1)
    if selected:
        x,y,_,bottom=box
        draw.rounded_rectangle((x+1,y+5,x+5,bottom-5),radius=2,fill=GOLD)


def heading(image, title, subtitle='', badge=None):
    draw=ImageDraw.Draw(image)
    width=image.width
    draw.polygon([(0,0),(width,0),(width-28,59),(0,59)],fill=(8,31,65))
    draw.line((18,61,width-18,61),fill=GOLD,width=2)
    label(draw,title,(22,9),width-48,24,True)
    label(draw,subtitle,(23,39),width-48,11,fill=DIM)
    if badge:
        draw.rounded_rectangle((width-98,12,width-22,32),radius=7,fill=GOLD)
        draw.text((width-88,15),badge,font=font(10,True),fill=(15,40,67))


def footer(image, primary='Detalhes', secondary='Voltar', detail=''):
    draw=ImageDraw.Draw(image)
    y=image.height-55
    draw.rectangle((2,y,image.width-3,image.height-3),fill=(6,28,54))
    draw.line((18,y,image.width-18,y),fill=(59,103,144))
    for x,glyph,text in ((22,'X',primary),(179,'△',secondary)):
        draw.ellipse((x,y+12,x+20,y+32),fill=(30,72,112),outline=(120,166,206))
        draw.text((x+5,y+14),glyph,font=font(12,True),fill=WHITE)
        label(draw,text,(x+27,y+14),123,12,True)
    label(draw,detail,(23,y+36),image.width-46,10,fill=DIM)


@lru_cache(maxsize=1)
def menu_palette():
    # Paleta de 16 cores: reserva tons de pele/roupa para os retratos originais.
    colors=((8,31,65),(11,43,78),(17,76,137),(24,98,166),(37,115,177),
            GOLD,WHITE,DIM,(61,116,164),(14,14,22),(238,183,135),(165,101,63),
            (233,98,30),(101,177,81),(180,42,49),(130,148,166))
    palette=Image.new('P',(1,1))
    palette.putpalette([c for rgb in colors for c in rgb]*16)
    return palette


def portrait_card(image, fighter, box, player=None, compact=False):
    draw=ImageDraw.Draw(image)
    panel(draw,box)
    x,y,right,bottom=box
    side=bottom-y-6
    cid=fighter if type(fighter)is int else fighter.get('character_id',fighter.get('character'))
    pic=portrait(cid)
    if pic is not None:
        pic=pic.resize((side,side),Image.Resampling.NEAREST)
        image.paste(pic,(x+3,y+3),pic)
    textx=x+side+10
    label(draw,character_names.character_name(cid),(textx,y+8),right-textx-7,12,True)
    if player:
        caption='JOGADOR '+str(player)
    elif type(fighter)is dict and fighter.get('reserve'):
        caption='REFORÇO'
    else:
        caption='CPU'
    if type(fighter)is dict and fighter.get('costume',0):
        caption+=' · TRAJE '+str(fighter['costume']+1)
    if not compact:
        label(draw,caption,(textx,y+25),right-textx-7,9,fill=GOLD if player else DIM)
        if bottom-y>=58 and isinstance(fighter,dict) and fighter.get('hp'):
            health=f"{fighter['hp']:,}".replace(',','.')+' PV'
            label(draw,health,(textx,y+43),right-textx-7,10,True,fill=DIM)


def scenario_browser(controller):
    """Biblioteca de batalhas; não anuncia integração ainda inexistente com a campanha."""
    image=backdrop()
    draw=ImageDraw.Draw(image)
    entries=controller.entries
    if controller.detail and entries:
        entry=entries[controller.row]
        doc=entry.get('document')
        heading(image,'PREPARAR BATALHA','Escolha seus controles e entre na arena')
        label(draw,entry['title'],(22,72),468,18,True)
        if doc:
            player_team=doc.get('player_team',1)
            for column,side in enumerate((player_team,3-player_team)):
                x=22+column*250
                label(draw,'ALIADOS' if column==0 else 'ADVERSÁRIOS',(x,107),216,11,True,fill=GOLD)
                fighters=sorted((f for f in doc['fighters'] if f['team']==side),key=lambda f:f['slot'])
                height=64 if len(fighters)<=2 else 54 if len(fighters)==3 else 40 if len(fighters)==4 else 34
                for index,f in enumerate(fighters[:5]):
                    player=(index+1 if column==0 and index<doc.get('human_players',1) and not controller.cpu_only else None)
                    portrait_card(image,f,(x,125+index*(height+4),x+218,125+index*(height+4)+height),player,compact=height<40)
            panel(draw,(22,315,490,359),selected=True)
            count=doc.get('human_players',1)
            label(draw,'SIMULAÇÃO CPU' if controller.cpu_only else ('COOPERATIVO · 2 JOGADORES' if count==2 else '1 JOGADOR'),
                  (34,322),435,12,True,fill=GOLD)
            stage=doc.get('stage') or {}
            label(draw,stage.get('name','Escolher arena ao continuar'),(34,340),435,10,fill=DIM)
            footer(image,'Jogar','Voltar','Esq./Dir.: alternar jogadores e simulação · Batalha independente')
        else:
            panel(draw,(22,122,490,235))
            label(draw,'Batalha indisponível',(36,138),434,16,True,fill=GOLD)
            label(draw,entry.get('error','Não foi possível abrir a batalha.'),(36,171),434,12)
            footer(image,'—','Voltar')
    else:
        heading(image,'BATALHAS COOPERATIVAS','Lutadores simultâneos na mesma equipe',badge='P1 + P2')
        label(draw,'ESCOLHA UMA BATALHA',(22,69),360,10,True,fill=DIM)
        label(draw,str(len(entries))+' disponíveis',(390,69),100,10,fill=DIM)
        first=controller.row//7*7
        for index,entry in enumerate(entries[first:first+7]):
            row=first+index;y=87+index*40
            selected=row==controller.row
            panel(draw,(20,y,491,y+35),selected)
            label(draw,f'{row+1:02}',(32,y+10),27,11,True,fill=GOLD if selected else DIM)
            label(draw,entry['title'],(69,y+5),400,13,True,fill=WHITE if not entry.get('error') else (244,156,136))
            doc=entry.get('document') or {}
            description='COOP 2P' if doc.get('human_players')==2 else 'CENÁRIO'
            label(draw,description,(70,y+22),390,8,fill=GOLD if selected else DIM)
        if not entries:
            panel(draw,(22,110,490,210))
            label(draw,'Nenhuma batalha disponível',(38,130),434,17,True)
        footer(image,'Detalhes','Voltar','Cima/Baixo: selecionar · L1/R1: página · Batalhas independentes')
    if controller.notice:
        draw.rounded_rectangle((22,365,490,387),radius=5,fill=(80,37,29))
        label(draw,controller.notice,(30,370),452,10,fill=(255,214,174))
    return image.quantize(palette=menu_palette(),dither=Image.Dither.NONE).convert('RGB')


def backdrop(size=(512, 448)):
    width, height = size
    result = Image.new('RGB', size)
    d = ImageDraw.Draw(result)
    for y in range(height):
        f = y / max(1, height-1)
        d.line((0, y, width, y), fill=(int(23-13*f), int(118-78*f), int(196-100*f)))
    # Geometria desenhada nesta extensão: diagonais e faixas, sem sprites externos.
    d.polygon([(0, 0), (width*.72, 0), (width*.28, height), (0, height)], fill=(24, 98, 166))
    for x in range(-height, width, 62):
        d.line((x, height, x+height, 0), fill=(37, 115, 177), width=2)
    d.rectangle((0, 0, width-1, height-1), outline=GOLD, width=3)
    return result


def credits():
    """Own FullCoop credit layout; the technical base is attributed in text."""
    image=backdrop()
    draw=ImageDraw.Draw(image)
    heading(image,'TENKAICHI TOGETHER','BT3 · Créditos')
    panel(draw,(18,78,494,184),selected=True)
    label(draw,'PROJETO, DIREÇÃO E IDEALIZAÇÃO',(34,91),440,11,True,fill=DIM)
    label(draw,'KawEduh',(32,112),280,33,True,fill=GOLD)
    label(draw,'Cooperativo local · Dragon History',(35,158),420,12)
    # Only portraits extracted from the selected original disc are admitted.
    for cid,x in ((0,355),(22,419)):
        pic=portrait(cid)
        if pic is not None:
            pic=pic.resize((62,62),Image.Resampling.NEAREST)
            image.paste(pic,(x,109),pic)
    panel(draw,(18,198,494,289))
    label(draw,'BASE TÉCNICA',(34,209),440,11,True,fill=DIM)
    label(draw,'Tag Team Mod',(32,228),440,23,True)
    label(draw,'tehmufti e colaboradores · código GPL-3.0',(34,263),440,12,fill=GOLD)
    panel(draw,(18,303,494,377))
    label(draw,'JOGO ORIGINAL',(34,312),440,11,True,fill=DIM)
    label(draw,'Dragon Ball Z: Budokai Tenkaichi 3',(34,332),440,16,True)
    label(draw,'Créditos originais preservados no jogo.',(34,356),440,11)
    draw.rectangle((3,392,508,444),fill=(8,31,65))
    draw.line((18,392,494,392),fill=GOLD,width=2)
    draw.ellipse((22,403,42,423),fill=(30,72,112),outline=DIM)
    draw.line((28,409,36,417),fill=WHITE,width=2)
    draw.line((28,417,36,409),fill=WHITE,width=2)
    draw.ellipse((47,403,67,423),fill=(30,72,112),outline=DIM)
    draw.line((57,408,51,418,63,418,57,408),fill=WHITE,width=1)
    label(draw,'Voltar',(76,405),170,14,True)
    label(draw,'Um projeto de KawEduh',(269,409),220,11,fill=DIM)
    return image.quantize(palette=menu_palette(),dither=Image.Dither.NONE).convert('RGB')


def portrait(character_id):
    """Só aceita o diretório de retratos da ISO escolhida, nunca caminhos arbitrários."""
    info = character_names.character_info(character_id)
    value = info.get('portrait_path')
    if not value:
        return None
    path = Path(value).resolve()
    allowed = (character_names.assets_folder() / 'portraits').resolve()
    if not path.is_relative_to(allowed):
        raise ValueError('Retrato fora do diretório extraído da ISO')
    try:
        with Image.open(path) as image:
            return image.convert('RGBA')
    except OSError:
        return None


def centred(draw, text, y, font, width=512, fill='white'):
    draw.text(((width-draw.textlength(text, font=font))/2, y), text, font=font, fill=fill,
              stroke_width=1, stroke_fill=(9, 30, 58))


def compose(teams, progress, message, mode='teams', humans=2, error=None):
    image = backdrop()
    d = ImageDraw.Draw(image)
    def rows_for(side):
        return next((t.get('fighters',t.get('members',[])) for t in teams if t.get('side')==side),[])
    sides_with_humans={side for side in (0,1) for row in rows_for(side)
                      if isinstance(row,dict) and row.get('player',0)>0}
    coop=(mode in ('coop','training_coop') or
          (mode in ('teams','training') and humans>1 and len(sides_with_humans)<=1 and len(rows_for(0))>=humans))
    heading(image,'COOPERATIVO' if coop else 'PREPARANDO BATALHA',
            'Lute ao lado do seu parceiro' if coop else 'Os lutadores estão entrando na arena')
    for side in (0, 1):
        rows=rows_for(side)
        team_label = 'ALIADOS' if side == 0 and coop else 'EQUIPE 1' if side == 0 else 'ADVERSÁRIOS'
        x = 28 if side == 0 else 290
        label(d,team_label,(x,86),194,11,True,fill=GOLD)
        height=68 if len(rows)<=3 else 40
        for index,row in enumerate(rows[:5]):
            y=110+(height+5)*index
            player=row.get('player') if isinstance(row,dict) else None
            if player is None and coop and side==0 and index<humans:
                player=index+1
            portrait_card(image,row,(x,y,x+194,y+height),player)
    centred(d,'VS',183,font(22,True),fill=GOLD)
    p = max(0, min(100, int(progress)))
    d.rounded_rectangle((28, 357, 484, 380), radius=7, fill=(8, 35, 67), outline=GOLD, width=2)
    if p:
        d.rounded_rectangle((32, 361, max(33, 32+448*p//100), 376), radius=4, fill=GOLD)
    centred(d, str(p)+'%', 386, fonts.truetype('sans-bold', 17))
    text = ' / '.join(error) if error else 'Preparando a batalha...'
    centred(d, text[:65], 419, fonts.truetype('sans', 12))
    return dict(background=image, foreground=None, lights=None)


def transition():
    image = backdrop((768, 576))
    d = ImageDraw.Draw(image)
    centred(d, 'BUDOKAI TENKAICHI 3', 242, fonts.truetype('sans-bold', 40), width=768)
    centred(d, 'CARREGANDO', 312, fonts.truetype('sans-bold', 20), width=768, fill=GOLD)
    return image
