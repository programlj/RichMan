# -*- coding: utf-8 -*-
"""
双人大富翁 4K旗舰版 - Two-Player Monopoly 4K Ultimate
3840×2160 窗口 | 高级感UI | 2200×2200棋盘 | 音量调节 | 20%过路费
"""

import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import random, math, struct, time, json, os, sys, subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Callable

# Auto-install pygame
def _ensure_pygame():
    try: import pygame; return pygame
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pygame", "-q"])
        import pygame; return pygame
pygame = _ensure_pygame()

# ==================== 4K Constants ====================
WINDOW_W = 3840; WINDOW_H = 2160
CELL_SIZE = 175; GRID = 11; BOARD_SZ = CELL_SIZE * GRID  # 1925
# Content: board(1925) + gap(40) + panel(850) = 2815, margin = (3840-2815)/2 = 512
BOARD_X = 512; BOARD_Y = 12
PANEL_X = 2477; PANEL_Y = 12; PANEL_W = 850; PANEL_H = BOARD_SZ
TITLE_H = 55; BUTTON_H = 155

PLAYER1_C = "#1E88E5"; PLAYER2_C = "#E53935"
P1_LIGHT = "#BBDEFB"; P2_LIGHT = "#FFCDD2"
BOARD_BORDER = "#6D4C41"
CELL_BG_DEFAULT = "#FFF8E1"
CELL_START = ("#66BB6A", "#A5D6A7")
CELL_JAIL = ("#FFA726", "#FFCC80")
CELL_PARKING = ("#BDBDBD", "#E0E0E0")
CELL_BANKRUPT = ("#EF5350", "#EF9A9A")
CELL_CHANCE = ("#FF9800", "#FFE0B2")
CELL_COMM = ("#42A5F5", "#BBDEFB")
CENTER_BG = "#FFFBF0"

BTN_ROLL_BG = ("#FF9800", "#F57C00"); BTN_BUY_BG = ("#4CAF50", "#388E3C")
BTN_END_BG = ("#2196F3", "#1976D2"); BTN_RESTART_BG = ("#9E9E9E", "#757575")
BTN_RULES_BG = ("#795548", "#5D4037"); BTN_MORTGAGE_BG = ("#FF7043", "#E64A19")
BTN_JAIL_BG = ("#8D6E63", "#6D4C41"); BTN_MUTE_BG = ("#607D8B", "#455A64")

CARD_BG_C = "#FFF3E0"; CARD_BD_C = "#E65100"
CARD_BG_CC = "#E3F2FD"; CARD_BD_CC = "#1565C0"
MORTGAGE_OVERLAY = "#EF5350"

# Fonts (1.6x scaled)
F_TITLE = ("Microsoft YaHei", 48, "bold")
F_SUBTITLE = ("Microsoft YaHei", 28, "bold")
F_PLAYER = ("Microsoft YaHei", 28, "bold")      # Changed: 28pt for player name
F_PLAYER_INFO = ("Microsoft YaHei", 24)
F_PLAYER_SMALL = ("Microsoft YaHei", 20)
F_NORMAL = ("Microsoft YaHei", 24)
F_BUTTON = ("Microsoft YaHei", 22, "bold")
F_CELL_NAME = ("Microsoft YaHei", 18, "bold")
F_CELL_PRICE = ("Microsoft YaHei", 14)
F_STATUS = ("Microsoft YaHei", 28, "bold")
F_LOG = ("Consolas", 18)
F_RULES_TITLE = ("Microsoft YaHei", 28, "bold")
F_RULES_BODY = ("Microsoft YaHei", 20)
F_CTR_TITLE = ("Microsoft YaHei", 56, "bold")
F_CTR_SUB = ("Microsoft YaHei", 30, "italic")
F_DICE_NUM = ("Microsoft YaHei", 72, "bold")
F_CARD_TITLE = ("Microsoft YaHei", 24, "bold")
F_CARD_BODY = ("Microsoft YaHei", 20)
F_CARD_ICON = ("Microsoft YaHei", 36)
F_MORT_TITLE = ("Microsoft YaHei", 22, "bold")
F_MORT_ITEM = ("Microsoft YaHei", 18)
F_VOL = ("Microsoft YaHei", 16, "bold")

PIECE_SZ = 64; PIECE_OFF = 28
INITIAL_CASH = 1500
CARD_DISPLAY_MS = 3500; CARD_FADE = 6
SAMPLE_RATE = 22050
VOL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "volume_settings.json")

# ==================== Volume Persistence ====================
def load_vol():
    try:
        with open(VOL_FILE, 'r') as f: return json.load(f)
    except: return {"bgm": 0.5, "sfx": 0.7, "muted": False}

def save_vol(settings):
    try:
        with open(VOL_FILE, 'w') as f: json.dump(settings, f)
    except: pass

# ==================== Audio System ====================
class AudioManager:
    def __init__(self):
        try: pygame.mixer.init(frequency=SAMPLE_RATE, size=-16, channels=2, buffer=512)
        except: pass
        s = load_vol()
        self.bgm_vol = s.get("bgm", 0.5); self.sfx_vol = s.get("sfx", 0.7)
        self.muted = s.get("muted", False)
        self._bgm_ch = self._sfx_ch = None; self._bgm_on = False
        try: self._bgm_ch = pygame.mixer.Channel(0); self._sfx_ch = pygame.mixer.Channel(1)
        except: pass

    def _save(self): save_vol({"bgm": self.bgm_vol, "sfx": self.sfx_vol, "muted": self.muted})

    def _gen_sound(self, freq, dur, wave="sine", decay=True, vol=1.0):
        n = int(SAMPLE_RATE * dur); buf = []
        for i in range(n):
            t = i / SAMPLE_RATE; env = 1.0 - i / n if decay else 1.0
            if wave == "sine": val = math.sin(2 * math.pi * freq * t)
            elif wave == "square": val = 1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0
            elif wave == "triangle": ph = (freq * t) % 1.0; val = 4.0 * abs(ph - 0.5) - 1.0
            elif wave == "noise": val = random.uniform(-1, 1)
            else: val = math.sin(2 * math.pi * freq * t)
            s = int(val * env * vol * 16000); s = max(-32767, min(32767, s))
            buf.append(struct.pack('<h', s))
        try: return pygame.mixer.Sound(buffer=b''.join(buf))
        except: return None

    def _play_sfx(self, freq, dur, wave="sine"):
        if self.muted: return
        snd = self._gen_sound(freq, dur, wave, vol=self.sfx_vol)
        if snd and self._sfx_ch: snd.set_volume(self.sfx_vol); self._sfx_ch.play(snd)

    def _play_combo(self, notes, wave="sine"):
        if self.muted: return
        total = sum(d for _, d in notes); n_s = int(SAMPLE_RATE * total); buf = []; t_off = 0
        for freq, dur in notes:
            n = int(SAMPLE_RATE * dur)
            for i in range(n):
                t = (t_off + i) / SAMPLE_RATE; env = max(0, 1.0 - i / n)
                val = math.sin(2 * math.pi * freq * t) if wave != "square" else (1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0)
                s = int(val * env * self.sfx_vol * 16000); s = max(-32767, min(32767, s))
                buf.append(struct.pack('<h', s))
            t_off += dur
        try:
            snd = pygame.mixer.Sound(buffer=b''.join(buf)); snd.set_volume(self.sfx_vol)
            if self._sfx_ch: self._sfx_ch.play(snd)
        except: pass

    def sfx_roll(self): self._play_sfx(80, 0.15, "noise"); self._play_combo([(300, 0.05), (450, 0.05), (600, 0.08)], "square")
    def sfx_move(self): self._play_sfx(250, 0.04, "square")
    def sfx_buy(self): self._play_combo([(523, 0.08), (659, 0.08), (784, 0.12)])
    def sfx_rent(self): self._play_combo([(400, 0.08), (300, 0.12)])
    def sfx_chance(self): self._play_combo([(440, 0.06), (554, 0.06), (659, 0.06), (880, 0.1)], "triangle")
    def sfx_community(self): self._play_combo([(330, 0.06), (440, 0.06), (523, 0.06), (659, 0.1)], "triangle")
    def sfx_jail(self): self._play_combo([(400, 0.1), (300, 0.1), (200, 0.15)], "square")
    def sfx_jail_free(self): self._play_combo([(523, 0.06), (659, 0.06), (784, 0.06), (1047, 0.12)])
    def sfx_bankrupt(self): self._play_combo([(600, 0.12), (400, 0.12), (200, 0.12), (100, 0.3)], "square")
    def sfx_win(self): self._play_combo([(523, 0.1), (659, 0.1), (784, 0.1), (1047, 0.1), (784, 0.1), (1047, 0.2)])
    def sfx_click(self): self._play_sfx(800, 0.03)
    def sfx_card_draw(self): self._play_sfx(600, 0.08, "triangle")
    def sfx_start(self): self._play_combo([(392, 0.1), (523, 0.1), (659, 0.1), (784, 0.15)])

    def _gen_bgm(self):
        melody = [(262, 0.3), (294, 0.3), (330, 0.3), (349, 0.3), (392, 0.3), (440, 0.3), (494, 0.3), (523, 0.3),
                  (494, 0.3), (440, 0.3), (392, 0.3), (349, 0.3), (330, 0.3), (294, 0.3), (262, 0.3), (330, 0.3),
                  (349, 0.3), (392, 0.3), (440, 0.3), (392, 0.3), (349, 0.3), (330, 0.3), (294, 0.3), (262, 0.4)]
        tdur = sum(d for _, d in melody) + 0.3; ns = int(SAMPLE_RATE * tdur); buf = []; toff = 0
        for freq, dur in melody:
            n = int(SAMPLE_RATE * dur)
            for i in range(n):
                t = (toff + i) / SAMPLE_RATE
                att = min(1.0, i / (SAMPLE_RATE * 0.02))
                rel = max(0.0, 1.0 - max(0, i - n + SAMPLE_RATE * 0.03) / (SAMPLE_RATE * 0.03))
                env = 0.85 * att * rel
                val = math.sin(2 * math.pi * freq * t) * 0.6 + math.sin(2 * math.pi * freq * 2 * t) * 0.2 + math.sin(2 * math.pi * freq * 3 * t) * 0.1
                s = int(val * env * self.bgm_vol * 12000); s = max(-32767, min(32767, s))
                buf.append(struct.pack('<h', s))
            toff += dur
        for _ in range(int(SAMPLE_RATE * 0.3)): buf.append(struct.pack('<h', 0))
        try: return pygame.mixer.Sound(buffer=b''.join(buf))
        except: return None

    def start_bgm(self):
        if self.muted or self._bgm_on: return
        try:
            snd = self._gen_bgm()
            if snd and self._bgm_ch: snd.set_volume(self.bgm_vol); self._bgm_ch.play(snd, loops=-1); self._bgm_on = True
        except: pass

    def stop_bgm(self):
        try:
            if self._bgm_ch: self._bgm_ch.stop()
            self._bgm_on = False
        except: pass

    def set_bgm_vol(self, v): self.bgm_vol = v
    def set_sfx_vol(self, v): self.sfx_vol = v
    def apply_vol(self):
        self._save()
        if self._bgm_ch and self._bgm_on:
            self._bgm_ch.set_volume(self.bgm_vol if not self.muted else 0)
    def apply_mute(self):
        self._save()
        if self.muted: self.stop_bgm()
        else: self.start_bgm()

# ==================== Enums & Data ====================
class CellType(Enum):
    START="start"; PROPERTY="property"; JAIL="jail"; FREE_PARKING="free_parking"
    BANKRUPTCY="bankruptcy"; CHANCE="chance"; COMMUNITY_CHEST="community"

class CardType(Enum):
    CHANCE="chance"; COMMUNITY_CHEST="community"

@dataclass
class Card:
    card_type:CardType; title:str; description:str
    effect:Callable[['GameEngine',int],str]; keepable:bool=False

@dataclass
class BoardCell:
    name:str; price:int; cell_type:CellType; row:int; col:int
    owner:Optional[int]=None; mortgaged:bool=False

@dataclass
class Player:
    name:str; color:str; light_color:str; cash:int=INITIAL_CASH; position:int=0
    start_cash:int=INITIAL_CASH  # record initial cash for display
    properties:List[int]=field(default_factory=list); skip_turn:bool=False; jail_free_cards:int=0

# ==================== Card Deck ====================
class CardDeck:
    def __init__(self, cards):
        self._all=list(cards); self._pile=[]; self._disc=[]; self.shuffle()
    def shuffle(self):
        self._pile=list(self._all+self._disc); random.shuffle(self._pile); self._disc=[]
    def draw(self):
        if not self._pile: self.shuffle()
        if self._pile:
            c=self._pile.pop(0)
            if not c.keepable: self._disc.append(c)
            return c
        return None
    def return_keepable(self, c): self._disc.append(c)

# ==================== Card Effects ====================
def _go_jail(eng, p): eng.players[p].position=30; eng.players[p].skip_turn=True; return "直接进监狱，暂停一回合！"
def _c_start(eng, p): eng.players[p].position=0; eng.players[p].cash+=200; return "前进到起点，获得200元！"
def _c_pos25(eng, p):
    pl=eng.players[p]; t=25; old=pl.position
    if t<old: pl.cash+=200
    pl.position=t; c=eng.get_cell(t)
    if c.owner is None: return f"前进到{c.name}(¥{c.price})"
    elif c.owner==p: return f"前进到{c.name}（你的地产）"
    else: rt=max(1,int(c.price*0.2))*2; pl.cash-=rt; eng.players[c.owner].cash+=rt; return f"前进到{c.name}，双倍过路费¥{rt}"
def _c_pos35(eng, p):
    pl=eng.players[p]; t=35; old=pl.position
    if t<old: pl.cash+=200
    pl.position=t; c=eng.get_cell(t)
    if c.owner is None: return f"前进到{c.name}(¥{c.price})"
    elif c.owner==p: return f"前进到{c.name}（你的地产）"
    else: fee=(eng.dice1+eng.dice2)*10; pl.cash-=fee; eng.players[c.owner].cash+=fee; return f"前进到{c.name}，10倍骰子¥{fee}"
def _c_div(eng, p): eng.players[p].cash+=50; return "股息50元！"
def _c_jf(eng, p): eng.players[p].jail_free_cards+=1; return "获得出狱免费卡！"
def _c_back3(eng, p): eng.players[p].position=(eng.players[p].position-3)%40; return "后退3格"
def _c_fine(eng, p): eng.players[p].cash-=15; return "超速罚款15元"
def _c_pay(eng, p): eng.players[p].cash-=50; eng.players[1-p].cash+=50; return f"向{eng.players[1-p].name}支付50元"
def _c_loan(eng, p): eng.players[p].cash+=150; return "贷款到期，获得150元"
def _c_cross(eng, p): eng.players[p].cash+=100; return "填字比赛赢得100元"
def _c_pos26(eng, p):
    pl=eng.players[p]; t=26
    if t<pl.position: pl.cash+=200
    pl.position=t; return f"前进到商业街（{eng.get_cell(t).name}）"
def _c_pos38(eng, p):
    pl=eng.players[p]; t=38
    if t<pl.position: pl.cash+=200
    pl.position=t; return f"前进到公园大道（{eng.get_cell(t).name}）"
def _c_repair(eng, p):
    pl=eng.players[p]; c=len(pl.properties)*30; pl.cash-=c; return f"维修费{c}元"
def _c_lotto(eng, p): eng.players[p].cash+=200; return "中彩票200元！"
def _c_stock(eng, p): eng.players[p].cash+=300; return "股市大涨300元！"

def _m_start(eng, p): eng.players[p].position=0; eng.players[p].cash+=200; return "前进到起点，获得200元！"
def _m_bank(eng, p): eng.players[p].cash+=200; return "银行出错，获得200元！"
def _m_doc(eng, p): eng.players[p].cash-=50; return "看医生支付50元"
def _m_jf(eng, p): eng.players[p].jail_free_cards+=1; return "获得出狱免费卡！"
def _m_jail(eng, p): return _go_jail(eng, p)
def _m_bday(eng, p): eng.players[1-p].cash-=50; eng.players[p].cash+=50; return f"生日！{eng.players[1-p].name}给你50元"
def _m_opera(eng, p): eng.players[1-p].cash-=30; eng.players[p].cash+=30; return f"歌剧之夜，{eng.players[1-p].name}支付30元"
def _m_tax(eng, p): eng.players[p].cash+=20; return "退税20元"
def _m_ins(eng, p): eng.players[p].cash+=100; return "保险到期，获得100元"
def _m_hosp(eng, p): eng.players[p].cash-=100; return "住院支付100元"
def _m_tuit(eng, p): eng.players[p].cash-=50; return "学费50元"
def _m_cons(eng, p): eng.players[p].cash+=25; return "咨询费25元"
def _m_street(eng, p):
    pl=eng.players[p]; c=len(pl.properties)*40; pl.cash-=c; return f"街道维修{c}元"
def _m_beauty(eng, p): eng.players[p].cash+=10; return "选美第二名，获得10元"
def _m_inherit(eng, p): eng.players[p].cash+=100; return "继承遗产100元"
def _m_stock_s(eng, p): eng.players[p].cash+=50; return "股票出售50元"

def create_chance_deck():
    return CardDeck([
        Card(CardType.CHANCE,"前进到起点","前进到起点，获得200元",_c_start),
        Card(CardType.CHANCE,"前进","前进到餐厅(¥240)",_c_pos25),
        Card(CardType.CHANCE,"前进","前进到银行(¥320)",_c_pos35),
        Card(CardType.CHANCE,"股息","银行支付股息50元",_c_div),
        Card(CardType.CHANCE,"出狱免费","出狱免费卡（可保留）",_c_jf,keepable=True),
        Card(CardType.CHANCE,"后退","后退3格",_c_back3),
        Card(CardType.CHANCE,"进监狱","直接进监狱",lambda e,p:_go_jail(e,p)),
        Card(CardType.CHANCE,"超速罚款","罚款15元",_c_fine),
        Card(CardType.CHANCE,"董事会主席","向每位玩家支付50元",_c_pay),
        Card(CardType.CHANCE,"贷款到期","获得150元",_c_loan),
        Card(CardType.CHANCE,"填字比赛","赢得100元",_c_cross),
        Card(CardType.CHANCE,"前进","前进到商场(¥260)",_c_pos26),
        Card(CardType.CHANCE,"前进","前进到摩天大楼(¥400)",_c_pos38),
        Card(CardType.CHANCE,"维修","每处地产支付30元",_c_repair),
        Card(CardType.CHANCE,"彩票","中彩票200元",_c_lotto),
        Card(CardType.CHANCE,"股市大涨","获得300元",_c_stock),
    ])

def create_community_deck():
    return CardDeck([
        Card(CardType.COMMUNITY_CHEST,"前进到起点","前进到起点，获得200元",_m_start),
        Card(CardType.COMMUNITY_CHEST,"银行出错","银行多给了200元",_m_bank),
        Card(CardType.COMMUNITY_CHEST,"看医生","支付50元",_m_doc),
        Card(CardType.COMMUNITY_CHEST,"出狱免费","出狱免费卡（可保留）",_m_jf,keepable=True),
        Card(CardType.COMMUNITY_CHEST,"进监狱","直接进监狱",_m_jail),
        Card(CardType.COMMUNITY_CHEST,"生日","从每位玩家获得50元",_m_bday),
        Card(CardType.COMMUNITY_CHEST,"歌剧之夜","收取30元门票",_m_opera),
        Card(CardType.COMMUNITY_CHEST,"退税","获得20元",_m_tax),
        Card(CardType.COMMUNITY_CHEST,"人寿保险","获得100元",_m_ins),
        Card(CardType.COMMUNITY_CHEST,"住院","支付100元",_m_hosp),
        Card(CardType.COMMUNITY_CHEST,"学费","支付50元",_m_tuit),
        Card(CardType.COMMUNITY_CHEST,"咨询费","获得25元",_m_cons),
        Card(CardType.COMMUNITY_CHEST,"街道维修","每处地产支付40元",_m_street),
        Card(CardType.COMMUNITY_CHEST,"选美比赛","获得10元",_m_beauty),
        Card(CardType.COMMUNITY_CHEST,"继承遗产","获得100元",_m_inherit),
        Card(CardType.COMMUNITY_CHEST,"股票出售","获得50元",_m_stock_s),
    ])

# ==================== Game Engine ====================
class GameEngine:
    PROPERTY_DEFS = {
        1:("村庄",60),2:("农田",60),3:("果园",80),4:("渔村",80),5:("牧场",100),6:("林场",100),
        8:("集市",100),9:("小商店",120),11:("面包店",120),13:("书店",140),14:("花店",160),
        15:("服装店",160),16:("药店",180),17:("小餐馆",180),18:("电影院",200),19:("健身房",200),
        21:("超市",200),23:("医院",220),24:("学校",240),25:("餐厅",240),26:("商场",260),
        27:("写字楼",260),28:("体育馆",280),29:("剧院",280),31:("博物馆",280),32:("图书馆",280),
        33:("游泳馆",300),34:("大酒店",300),35:("银行",320),37:("游乐园",380),38:("摩天大楼",400),39:("宫殿",400),
    }
    CARD_CELLS={7:CellType.CHANCE,22:CellType.CHANCE,12:CellType.COMMUNITY_CHEST,36:CellType.COMMUNITY_CHEST}
    CARD_NAMES={7:("机遇",CellType.CHANCE),22:("机遇",CellType.CHANCE),12:("命运",CellType.COMMUNITY_CHEST),36:("命运",CellType.COMMUNITY_CHEST)}
    CORNERS={0:("起点",CellType.START),10:("破产",CellType.BANKRUPTCY),20:("免费停车",CellType.FREE_PARKING),30:("监狱",CellType.JAIL)}

    def __init__(self, audio=None):
        self.audio=audio; self.players=[]; self.board=[]; self.current_player_idx=0
        self.dice1=0; self.dice2=0; self.log=[]; self.game_over=False; self.winner=None
        self.chance_deck=create_chance_deck(); self.community_deck=create_community_deck()
        self.last_drawn_card=None; self._init_board(); self._init_players()

    def _init_board(self):
        self.board=[]
        for pos in range(40):
            r,c=self._pos_to_grid(pos)
            if pos in self.CORNERS: n,ct=self.CORNERS[pos]; pr=0
            elif pos in self.CARD_CELLS: n,ct=self.CARD_NAMES[pos]; pr=0
            else: n,pr=self.PROPERTY_DEFS.get(pos,("?",0)); ct=CellType.PROPERTY
            self.board.append(BoardCell(n,pr,ct,r,c))

    def _init_players(self):
        cash = getattr(self, 'INITIAL_CASH', INITIAL_CASH)
        self.players=[Player("玩家 1",PLAYER1_C,P1_LIGHT,cash=cash,start_cash=cash),
                       Player("玩家 2",PLAYER2_C,P2_LIGHT,cash=cash,start_cash=cash)]
        self.current_player_idx=0; self.game_over=False; self.winner=None

    @staticmethod
    def _pos_to_grid(pos):
        if pos<=10: return (10,pos)
        elif pos<=20: return (20-pos,10)
        elif pos<=30: return (0,30-pos)
        else: return (pos-30,0)

    @property
    def current_player(self): return self.players[self.current_player_idx]
    def get_cell(self,pos): return self.board[pos]

    def roll_dice(self):
        self.dice1=random.randint(1,6); self.dice2=random.randint(1,6)
        self.add_log(f"{self.current_player.name} 掷出 [{self.dice1}][{self.dice2}]，共{self.dice1+self.dice2}点")
        return self.dice1,self.dice2

    def draw_card(self,ct):
        d=self.chance_deck if ct==CellType.CHANCE else self.community_deck
        card=d.draw(); self.last_drawn_card=card
        cn="机遇卡" if ct==CellType.CHANCE else "命运卡"
        self.add_log(f"🃏 {self.current_player.name} 抽到{cn}：「{card.title}」")
        return card

    def use_jail_free(self,pi):
        p=self.players[pi]
        if p.jail_free_cards>0: p.jail_free_cards-=1; p.skip_turn=False; self.add_log(f"🔑 {p.name}使用出狱免费卡！"); return True
        return False

    def execute_card_effect(self,pi,card):
        r=card.effect(self,pi); self.add_log(f"  → {r}"); return r

    # Mortgage
    def mortgage_property(self,pi,pos):
        p=self.players[pi]; c=self.get_cell(pos)
        if pos not in p.properties: return False,"不是你的地产"
        if c.mortgaged: return False,"已抵押"
        mv=int(c.price*0.5); c.mortgaged=True; p.cash+=mv
        self.add_log(f"🏚️ {p.name}抵押{c.name}，获得¥{mv}"); return True,f"抵押{c.name}，获得¥{mv}"

    def redeem_property(self,pi,pos):
        p=self.players[pi]; c=self.get_cell(pos)
        if pos not in p.properties: return False,"不是你的地产"
        if not c.mortgaged: return False,"未抵押"
        mv=int(c.price*0.5); rc=int(mv*1.1)
        if p.cash<rc: return False,f"现金不足，需要¥{rc}"
        p.cash-=rc; c.mortgaged=False
        self.add_log(f"🏠 {p.name}赎回{c.name}，支付¥{rc}"); return True,f"赎回{c.name}，支付¥{rc}"

    def get_mortgageable(self,pi): return [p for p in self.players[pi].properties if not self.get_cell(p).mortgaged]
    def get_mortgaged(self,pi): return [p for p in self.players[pi].properties if self.get_cell(p).mortgaged]
    def get_mortgage_val(self,pos): return int(self.get_cell(pos).price*0.5)
    def get_redeem_cost(self,pos): return int(self.get_cell(pos).price*0.5*1.1)

    def process_landing(self):
        pl=self.current_player; c=self.get_cell(pl.position)
        if c.cell_type==CellType.START: pl.cash+=200; self.add_log(f"🎉 {pl.name}到达起点，+200元！"); return "start"
        elif c.cell_type==CellType.JAIL: pl.skip_turn=True; self.add_log(f"🔒 {pl.name}进监狱！"); return "jail"
        elif c.cell_type==CellType.FREE_PARKING: self.add_log(f"🅿️ {pl.name}免费停车"); return "parking"
        elif c.cell_type==CellType.BANKRUPTCY:
            pl.cash-=150; self.add_log(f"💸 {pl.name}破产格，-150元！")
            if pl.cash<0 and not self._can_avoid(pl): self._bankrupt(pl); return "bankrupt"
            return "penalty"
        elif c.cell_type in (CellType.CHANCE,CellType.COMMUNITY_CHEST):
            return "chance" if c.cell_type==CellType.CHANCE else "community"
        elif c.cell_type==CellType.PROPERTY:
            if c.owner is None: return "buyable"
            elif c.owner==self.current_player_idx: self.add_log(f"🏠 自己的{c.name}"); return "own"
            else:
                if c.mortgaged: self.add_log(f"🏚️ {c.name}已抵押，免过路费"); return "own"
                rent=max(1,int(c.price*0.2))  # 20% rent
                pl.cash-=rent; self.players[c.owner].cash+=rent
                self.add_log(f"💰 {pl.name}向{self.players[c.owner].name}支付过路费¥{rent}")
                if pl.cash<0 and not self._can_avoid(pl): self._bankrupt(pl); return "bankrupt"
                return "rent"
        return "unknown"

    def charge_pass_rent(self, pos: int) -> bool:
        """Charge 20% rent when passing through opponent's property.
        Returns True if player went bankrupt during this step."""
        pl = self.current_player
        c = self.get_cell(pos)
        if c.cell_type == CellType.PROPERTY and c.owner is not None \
           and c.owner != self.current_player_idx and not c.mortgaged:
            rent = max(1, int(c.price * 0.2))
            pl.cash -= rent; self.players[c.owner].cash += rent
            self.add_log(f"💰 {pl.name}经过{c.name}，支付¥{rent}维护费给{self.players[c.owner].name}")
            if pl.cash < 0 and not self._can_avoid(pl):
                self._bankrupt(pl); return True
        return False

    def _can_avoid(self,pl): return len([p for p in pl.properties if not self.get_cell(p).mortgaged])>0

    def buy_property(self):
        pl=self.current_player; c=self.get_cell(pl.position)
        if c.cell_type!=CellType.PROPERTY: return False,"不是地产"
        if c.owner is not None: return False,"已被购买"
        if c.mortgaged: return False,"已被抵押"
        if pl.cash<c.price: return False,f"现金不足（需要¥{c.price}）"
        pl.cash-=c.price; c.owner=self.current_player_idx; pl.properties.append(pl.position)
        self.add_log(f"🏠 {pl.name}购买{c.name}，花费¥{c.price}！"); return True,f"购买{c.name}成功！"

    def _bankrupt(self,pl):
        for pos in pl.properties:
            c=self.get_cell(pos)
            if c.mortgaged: c.mortgaged=False; c.owner=None; self.add_log(f"🏚️ 银行收回{c.name}")
        pl.properties.clear(); self.game_over=True
        self.winner=self.players[1-self.players.index(pl)]
        self.add_log(f"💀 {pl.name}破产！{self.winner.name}获胜！🎉")

    def next_turn(self):
        self.current_player_idx=1-self.current_player_idx; self.dice1=0; self.dice2=0
        if not self.game_over: self.add_log(f"➡️ 轮到{self.current_player.name}行动")

    def check_jail(self):
        pl=self.current_player
        if pl.skip_turn:
            if pl.jail_free_cards>0: return False
            pl.skip_turn=False; self.add_log(f"🔒 {pl.name}在监狱中，本回合跳过！"); return True
        return False

    def reset(self):
        self.chance_deck=create_chance_deck(); self.community_deck=create_community_deck()
        self.last_drawn_card=None; self._init_board(); self._init_players()
        self.log.clear(); self.dice1=0; self.dice2=0
        self.add_log("🎮 游戏开始！双人大富翁4K旗舰版！"); self.add_log(f"➡️ 轮到{self.current_player.name}行动")

    def add_log(self,msg): self.log.append(msg)
    def get_total_prop_val(self,pi): return sum(self.board[p].price for p in self.players[pi].properties)


# ==================== Board Canvas (4K Premium) ====================
class BoardCanvas(tk.Canvas):
    def __init__(self,parent,engine,**kw):
        super().__init__(parent,width=BOARD_SZ,height=BOARD_SZ,bg="#1A0A00",highlightthickness=0,**kw)
        self.engine=engine; self.piece_ids={}; self.cell_rects={}; self.dice1_t=0; self.dice2_t=0; self._draw_all()

    def _draw_all(self): self._draw_board(); self._draw_center(); self._draw_pieces()

    def _draw_board(self):
        for pos in range(40): self._draw_cell(self.engine.get_cell(pos),pos)

    def _draw_cell(self,cell,pos):
        x1=cell.col*CELL_SIZE; y1=cell.row*CELL_SIZE; x2=x1+CELL_SIZE; y2=y1+CELL_SIZE
        # Determine colors with gradient effect (top color, bottom color)
        if cell.owner is not None:
            oc=self.engine.players[cell.owner].color
            fill=oc; top=oc
        elif cell.cell_type==CellType.START: fill,top=CELL_START[0],CELL_START[1]
        elif cell.cell_type==CellType.JAIL: fill,top=CELL_JAIL[0],CELL_JAIL[1]
        elif cell.cell_type==CellType.FREE_PARKING: fill,top=CELL_PARKING[0],CELL_PARKING[1]
        elif cell.cell_type==CellType.BANKRUPTCY: fill,top=CELL_BANKRUPT[0],CELL_BANKRUPT[1]
        elif cell.cell_type==CellType.CHANCE: fill,top=CELL_CHANCE[0],CELL_CHANCE[1]
        elif cell.cell_type==CellType.COMMUNITY_CHEST: fill,top=CELL_COMM[0],CELL_COMM[1]
        else: fill,top="#FFF8E1","#FFF3E0"

        # Main rect with rounded corners (simulated)
        rid=self.create_rectangle(x1+2,y1+2,x2-2,y2-2,fill=fill,outline=BOARD_BORDER,width=2,tags="cell")
        # Top gradient bar
        self.create_rectangle(x1+2,y1+2,x2-2,y1+CELL_SIZE//3,fill=top,outline="",tags="cell")
        # Inner shadow effect
        self.create_rectangle(x1+4,y1+4,x2-4,y1+6,fill="#EEEEEE",outline="",tags="cell")
        self.cell_rects[pos]=rid

        # Mortgage overlay
        if cell.mortgaged:
            self.create_rectangle(x1+2,y1+2,x2-2,y2-2,fill="",outline=MORTGAGE_OVERLAY,width=3,tags="cell")
            for i in range(4):
                self.create_line(x1+10,y1+10+i*20,x2-10,y2-10-i*20,fill=MORTGAGE_OVERLAY,width=1,tags="cell")
            cx_m=x1+CELL_SIZE//2; cy_m=y1+CELL_SIZE//2
            self.create_rectangle(cx_m-50,cy_m-16,cx_m+50,cy_m+16,fill="#C62828",outline="",tags="cell")
            self.create_text(cx_m,cy_m,text="已抵押",font=("Microsoft YaHei",13,"bold"),fill="white",tags="cell")

        # Owner strip
        if cell.owner is not None:
            self.create_rectangle(x1+2,y1+2,x2-2,y1+12,fill=self.engine.players[cell.owner].color,outline="",tags="cell")

        cx=x1+CELL_SIZE//2; ny=y1+CELL_SIZE//2-18; py=y1+CELL_SIZE//2+18
        self.create_text(cx,ny,text=cell.name,font=F_CELL_NAME,fill="#333333",tags="cell")
        if cell.cell_type==CellType.PROPERTY:
            txt=f"¥{cell.price}" if not cell.mortgaged else f"¥{cell.price} [押]"
            self.create_text(cx,py,text=txt,font=F_CELL_PRICE,fill="#555555",tags="cell")
        elif cell.cell_type==CellType.START: self.create_text(cx,py,text="← 出发",font=F_CELL_PRICE,fill="#1B5E20",tags="cell")
        elif cell.cell_type==CellType.JAIL: self.create_text(cx,py,text="暂停一回合",font=F_CELL_PRICE,fill="#BF360C",tags="cell")
        elif cell.cell_type==CellType.FREE_PARKING: self.create_text(cx,py,text="休息一下",font=F_CELL_PRICE,fill="#424242",tags="cell")
        elif cell.cell_type==CellType.BANKRUPTCY: self.create_text(cx,py,text="罚金¥150",font=F_CELL_PRICE,fill="#B71C1C",tags="cell")
        elif cell.cell_type==CellType.CHANCE: self.create_text(cx,py,text="🃏 机遇卡",font=F_CELL_PRICE,fill="#BF360C",tags="cell")
        elif cell.cell_type==CellType.COMMUNITY_CHEST: self.create_text(cx,py,text="📦 命运卡",font=F_CELL_PRICE,fill="#0D47A1",tags="cell")

    def _draw_center(self):
        ix1=CELL_SIZE+2; iy1=CELL_SIZE+2; ix2=10*CELL_SIZE-2; iy2=10*CELL_SIZE-2
        self.create_rectangle(ix1,iy1,ix2,iy2,fill=CENTER_BG,outline=BOARD_BORDER,width=3,tags="center")
        cx=ix1+(ix2-ix1)//2; cy_top=iy1+280
        self.create_text(cx,cy_top-100,text="🎲 双人大富翁 🎲",font=F_CTR_TITLE,fill="#5D4037",tags="center")
        self.create_text(cx,cy_top-20,text="4K Ultimate Edition",font=F_CTR_SUB,fill="#8D6E63",tags="center")
        dy=cy_top+100
        self.create_rectangle(cx-280,dy,cx+280,dy+400,fill="#FFF8E1",outline=BOARD_BORDER,width=2,tags="center")
        self.create_text(cx,dy+45,text="🎯 骰子",font=("Microsoft YaHei",28,"bold"),fill="#5D4037",tags="center")
        self.create_rectangle(cx-200,dy+90,cx-20,dy+320,outline=BOARD_BORDER,width=3,tags="center")
        self.create_rectangle(cx+20,dy+90,cx+200,dy+320,outline=BOARD_BORDER,width=3,tags="center")
        self.dice1_t=self.create_text(cx-110,dy+205,text="?",font=F_DICE_NUM,fill="#999999",tags="center")
        self.dice2_t=self.create_text(cx+110,dy+205,text="?",font=F_DICE_NUM,fill="#999999",tags="center")
        self.total_t=self.create_text(cx,dy+380,text="",font=("Microsoft YaHei",28,"bold"),fill="#5D4037",tags="center")

    def _draw_pieces(self):
        for idx,pl in enumerate(self.engine.players): self._draw_piece(idx,pl)

    def _draw_piece(self,idx,pl):
        c=self.engine.get_cell(pl.position)
        cx=c.col*CELL_SIZE+CELL_SIZE//2; cy=c.row*CELL_SIZE+CELL_SIZE//2
        if idx==0: px=cx-PIECE_OFF; py=cy-PIECE_OFF
        else: px=cx+PIECE_OFF-PIECE_SZ; py=cy+PIECE_OFF-PIECE_SZ
        if idx in self.piece_ids: self.delete(self.piece_ids[idx])
        # Glow effect
        self.create_oval(px-4,py-4,px+PIECE_SZ+4,py+PIECE_SZ+4,fill="",outline=pl.color,width=3,tags="piece")
        pid=self.create_oval(px,py,px+PIECE_SZ,py+PIECE_SZ,fill=pl.color,outline="white",width=4,tags="piece")
        self.create_text(px+PIECE_SZ//2,py+PIECE_SZ//2,text=str(idx+1),font=("Microsoft YaHei",22,"bold"),fill="white",tags="piece")
        self.piece_ids[idx]=pid

    def update_display(self):
        try:
            self.delete("cell"); self.delete("piece"); self.cell_rects.clear()
            for pos in range(40): self._draw_cell(self.engine.get_cell(pos), pos)
            self._update_dice(); self.piece_ids.clear(); self._draw_pieces(); self.tag_raise("piece")
        except Exception:
            pass  # Never let a display update break the game loop

    def _update_dice(self):
        try:
            if self.engine.dice1 > 0:
                self.itemconfig(self.dice1_t, text=str(self.engine.dice1), fill="#333333")
                self.itemconfig(self.dice2_t, text=str(self.engine.dice2), fill="#333333")
                self.itemconfig(self.total_t, text=f"合计: {self.engine.dice1 + self.engine.dice2} 步")
            else:
                self.itemconfig(self.dice1_t, text="?", fill="#999999")
                self.itemconfig(self.dice2_t, text="?", fill="#999999")
                self.itemconfig(self.total_t, text="")
        except Exception:
            pass

    def animate_move(self, fp, steps, cb):
        """Animate movement, charging rent for EVERY opponent property passed."""
        positions = [(fp + i) % 40 for i in range(1, steps + 1)]
        if not positions:
            cb(); return

        self._anim_idx = 0
        self._anim_positions = positions
        self._anim_cb = cb
        self._anim_start = time.time()

        def tick():
            try:
                idx = self._anim_idx
                if time.time() - self._anim_start > 6.0:
                    self.engine.current_player.position = self._anim_positions[-1]
                    self.update_display(); self._anim_cb(); return
                if idx >= len(self._anim_positions):
                    self._anim_cb(); return

                pos = self._anim_positions[idx]
                self.engine.current_player.position = pos

                # CHARGE RENT for passing through opponent's property
                bankrupt = self.engine.charge_pass_rent(pos)
                self.update_display()

                if bankrupt:
                    self._anim_cb(); return  # stop immediately on bankruptcy

                self._anim_idx += 1
                delay = 80 + idx * 5
                self.after(min(delay, 200), tick)
            except Exception:
                try:
                    self.engine.current_player.position = self._anim_positions[-1]
                    self.update_display()
                except Exception:
                    pass
                self._anim_cb()

        tick()


# ==================== Player Panel (Premium Cards) ====================
class PlayerPanel(tk.Frame):
    CARD_H=430; AVATAR_SZ=140; CIRCLE_R=56

    def __init__(self,parent,engine,**kw):
        super().__init__(parent,width=PANEL_W,height=PANEL_H,bg="#F5F0E8",**kw)
        self.engine=engine; self.pack_propagate(False)
        self.p1_f=self.p2_f=None
        self.p1_cash=self.p1_prop=self.p1_val=self.p1_pos=self.p1_st=None
        self.p2_cash=self.p2_prop=self.p2_val=self.p2_pos=self.p2_st=None
        self.turn_l=self.log_t=None; self.card_f=self.card_icon=self.card_title=self.card_desc=None
        self._cf_job=None; self._build()

    def _build(self):
        tk.Label(self,text="📋 玩家信息",font=F_SUBTITLE,bg="#F5F0E8",fg="#4E342E").pack(pady=(12,6))
        self.p1_f=self._make_card(); self.p1_f.pack(fill="x",padx=20,pady=6); self._build_card(self.p1_f,0)
        self.p2_f=self._make_card(); self.p2_f.pack(fill="x",padx=20,pady=6); self._build_card(self.p2_f,1)
        self.turn_l=tk.Label(self,text="",font=F_STATUS,bg="#F5F0E8",fg="#4E342E"); self.turn_l.pack(pady=4)
        self._build_card_display()
        tk.Frame(self,height=2,bg="#BCAAA4").pack(fill="x",padx=25,pady=4)
        # Spacer so log TEXT starts at flower shop (pos14=grid[6][10], y=1050)
        # Title(56)+P1(442)+P2(442)+Turn(44)+Sep(10)=994
        # Log title ~35px → need 1050-35=1015 → spacer=1015-994=21
        tk.Frame(self,height=21,bg="#F5F0E8").pack(fill="x")
        tk.Label(self,text="📜 游戏日志",font=F_SUBTITLE,bg="#F5F0E8",fg="#4E342E").pack(pady=(4,2))
        self.log_t=ScrolledText(self,font=F_LOG,bg="#FFFDE7",fg="#333333",wrap=tk.WORD,state="disabled",height=14)
        self.log_t.pack(fill="x",expand=False,padx=20,pady=(0,12))

    def _make_card(self):
        # Clean single-frame card, matching log style
        card=tk.Frame(self,bg="white",bd=2,relief="solid",
                       highlightbackground="#BCAAA4",highlightthickness=1,
                       width=PANEL_W-40,height=self.CARD_H)
        card.pack_propagate(False)
        return card

    def _build_card(self,frame,pi):
        pl=self.engine.players[pi]; cw=PANEL_W-46
        av_sz=self.AVATAR_SZ; av=tk.Canvas(frame,width=av_sz,height=av_sz,bg="white",highlightthickness=0)
        av.place(x=22,y=(self.CARD_H-av_sz)//2)
        r=self.CIRCLE_R; cxa=cya=av_sz//2
        # Avatar gradient circles
        for i in range(r,0,-8): av.create_oval(cxa-i,cya-i,cxa+i,cya+i,fill=pl.color,outline="",width=0)
        av.create_oval(cxa-r,cya-r,cxa+r,cya+r,fill=pl.color,outline=pl.color,width=2)
        av.create_oval(cxa-r+3,cya-r+3,cxa+r-3,cya+r-3,fill="",outline="#EEEEEE",width=2)
        av.create_text(cxa,cya,text=str(pi+1),font=("Microsoft YaHei",34,"bold"),fill="white")

        # Info text - spaced to prevent any overlap
        ix=180; lh=62
        lines=6; y0=(self.CARD_H - lh*(lines-1))//2 - 10
        tk.Label(frame,text=pl.name,font=F_PLAYER,bg="white",fg=pl.color,anchor="w").place(x=ix,y=y0,width=cw-ix-15)
        cash_l=tk.Label(frame,text="",font=("Microsoft YaHei",24,"bold"),bg="white",fg="#1B5E20",anchor="w")
        cash_l.place(x=ix,y=y0+lh,width=cw-ix-15)
        prop_l=tk.Label(frame,text="",font=("Microsoft YaHei",18),bg="white",fg="#555555",anchor="w")
        prop_l.place(x=ix,y=y0+lh*2,width=cw-ix-15)
        val_l=tk.Label(frame,text="",font=("Microsoft YaHei",17),bg="white",fg="#777777",anchor="w")
        val_l.place(x=ix,y=y0+lh*3,width=cw-ix-15)
        pos_l=tk.Label(frame,text="",font=("Microsoft YaHei",17),bg="white",fg="#888888",anchor="w")
        pos_l.place(x=ix,y=y0+lh*4,width=cw-ix-15)
        st_l=tk.Label(frame,text="",font=("Microsoft YaHei",15,"bold"),bg="white",fg="#E65100",anchor="w")
        st_l.place(x=ix,y=y0+lh*5,width=cw-ix-15)
        if pi==0: self.p1_cash,self.p1_prop,self.p1_val,self.p1_pos,self.p1_st=cash_l,prop_l,val_l,pos_l,st_l
        else: self.p2_cash,self.p2_prop,self.p2_val,self.p2_pos,self.p2_st=cash_l,prop_l,val_l,pos_l,st_l
        self._set_vals(pi,cash_l,prop_l,val_l,pos_l,st_l)

    def _build_card_display(self): self.card_f=tk.Frame(self,bg="#F5F0E8")

    def show_card(self,card):
        self._hide_card()
        cbg=CARD_BG_C if card.card_type==CardType.CHANCE else CARD_BG_CC
        cbd=CARD_BD_C if card.card_type==CardType.CHANCE else CARD_BD_CC
        cl="🃏 机遇卡" if card.card_type==CardType.CHANCE else "📦 命运卡"
        ic="🃏" if card.card_type==CardType.CHANCE else "📦"
        self.card_f=tk.Frame(self,bg=cbg,bd=3,relief="solid",highlightbackground=cbd,highlightthickness=3)
        self.card_f.pack(fill="x",padx=20,pady=6,before=self.log_t.master)
        inn=tk.Frame(self.card_f,bg=cbg); inn.pack(fill="both",expand=True,padx=18,pady=14)
        self.card_icon=tk.Label(inn,text=ic,font=F_CARD_ICON,bg=cbg); self.card_icon.pack(side="left",padx=(0,15))
        ta=tk.Frame(inn,bg=cbg); ta.pack(side="left",fill="both",expand=True)
        self.card_title=tk.Label(ta,text=f"{cl}：{card.title}",font=F_CARD_TITLE,bg=cbg,fg=cbd,anchor="w"); self.card_title.pack(fill="x")
        self.card_desc=tk.Label(ta,text=card.description,font=F_CARD_BODY,bg=cbg,fg="#333333",anchor="w",justify="left"); self.card_desc.pack(fill="x",pady=(5,0))
        self._cf_job=self.after(CARD_DISPLAY_MS,self._start_fade)

    def _start_fade(self):
        if self.card_f is None or not self.card_f.winfo_exists(): return
        self._fs=0; self._do_fade()
    def _do_fade(self):
        if self.card_f is None or not self.card_f.winfo_exists(): return
        self._fs+=1
        if self._fs>=CARD_FADE: self._hide_card(); return
        self.card_f.configure(bg="#EFEBE0"); self.after(80,self._do_fade)
    def _hide_card(self):
        if self._cf_job is not None: self.after_cancel(self._cf_job); self._cf_job=None
        if self.card_f is not None and self.card_f.winfo_exists(): self.card_f.destroy(); self.card_f=None
        self.card_icon=self.card_title=self.card_desc=None

    def update_display(self):
        self._set_vals(0,self.p1_cash,self.p1_prop,self.p1_val,self.p1_pos,self.p1_st)
        self._set_vals(1,self.p2_cash,self.p2_prop,self.p2_val,self.p2_pos,self.p2_st)
        if self.engine.game_over:
            self.turn_l.config(text=f"🏆 {self.engine.winner.name}获胜！游戏结束！",fg="#2E7D32")
            self.p1_f.configure(highlightbackground="#BCAAA4",highlightthickness=1)
            self.p2_f.configure(highlightbackground="#BCAAA4",highlightthickness=1)
        else:
            cur=self.engine.current_player
            self.turn_l.config(text=f"🎯 当前行动: {cur.name}",fg=cur.color)
            if self.engine.current_player_idx==0:
                self.p1_f.configure(highlightbackground=PLAYER1_C,highlightthickness=4)
                self.p2_f.configure(highlightbackground="#BCAAA4",highlightthickness=1)
            else:
                self.p2_f.configure(highlightbackground=PLAYER2_C,highlightthickness=4)
                self.p1_f.configure(highlightbackground="#BCAAA4",highlightthickness=1)
        self._upd_log()

    def _set_vals(self,idx,cl,pl,vl,po,st):
        p=self.engine.players[idx]
        # Line 1: Cash
        cl.config(text=f"💰 现金: ¥{p.cash:,}")
        # Line 2: Property count + jail cards
        ji=f"  🔑出狱卡×{p.jail_free_cards}" if p.jail_free_cards>0 else ""
        pl.config(text=f"🏠 地产: {len(p.properties)}处{ji}")
        # Line 3: Total property value + mortgage info
        pv=self.engine.get_total_prop_val(idx)
        mc=len(self.engine.get_mortgaged(idx))
        mi=f"  ⚠已抵押×{mc}" if mc>0 else ""
        vl.config(text=f"💎 总价值: ¥{pv:,}{mi}")
        # Line 4: Position
        po.config(text=f"📍 {self.engine.get_cell(p.position).name}")
        # Line 5: Status
        if p.skip_turn: st.config(text="⚠ 下回合暂停（监狱中）")
        elif p.jail_free_cards>0: st.config(text=f"🔑 持有{p.jail_free_cards}张出狱免费卡（在监狱中可使用）")
        else: st.config(text="")

    def _upd_log(self):
        self.log_t.configure(state="normal"); self.log_t.delete("1.0",tk.END)
        for e in self.engine.log[-60:]: self.log_t.insert(tk.END,e+"\n")
        self.log_t.see(tk.END); self.log_t.configure(state="disabled")


# ==================== Mortgage Dialog ====================
class MortgageDialog(tk.Toplevel):
    def __init__(self,parent,engine,pi,on_close=None):
        super().__init__(parent); self.engine=engine; self.pi=pi; self.on_close=on_close
        self.selected=[]; self.mode="mortgage"; self._build()
        self.transient(parent); self.grab_set()
        dw,dh=900,800
        self.geometry(f"{dw}x{dh}+{(self.winfo_screenwidth()-dw)//2}+{(self.winfo_screenheight()-dh)//2}")
        self.resizable(False,False); self.title("地产管理 - 抵押/赎回")

    def _build(self):
        self.configure(bg="#FFF8E1"); pl=self.engine.players[self.pi]
        tk.Label(self,text=f"🏠 {pl.name} - 地产管理",font=F_MORT_TITLE,bg="#FFF8E1",fg="#4E342E").pack(pady=(15,5))
        self.cash_l=tk.Label(self,text=f"💰 当前现金: ¥{pl.cash:,}",font=("Microsoft YaHei",20,"bold"),bg="#FFF8E1",fg="#333333")
        self.cash_l.pack(pady=(0,8))
        tf=tk.Frame(self,bg="#FFF8E1"); tf.pack(fill="x",padx=30,pady=5)
        self.mt_btn=tk.Button(tf,text="🏚️ 抵押地产",font=("Microsoft YaHei",20,"bold"),bg="#E65100",fg="white",bd=0,padx=30,pady=12,command=lambda:self._sw("mortgage"))
        self.mt_btn.pack(side="left",padx=5)
        self.rd_btn=tk.Button(tf,text="💰 赎回地产",font=("Microsoft YaHei",20,"bold"),bg="#2E7D32",fg="white",bd=0,padx=30,pady=12,command=lambda:self._sw("redeem"))
        self.rd_btn.pack(side="left",padx=5)
        lf=tk.Frame(self,bg="#FFFDE7",bd=2,relief="solid"); lf.pack(fill="both",expand=True,padx=30,pady=10)
        self.canv=tk.Canvas(lf,bg="#FFFDE7",highlightthickness=0)
        sb=tk.Scrollbar(lf,orient="vertical",command=self.canv.yview)
        self.sf=tk.Frame(self.canv,bg="#FFFDE7")
        self.sf.bind("<Configure>",lambda e:self.canv.configure(scrollregion=self.canv.bbox("all")))
        self.canv.create_window((0,0),window=self.sf,anchor="nw")
        self.canv.configure(yscrollcommand=sb.set); self.canv.pack(side="left",fill="both",expand=True); sb.pack(side="right",fill="y")
        af=tk.Frame(self,bg="#FFF8E1"); af.pack(fill="x",padx=30,pady=(5,15))
        self.act_l=tk.Label(af,text="",font=("Microsoft YaHei",16),bg="#FFF8E1",fg="#C62828"); self.act_l.pack(side="left")
        tk.Button(af,text="执行",font=("Microsoft YaHei",20,"bold"),fg="white",bg="#4E342E",bd=0,padx=35,pady=12,command=self._exec).pack(side="right")
        tk.Button(af,text="关闭",font=("Microsoft YaHei",16),fg="#333",bg="#BDBDBD",bd=0,padx=25,pady=10,command=self.destroy).pack(side="right",padx=10)
        self._sw("mortgage")

    def _sw(self,m):
        self.mode=m; self.selected=[]
        self.mt_btn.configure(bg="#E65100" if m=="mortgage" else "#FF7043")
        self.rd_btn.configure(bg="#2E7D32" if m=="redeem" else "#43A047")
        self._refresh()

    def _refresh(self):
        for w in self.sf.winfo_children(): w.destroy()
        self.cvars={}
        props=self.engine.get_mortgageable(self.pi) if self.mode=="mortgage" else self.engine.get_mortgaged(self.pi)
        tt="可抵押地产" if self.mode=="mortgage" else "已抵押地产（可赎回）"
        tk.Label(self.sf,text=f"📋 {tt} ({len(props)}处)",font=("Microsoft YaHei",18,"bold"),bg="#FFFDE7",fg="#4E342E").pack(anchor="w",padx=15,pady=8)
        if not props: tk.Label(self.sf,text="  暂无可用地产",font=("Microsoft YaHei",16),bg="#FFFDE7",fg="#999999").pack(padx=20,pady=20)
        else:
            for pos in props: self._add_item(pos)
        self._upd_total()

    def _add_item(self,pos):
        c=self.engine.get_cell(pos); it=tk.Frame(self.sf,bg="white",bd=1,relief="solid"); it.pack(fill="x",padx=15,pady=3)
        var=tk.BooleanVar(value=False); self.cvars[pos]=var
        tk.Checkbutton(it,variable=var,bg="white",command=lambda p=pos:self._tog(p)).pack(side="left",padx=5)
        if self.mode=="mortgage": v=self.engine.get_mortgage_val(pos); info=f"{c.name} | 原价:¥{c.price:,} | 可抵押:¥{v:,}"
        else: rc=self.engine.get_redeem_cost(pos); mv=self.engine.get_mortgage_val(pos); info=f"{c.name} | 原价:¥{c.price:,} | 赎回:¥{rc:,} (本金¥{mv:,}+10%)"
        tk.Label(it,text=info,font=F_MORT_ITEM,bg="white",fg="#333333").pack(side="left",padx=15,pady=10)

    def _tog(self,pos):
        if self.cvars[pos].get(): self.selected.append(pos)
        elif pos in self.selected: self.selected.remove(pos)
        self._upd_total()

    def _upd_total(self):
        tot=sum(self.engine.get_mortgage_val(p) if self.mode=="mortgage" else self.engine.get_redeem_cost(p) for p in self.selected)
        pl=self.engine.players[self.pi]
        if self.mode=="mortgage": t=f"选择{len(self.selected)}处，共获得¥{tot:,}"
        else: t=f"选择{len(self.selected)}处，共支付¥{tot:,} (余额¥{pl.cash:,})" + (" ⚠余额不足！" if tot>pl.cash else "")
        self.act_l.config(text=t)

    def _exec(self):
        if not self.selected: messagebox.showwarning("提示","请至少选择一个地产。",parent=self); return
        pl=self.engine.players[self.pi]
        if self.mode=="mortgage":
            ok=sum(1 for p in self.selected if self.engine.mortgage_property(self.pi,p)[0])
            messagebox.showinfo("完成",f"成功抵押{ok}处地产",parent=self)
        else:
            tot=sum(self.engine.get_redeem_cost(p) for p in self.selected)
            if tot>pl.cash: messagebox.showwarning("余额不足",f"需要¥{tot:,}，你只有¥{pl.cash:,}",parent=self); return
            ok=sum(1 for p in self.selected if self.engine.redeem_property(self.pi,p)[0])
            messagebox.showinfo("完成",f"成功赎回{ok}处地产",parent=self)
        self._refresh()
        if self.on_close: self.on_close()


# ==================== Volume Control Panel ====================
class VolumePanel(tk.Toplevel):
    def __init__(self,parent,audio):
        super().__init__(parent); self.audio=audio
        self.title("音量控制"); self.configure(bg="#FFF8E1")
        self.transient(parent)
        dw,dh=500,380
        self.geometry(f"{dw}x{dh}+{(self.winfo_screenwidth()-dw)//2}+{(self.winfo_screenheight()-dh)//2}")
        self.resizable(False,False)
        self._build()

    def _build(self):
        tk.Label(self,text="🔊 音量控制",font=("Microsoft YaHei",22,"bold"),bg="#FFF8E1",fg="#4E342E").pack(pady=(15,10))

        # BGM volume
        bgm_f=tk.Frame(self,bg="#FFF8E1"); bgm_f.pack(fill="x",padx=40,pady=10)
        tk.Label(bgm_f,text="🎵 背景音乐",font=("Microsoft YaHei",18,"bold"),bg="#FFF8E1",fg="#333333").pack(side="left")
        self.bgm_l=tk.Label(bgm_f,text=f"{int(self.audio.bgm_vol*100)}%",font=("Microsoft YaHei",18),bg="#FFF8E1",fg="#666666")
        self.bgm_l.pack(side="right")
        self.bgm_s=tk.Scale(self,from_=0,to=100,orient="horizontal",length=380,bg="#FFF8E1",
                             highlightthickness=0,command=self._on_bgm)
        self.bgm_s.set(self.audio.bgm_vol*100); self.bgm_s.pack(padx=40)

        # SFX volume
        sfx_f=tk.Frame(self,bg="#FFF8E1"); sfx_f.pack(fill="x",padx=40,pady=(15,10))
        tk.Label(sfx_f,text="🔔 音效",font=("Microsoft YaHei",18,"bold"),bg="#FFF8E1",fg="#333333").pack(side="left")
        self.sfx_l=tk.Label(sfx_f,text=f"{int(self.audio.sfx_vol*100)}%",font=("Microsoft YaHei",18),bg="#FFF8E1",fg="#666666")
        self.sfx_l.pack(side="right")
        self.sfx_s=tk.Scale(self,from_=0,to=100,orient="horizontal",length=380,bg="#FFF8E1",
                             highlightthickness=0,command=self._on_sfx)
        self.sfx_s.set(self.audio.sfx_vol*100); self.sfx_s.pack(padx=40)

        # Mute button
        mute_text="🔇 取消静音" if self.audio.muted else "🔊 静音"
        self.mute_btn=tk.Button(self,text=mute_text,font=("Microsoft YaHei",18,"bold"),
                                 bg="#607D8B" if not self.audio.muted else "#E53935",fg="white",
                                 bd=0,padx=30,pady=10,command=self._tog_mute)
        self.mute_btn.pack(pady=(15,5))

        tk.Button(self,text="关闭",font=("Microsoft YaHei",16),bg="#BDBDBD",fg="#333",bd=0,padx=25,pady=8,command=self.destroy).pack(pady=(5,15))

    def _on_bgm(self,v):
        vol=int(v)/100; self.audio.set_bgm_vol(vol); self.audio.apply_vol()
        self.bgm_l.config(text=f"{int(v)}%")

    def _on_sfx(self,v):
        vol=int(v)/100; self.audio.set_sfx_vol(vol); self.audio.apply_vol()
        self.sfx_l.config(text=f"{int(v)}%")

    def _tog_mute(self):
        self.audio.muted=not self.audio.muted; self.audio.apply_mute()
        self.audio.sfx_click()
        if self.audio.muted: self.mute_btn.configure(text="🔇 取消静音",bg="#E53935")
        else: self.mute_btn.configure(text="🔊 静音",bg="#607D8B")


# ==================== Main App ====================
class RichManApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("双人大富翁 4K旗舰版"); self.configure(bg="#1A0A00")
        self.geometry(f"{WINDOW_W}x{WINDOW_H}")
        self.resizable(False,False)
        self.audio=AudioManager()
        # Ask for starting cash
        self._starting_cash = self._ask_starting_cash()
        self.engine=GameEngine(audio=self.audio)
        self.engine.INITIAL_CASH = self._starting_cash
        self._can_roll=True; self._can_buy=False; self._animating=False; self._pending_card=False
        self._pend_id=None; self._btns={}; self._muted=self.audio.muted
        self._build_ui(); self.engine.reset(); self.refresh_all()
        self.audio.sfx_start(); self.audio.start_bgm()
        # Center and maximize
        self.update_idletasks()
        self.geometry(f"+{max(0,(self.winfo_screenwidth()-WINDOW_W)//2)}+{max(0,(self.winfo_screenheight()-WINDOW_H)//2)}")
        try: self.state('zoomed')
        except: pass

    def _ask_starting_cash(self):
        """Popup to set starting cash before game begins."""
        from tkinter import simpledialog
        self.update_idletasks(); self.withdraw()
        v=simpledialog.askinteger("起始金额","每位玩家起始金额：\n(默认1500，范围500-10000)",
                                   initialvalue=INITIAL_CASH,minvalue=500,maxvalue=10000,parent=self)
        self.deiconify(); return v if v else INITIAL_CASH

    def _build_ui(self):
        # Title bar with volume control
        tf=tk.Frame(self,bg="#2E1A0A",height=TITLE_H); tf.pack(fill="x",side="top"); tf.pack_propagate(False)
        ti=tk.Frame(tf,bg="#2E1A0A"); ti.pack(expand=True,fill="both")
        tk.Label(ti,text="🎲 双 人 大 富 翁  🎲",font=F_TITLE,bg="#2E1A0A",fg="#FFCC80").place(relx=0.5,rely=0.5,anchor="center")
        # Volume + mute buttons on right
        vol_frame=tk.Frame(ti,bg="#2E1A0A"); vol_frame.place(relx=0.97,rely=0.5,anchor="e")
        self.mute_btn=tk.Button(vol_frame,text="🔊" if not self._muted else "🔇",font=("Microsoft YaHei",18),
                                 bg=BTN_MUTE_BG[0],fg="white",bd=0,padx=10,pady=4,cursor="hand2",command=self._tog_mute)
        self.mute_btn.pack(side="right",padx=3)
        self.vol_btn=tk.Button(vol_frame,text="🎚️ 音量",font=("Microsoft YaHei",14),
                                bg="#5D4037",fg="white",bd=0,padx=10,pady=4,cursor="hand2",command=self._open_vol)
        self.vol_btn.pack(side="right",padx=3)

        # Content
        ct=tk.Frame(self,bg="#1A0A00"); ct.pack(fill="both",expand=True,side="top")
        self.board_c=BoardCanvas(ct,self.engine)
        self.board_c.place(x=BOARD_X,y=BOARD_Y,width=BOARD_SZ,height=BOARD_SZ)
        self.panel=PlayerPanel(ct,self.engine)
        self.panel.place(x=PANEL_X,y=PANEL_Y,width=PANEL_W,height=PANEL_H)

        # Bottom
        bf=tk.Frame(self,bg="#1A0A00",height=BUTTON_H); bf.pack(fill="x",side="bottom"); bf.pack_propagate(False)
        self.st_l=tk.Label(bf,text="",font=F_STATUS,bg="#1A0A00",fg="#FFCC80"); self.st_l.pack(pady=(10,4))
        bc=tk.Frame(bf,bg="#1A0A00"); bc.pack(expand=True)
        specs=[("roll","🎲 掷骰子",BTN_ROLL_BG,self.on_roll),("buy","🏠 购买地产",BTN_BUY_BG,self.on_buy),
               ("end","⏭️ 结束回合",BTN_END_BG,self.on_end_turn),("mortgage","🏚️ 抵押地产",BTN_MORTGAGE_BG,self.on_mortgage),
               ("jail_free","🔑 出狱卡",BTN_JAIL_BG,self.on_use_jail),("restart","🔄 重新开始",BTN_RESTART_BG,self.on_restart),
               ("rules","📖 规则说明",BTN_RULES_BG,self.on_rules)]
        for k,t,cl,cb in specs:
            btn=self._mk_btn(bc,t,cl,cb); btn.pack(side="left",padx=8); self._btns[k]=btn

    def _mk_btn(self,p,text,colors,cmd):
        c1,c2=colors
        btn=tk.Button(p,text=text,font=F_BUTTON,fg="white",bg=c1,activeforeground="white",
                       activebackground=c2,bd=0,padx=28,pady=20,cursor="hand2",command=cmd,
                       width=10,disabledforeground="#999999")
        def _e(e,b=btn,bg=c1): b.configure(bg=self._light(bg,0.15)) if str(b.cget("state"))!="disabled" else None
        def _l(e,b=btn,bg=c1): b.configure(bg=bg) if str(b.cget("state"))!="disabled" else None
        btn.bind("<Enter>",_e); btn.bind("<Leave>",_l)
        return btn

    @staticmethod
    def _light(h,f): c=h.lstrip('#'); r,g,b=int(c[0:2],16),int(c[2:4],16),int(c[4:6],16); return f"#{min(255,int(r+(255-r)*f)):02x}{min(255,int(g+(255-g)*f)):02x}{min(255,int(b+(255-b)*f)):02x}"
    @staticmethod
    def _dark(h,f): c=h.lstrip('#'); r,g,b=int(c[0:2],16),int(c[2:4],16),int(c[4:6],16); return f"#{int(r*f):02x}{int(g*f):02x}{int(b*f):02x}"

    def _tog_mute(self):
        self.audio.sfx_click(); self.audio.muted=not self.audio.muted; self.audio.apply_mute()
        self._muted=self.audio.muted
        self.mute_btn.configure(text="🔇" if self._muted else "🔊",bg="#E53935" if self._muted else BTN_MUTE_BG[0])

    def _open_vol(self): self.audio.sfx_click(); VolumePanel(self,self.audio)

    def _upd_btns(self):
        pl=self.engine.current_player; hjc=pl.jail_free_cards>0; ij=pl.skip_turn; hp=len(pl.properties)>0
        if self.engine.game_over:
            self._setb(roll=False,buy=False,end=False,mortgage=False,jail_free=False,restart=True,rules=True)
            self.st_l.config(text="🏆 游戏结束！点击「重新开始」再来一局")
        elif self._animating: self._setb(0,0,0,0,0,0,1); self.st_l.config(text="🎲 移动中...")
        elif self._can_roll: self._setb(1,0,0,hp,hjc and ij,1,1); self.st_l.config(text=f"🎯 {pl.name}的回合，请掷骰子！")
        elif self._can_buy:
            c=self.engine.get_cell(pl.position); self._setb(0,1,1,hp,0,1,1)
            self.st_l.config(text=f"💡 可购买「{c.name}」(¥{c.price})，或结束回合")
        elif self._pending_card: self._setb(0,0,0,0,0,0,1); self.st_l.config(text="🃏 展示卡片中...")
        else: self._setb(0,0,1,0,0,1,1); self.st_l.config(text="点击「结束回合」继续")

    def _setb(self,roll,buy,end,mortgage,jail_free,restart,rules):
        ss={"roll":roll,"buy":buy,"end":end,"mortgage":mortgage,"jail_free":jail_free,"restart":restart,"rules":rules}
        cs={"roll":BTN_ROLL_BG[0],"buy":BTN_BUY_BG[0],"end":BTN_END_BG[0],"mortgage":BTN_MORTGAGE_BG[0],
            "jail_free":BTN_JAIL_BG[0],"restart":BTN_RESTART_BG[0],"rules":BTN_RULES_BG[0]}
        for k,v in ss.items():
            if k in self._btns: self._btns[k].configure(state=tk.NORMAL if v else tk.DISABLED,bg=cs[k] if v else "#555555")

    def _sched_end(self,d): self._cancel(); self._pend_id=self.after(d,self._end_sched)
    def _cancel(self):
        if self._pend_id is not None: self.after_cancel(self._pend_id); self._pend_id=None
    def _end_sched(self): self._pend_id=None; self._end_turn()

    def on_roll(self):
        if not self._can_roll or self._animating or self.engine.game_over: return
        self.audio.sfx_click()
        if self.engine.check_jail(): self._can_roll=False; self.refresh_all(); self._sched_end(1000); return
        self._can_roll=False; self._animating=True; self._can_buy=False; self._pending_card=False
        d1,d2=self.engine.roll_dice(); steps=d1+d2; fp=self.engine.current_player.position
        self.audio.sfx_roll(); self.refresh_all()
        self.after(500, lambda: self.board_c.animate_move(fp, steps, self._on_move_done))

    def _on_move_done(self):
        self._animating = False
        try:
            self.audio.sfx_move()
            result = self.engine.process_landing()
        except Exception as e:
            # Safety: ensure UI recovers from any error
            self._can_roll = False; self._can_buy = False
            self.refresh_all(); self._sched_end(500)
            return

        # --- Handle game-over from process_landing ---
        if self.engine.game_over:
            self._show_game_over()
            return

        if result in ("chance", "community"):
            self.audio.sfx_card_draw()
            ct = CellType.CHANCE if result == "chance" else CellType.COMMUNITY_CHEST
            card = self.engine.draw_card(ct)
            if card.card_type == CardType.CHANCE: self.audio.sfx_chance()
            else: self.audio.sfx_community()
            self.panel.show_card(card); self._pending_card = True; self.refresh_all()
            self.after(CARD_DISPLAY_MS, lambda: self._exec_card(card))

        elif result == "buyable":
            self._can_buy = True
            self.engine.add_log("💡 可购买当前地产，或结束回合"); self.refresh_all()

        elif result in ("rent", "penalty"):
            if result == "rent": self.audio.sfx_rent()
            self._can_buy = False; self.refresh_all()
            self._handle_debt_or_continue()  # <-- NEW: check bankruptcy before continuing

        elif result == "jail":
            self.audio.sfx_jail(); self._can_buy = False; self.refresh_all(); self._sched_end(800)

        else:
            self._can_buy = False; self.refresh_all(); self._sched_end(800)

    def _exec_card(self, card):
        self._pending_card = False
        if card.keepable:
            self.engine.execute_card_effect(self.engine.current_player_idx, card)
        else:
            self.engine.execute_card_effect(self.engine.current_player_idx, card)

        # --- Handle bankruptcy after card effect ---
        if self.engine.game_over:
            self._show_game_over()
            return

        pl = self.engine.current_player
        if pl.cash < 0:
            self.refresh_all()
            self._handle_debt_or_continue()
        else:
            self.refresh_all(); self._sched_end(600)

    def _handle_debt_or_continue(self):
        """Check if player can avoid bankruptcy via mortgage. If not, declare bankruptcy."""
        pl = self.engine.current_player
        if pl.cash >= 0:
            self._sched_end(800)
            return

        # Player has negative cash — can they mortgage?
        mortgageable = self.engine.get_mortgageable(self.engine.current_player_idx)
        if mortgageable:
            self.engine.add_log(f"⚠ {pl.name}欠债¥{abs(pl.cash)}！必须抵押地产偿还！")
            self.refresh_all()
            # Open mortgage dialog; after close, re-check
            self.after(300, lambda: self._force_mortgage_then_check())
        else:
            # No properties to mortgage — bankruptcy!
            self.engine._bankrupt(pl)
            self._show_game_over()

    def _force_mortgage_then_check(self):
        """Open mortgage dialog. After close, re-check if debt is cleared."""
        pl = self.engine.current_player
        if pl.cash >= 0:
            self._sched_end(500); return

        mortgageable = self.engine.get_mortgageable(self.engine.current_player_idx)
        if not mortgageable:
            self.engine._bankrupt(pl)
            self._show_game_over()
            return

        # Open dialog as modal — player must mortgage
        dlg = MortgageDialog(self, self.engine, self.engine.current_player_idx,
                             on_close=lambda: self._after_forced_mortgage())
        dlg.title("⚠ 你必须抵押地产偿还债务！")
        dlg.grab_set()

    def _after_forced_mortgage(self):
        """After mortgage dialog closes, re-check cash."""
        self.refresh_all()
        pl = self.engine.current_player
        if pl.cash >= 0:
            self.engine.add_log(f"✅ {pl.name}已偿还债务，继续游戏"); self._sched_end(500)
        elif self.engine.get_mortgageable(self.engine.current_player_idx):
            self.engine.add_log(f"⚠ {pl.name}仍欠债¥{abs(pl.cash)}，需要继续抵押！")
            self._force_mortgage_then_check()
        else:
            self.engine._bankrupt(pl)
            self._show_game_over()

    def _show_game_over(self):
        """Show game-over UI."""
        self.audio.sfx_bankrupt()
        self.refresh_all()
        self.update()
        messagebox.showinfo("游戏结束",
                            f"💀 {self.engine.current_player.name}破产了！\n\n"
                            f"🏆 {self.engine.winner.name}获胜！")
        self.audio.sfx_win()

    def on_mortgage(self):
        self.audio.sfx_click()
        if self._animating: return
        if len(self.engine.current_player.properties)==0: messagebox.showinfo("提示","你没有地产可以抵押。",parent=self); return
        MortgageDialog(self,self.engine,self.engine.current_player_idx,on_close=lambda:self.refresh_all())

    def on_use_jail(self):
        self.audio.sfx_click(); pl=self.engine.current_player
        if pl.jail_free_cards<=0: return
        if not pl.skip_turn: messagebox.showinfo("提示","你当前不在监狱中。",parent=self); return
        self.engine.use_jail_free(self.engine.current_player_idx); self.audio.sfx_jail_free(); self.refresh_all()
        messagebox.showinfo("出狱成功",f"{pl.name}使用出狱免费卡，重获自由！",parent=self)

    def on_buy(self):
        if not self._can_buy or self.engine.game_over: return
        self.audio.sfx_click(); ok,msg=self.engine.buy_property()
        if ok: self.audio.sfx_buy(); self._can_buy=False; self.refresh_all(); self._sched_end(500)
        else: messagebox.showwarning("购买失败",msg,parent=self)

    def on_end_turn(self):
        if self._animating or self.engine.game_over: return
        self.audio.sfx_click()
        if self._can_buy: self.engine.add_log(f"{self.engine.current_player.name}选择不购买，结束回合"); self._can_buy=False
        if not self._can_roll: self._end_turn()

    def _end_turn(self):
        self._cancel()
        if self.engine.game_over: return
        self.engine.next_turn(); self._can_roll=True; self._can_buy=False; self._pending_card=False; self.refresh_all()

    def on_restart(self):
        if self._animating: return; self.audio.sfx_click()
        if messagebox.askyesno("重新开始","确定重新开始游戏吗？",parent=self):
            self._cancel(); self.engine.reset(); self._can_roll=True; self._can_buy=False
            self._animating=False; self._pending_card=False; self.panel._hide_card(); self.refresh_all(); self.audio.sfx_start()

    def on_rules(self):
        self.audio.sfx_click()
        rt="""\
╔══════════════════════════════════════╗
║   📖 双人大富翁 4K旗舰版 - 完整规则  ║
╚══════════════════════════════════════╝

🎯 目标: 让对手破产！

🎮 流程: 轮流掷骰子 → 移动 → 触发效果

🏠 地产 (32处)
━━━━━━━━━━━━━━━━━━━━━━━
• 走到空地可购买
• 对手走到你的地产 → 支付20%过路费
• 已抵押地产不收取过路费

🏚️ 抵押系统
━━━━━━━━━━━━━━━━━━━━━━━
• 抵押获地产价格50%现金
• 赎回需本金+10%利息
• 资金不足时可抵押避免破产

🃏 卡片系统
━━━━━━━━━━━━━━━━━━━━━━━
机遇卡(橙)第7/22格 | 命运卡(蓝)第12/36格

🔊 音量控制
━━━━━━━━━━━━━━━━━━━━━━━
• 右上角 🔊/🔇 一键静音
• 🎚️ 音量按钮调节BGM/音效
• 音量自动保存，下次启动生效

🎁 特殊格子
━━━━━━━━━━━━━━━━━━━━━━━
🟢起点(+200) 🔒监狱(暂停) 🅿️免费停车
🔴破产(-150) 🃏机遇卡 📦命运卡
"""
        d=tk.Toplevel(self); d.title("游戏规则"); d.configure(bg="#FFF8E1")
        dw,dh=850,800
        d.geometry(f"{dw}x{dh}+{(self.winfo_screenwidth()-dw)//2}+{(self.winfo_screenheight()-dh)//2}")
        d.resizable(False,False); d.transient(self); d.grab_set()
        tk.Label(d,text="📖 双人大富翁 4K旗舰版",font=F_RULES_TITLE,bg="#FFF8E1",fg="#4E342E").pack(pady=15)
        tw=ScrolledText(d,font=F_RULES_BODY,bg="#FFFDE7",fg="#333333",wrap=tk.WORD,width=60,height=28)
        tw.pack(fill="both",expand=True,padx=30,pady=(0,20)); tw.insert("1.0",rt); tw.configure(state="disabled")
        tk.Button(d,text="我知道了",font=F_BUTTON,fg="white",bg="#5D4037",bd=0,padx=40,pady=12,command=d.destroy).pack(pady=(0,20))

    def refresh_all(self): self.board_c.update_display(); self.panel.update_display(); self._upd_btns()


def main():
    app=RichManApp(); app.mainloop()

if __name__=="__main__":
    main()
