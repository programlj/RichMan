# -*- coding: utf-8 -*-
"""
双人大富翁 - Two-Player Monopoly Game
专门适配 Windows 3024×2056 高分辨率屏幕
窗口 2400×1600，UI 元素 2.5 倍缩放
"""

import ctypes

# ============ Windows High DPI Awareness ============
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor DPI (Windows 8.1+)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()   # System DPI (Windows Vista+)
    except Exception:
        pass

import tkinter as tk
from tkinter import messagebox
from tkinter.scrolledtext import ScrolledText
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple


# ==================== Constants ====================

# Window dimensions
WINDOW_WIDTH = 2400
WINDOW_HEIGHT = 1600

# Board layout
CELL_SIZE = 120          # Each cell is 120×120 px
GRID_SIZE = 11           # 11×11 grid → 40 perimeter cells + inner area
BOARD_SIZE = CELL_SIZE * GRID_SIZE  # 1320 px

# Content centering: board(1320) + gap(40) + panel(600) = 1960
# Left margin = (2400 - 1960) / 2 = 220
BOARD_X = 220            # Board canvas left edge in content frame
BOARD_Y = 15             # Board canvas top edge in content frame
PANEL_X = 1580           # Right panel left edge (220 + 1320 + 40)
PANEL_Y = 15
PANEL_WIDTH = 600
PANEL_HEIGHT = 1320

# Player colors
PLAYER1_COLOR = "#1E88E5"      # Blue
PLAYER2_COLOR = "#E53935"      # Red
PLAYER1_LIGHT = "#BBDEFB"      # Light blue (owned property bg)
PLAYER2_LIGHT = "#FFCDD2"      # Light red (owned property bg)

# Board colors
BOARD_BG = "#F5F5DC"           # Beige / cream
BOARD_BORDER = "#8B4513"       # Saddle brown
CELL_BG_DEFAULT = "#FFF8DC"    # Cornsilk (default cell)
CELL_BG_START = "#A5D6A7"      # Green
CELL_BG_JAIL = "#FFCC80"       # Orange
CELL_BG_PARKING = "#E0E0E0"    # Gray
CELL_BG_BANKRUPTCY = "#EF9A9A"  # Light red
CENTER_BG = "#FFF9E6"          # Inner board area

# Button colors
BTN_ROLL = "#FF9800"           # Orange
BTN_BUY = "#4CAF50"            # Green
BTN_END = "#2196F3"            # Blue
BTN_RESTART = "#9E9E9E"        # Gray
BTN_RULES = "#795548"          # Brown

# Fonts (scaled ×2.5 for high DPI)
FONT_TITLE = ("Microsoft YaHei", 32, "bold")
FONT_SUBTITLE = ("Microsoft YaHei", 20, "bold")
FONT_PLAYER = ("Microsoft YaHei", 22, "bold")
FONT_PLAYER_INFO = ("Microsoft YaHei", 18)
FONT_PLAYER_SMALL = ("Microsoft YaHei", 16)
FONT_NORMAL = ("Microsoft YaHei", 18)
FONT_BUTTON = ("Microsoft YaHei", 18, "bold")
FONT_CELL_NAME = ("Microsoft YaHei", 13, "bold")
FONT_CELL_PRICE = ("Microsoft YaHei", 11)
FONT_STATUS = ("Microsoft YaHei", 20, "bold")
FONT_LOG = ("Consolas", 14)
FONT_RULES_TITLE = ("Microsoft YaHei", 22, "bold")
FONT_RULES_BODY = ("Microsoft YaHei", 16)
FONT_CENTER_TITLE = ("Microsoft YaHei", 42, "bold")
FONT_CENTER_SUB = ("Microsoft YaHei", 24, "italic")
FONT_DICE_NUM = ("Microsoft YaHei", 60, "bold")

# Player piece
PIECE_SIZE = 40
PIECE_OFFSET = 18  # Offset from cell center for player 1; player 2 offset opposite

# Starting cash
INITIAL_CASH = 1500


# ==================== Enums & Data Classes ====================

class CellType(Enum):
    START = "start"
    PROPERTY = "property"
    JAIL = "jail"
    FREE_PARKING = "free_parking"
    BANKRUPTCY = "bankruptcy"


@dataclass
class BoardCell:
    """Represents one cell on the board."""
    name: str
    price: int
    cell_type: CellType
    row: int          # Grid row (0-10)
    col: int          # Grid column (0-10)
    owner: Optional[int] = None   # None = no owner, 0 = player1, 1 = player2


@dataclass
class Player:
    """Represents a player."""
    name: str
    color: str
    light_color: str
    cash: int = INITIAL_CASH
    position: int = 0           # Board position 0-39
    properties: List[int] = field(default_factory=list)
    skip_turn: bool = False     # Set when landing on jail; skip next turn


# ==================== Game Engine ====================

class GameEngine:
    """Pure game logic, independent of UI."""

    PROPERTY_DEFS = {
        # Bottom row (positions 1-9)
        1: ("村庄", 60),    2: ("农田", 60),    3: ("果园", 80),
        4: ("渔村", 80),    5: ("牧场", 100),   6: ("林场", 100),
        7: ("矿场", 100),   8: ("集市", 100),   9: ("小商店", 120),
        # Right column (positions 11-19)
        11: ("面包店", 120), 12: ("咖啡馆", 140), 13: ("书店", 140),
        14: ("花店", 160),   15: ("服装店", 160), 16: ("药店", 180),
        17: ("小餐馆", 180), 18: ("电影院", 200), 19: ("健身房", 200),
        # Top row (positions 21-29)
        21: ("超市", 200),   22: ("公寓", 220),   23: ("医院", 220),
        24: ("学校", 240),   25: ("餐厅", 240),   26: ("商场", 260),
        27: ("写字楼", 260), 28: ("体育馆", 280), 29: ("剧院", 280),
        # Left column (positions 31-39)
        31: ("博物馆", 280), 32: ("图书馆", 280), 33: ("游泳馆", 300),
        34: ("大酒店", 300), 35: ("银行", 320),   36: ("机场", 350),
        37: ("游乐园", 380), 38: ("摩天大楼", 400), 39: ("宫殿", 400),
    }

    CORNER_DEFS = {
        0:  ("起点", CellType.START),
        10: ("破产", CellType.BANKRUPTCY),
        20: ("免费停车", CellType.FREE_PARKING),
        30: ("监狱", CellType.JAIL),
    }

    def __init__(self):
        self.players: List[Player] = []
        self.board: List[BoardCell] = []
        self.current_player_idx: int = 0
        self.dice1: int = 0
        self.dice2: int = 0
        self.log: List[str] = []
        self.game_over: bool = False
        self.winner: Optional[Player] = None
        self._init_board()
        self._init_players()

    def _init_board(self):
        """Initialize the 40-cell board."""
        self.board = []
        for pos in range(40):
            row, col = self._pos_to_grid(pos)
            if pos in self.CORNER_DEFS:
                name, cell_type = self.CORNER_DEFS[pos]
                price = 0
            else:
                name, price = self.PROPERTY_DEFS.get(pos, ("未知", 0))
                cell_type = CellType.PROPERTY
            self.board.append(BoardCell(
                name=name, price=price, cell_type=cell_type,
                row=row, col=col
            ))

    def _init_players(self):
        """Initialize two players."""
        self.players = [
            Player(name="玩家 1", color=PLAYER1_COLOR, light_color=PLAYER1_LIGHT),
            Player(name="玩家 2", color=PLAYER2_COLOR, light_color=PLAYER2_LIGHT),
        ]
        self.current_player_idx = 0
        self.game_over = False
        self.winner = None

    @staticmethod
    def _pos_to_grid(pos: int) -> Tuple[int, int]:
        """Convert board position (0-39) to grid coordinates (row, col)."""
        if pos <= 10:
            return (10, pos)              # Bottom row, left→right
        elif pos <= 20:
            return (20 - pos, 10)         # Right column, bottom→top
        elif pos <= 30:
            return (0, 30 - pos)          # Top row, right→left
        else:
            return (pos - 30, 0)          # Left column, top→bottom

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def get_cell(self, pos: int) -> BoardCell:
        return self.board[pos]

    def roll_dice(self) -> Tuple[int, int]:
        """Roll two dice. Returns (dice1, dice2)."""
        self.dice1 = random.randint(1, 6)
        self.dice2 = random.randint(1, 6)
        self.add_log(f"{self.current_player.name} 掷出了 [{self.dice1}] 和 [{self.dice2}]，"
                     f"共 {self.dice1 + self.dice2} 点")
        return self.dice1, self.dice2

    def process_landing(self) -> str:
        """
        Process what happens when the current player lands on their cell.
        Returns a status string: 'start', 'jail', 'parking', 'bankrupt',
        'penalty', 'buyable', 'own', 'rent'.
        """
        player = self.current_player
        cell = self.get_cell(player.position)

        if cell.cell_type == CellType.START:
            player.cash += 200
            self.add_log(f"🎉 {player.name} 到达起点，获得 200 元奖励！")
            return "start"

        elif cell.cell_type == CellType.JAIL:
            player.skip_turn = True
            self.add_log(f"🔒 {player.name} 进入监狱，暂停一回合！")
            return "jail"

        elif cell.cell_type == CellType.FREE_PARKING:
            self.add_log(f"🅿️ {player.name} 在免费停车，什么都不做。")
            return "parking"

        elif cell.cell_type == CellType.BANKRUPTCY:
            penalty = 150
            player.cash -= penalty
            self.add_log(f"💸 {player.name} 走到破产格，缴纳 {penalty} 元罚金！")
            if player.cash < 0:
                self._declare_bankruptcy(player)
                return "bankrupt"
            return "penalty"

        elif cell.cell_type == CellType.PROPERTY:
            if cell.owner is None:
                return "buyable"
            elif cell.owner == self.current_player_idx:
                self.add_log(f"🏠 这是 {player.name} 自己的地产。")
                return "own"
            else:
                rent = max(1, int(cell.price * 0.1))
                player.cash -= rent
                owner_player = self.players[cell.owner]
                owner_player.cash += rent
                self.add_log(f"💰 {player.name} 向 {owner_player.name} "
                             f"支付了 {rent} 元过路费！")
                if player.cash < 0:
                    self._declare_bankruptcy(player)
                    return "bankrupt"
                return "rent"

        return "unknown"

    def buy_property(self) -> Tuple[bool, str]:
        """
        Current player attempts to buy the property they're standing on.
        Returns (success, message).
        """
        player = self.current_player
        cell = self.get_cell(player.position)

        if cell.cell_type != CellType.PROPERTY:
            return False, "当前位置不是地产，无法购买。"
        if cell.owner is not None:
            return False, "该地产已被购买。"
        if player.cash < cell.price:
            return False, f"现金不足！需要 {cell.price} 元，你只有 {player.cash} 元。"

        player.cash -= cell.price
        cell.owner = self.current_player_idx
        player.properties.append(player.position)
        self.add_log(f"🏠 {player.name} 购买了 {cell.name}，花费 {cell.price} 元！")
        return True, f"成功购买 {cell.name}！"

    def _declare_bankruptcy(self, player: Player):
        """Declare a player bankrupt."""
        self.game_over = True
        self.winner = self.players[1 - self.players.index(player)]
        self.add_log(f"💀 {player.name} 破产了！{self.winner.name} 获胜！🎉")

    def next_turn(self):
        """Advance to the next player's turn."""
        self.current_player_idx = 1 - self.current_player_idx
        self.dice1 = 0
        self.dice2 = 0
        if not self.game_over:
            self.add_log(f"➡️ 轮到 {self.current_player.name} 行动")

    def check_jail_skip(self) -> bool:
        """Check if current player should skip their turn due to jail.
        Returns True if turn was skipped."""
        player = self.current_player
        if player.skip_turn:
            player.skip_turn = False
            self.add_log(f"🔒 {player.name} 在监狱中，本回合跳过！")
            return True
        return False

    def reset(self):
        """Reset the entire game."""
        self._init_board()
        self._init_players()
        self.log.clear()
        self.dice1 = 0
        self.dice2 = 0
        self.add_log("🎮 游戏开始！双人大富翁！")
        self.add_log(f"➡️ 轮到 {self.current_player.name} 行动")

    def add_log(self, message: str):
        """Add a message to the game log."""
        self.log.append(message)

    def get_total_property_value(self, player_idx: int) -> int:
        """Get total value of a player's properties."""
        player = self.players[player_idx]
        return sum(self.board[p].price for p in player.properties)


# ==================== Board Canvas ====================

class BoardCanvas(tk.Canvas):
    """Canvas widget that draws the game board."""

    def __init__(self, parent, engine: GameEngine, **kwargs):
        super().__init__(parent, width=BOARD_SIZE, height=BOARD_SIZE,
                         bg="#2C1810", highlightthickness=0, **kwargs)
        self.engine = engine
        self.piece_ids: dict = {}
        self.cell_rects: dict = {}
        self.dice1_text: int = 0
        self.dice2_text: int = 0

        self._draw_all()

    def _draw_all(self):
        """Full initial draw."""
        self._draw_board()
        self._draw_center()
        self._draw_pieces()

    def _draw_board(self):
        """Draw all 40 cells on the board."""
        for pos in range(40):
            cell = self.engine.get_cell(pos)
            self._draw_cell(cell, pos)

    def _draw_cell(self, cell: BoardCell, pos: int):
        """Draw a single cell."""
        x1 = cell.col * CELL_SIZE
        y1 = cell.row * CELL_SIZE
        x2 = x1 + CELL_SIZE
        y2 = y1 + CELL_SIZE

        # Fill color
        if cell.owner is not None:
            fill = self.engine.players[cell.owner].light_color
        elif cell.cell_type == CellType.START:
            fill = CELL_BG_START
        elif cell.cell_type == CellType.JAIL:
            fill = CELL_BG_JAIL
        elif cell.cell_type == CellType.FREE_PARKING:
            fill = CELL_BG_PARKING
        elif cell.cell_type == CellType.BANKRUPTCY:
            fill = CELL_BG_BANKRUPTCY
        else:
            fill = CELL_BG_DEFAULT

        # Background rect
        rect_id = self.create_rectangle(
            x1 + 1, y1 + 1, x2 - 1, y2 - 1,
            fill=fill, outline=BOARD_BORDER, width=2, tags="cell"
        )
        self.cell_rects[pos] = rect_id

        # Owner strip
        if cell.owner is not None:
            owner_color = self.engine.players[cell.owner].color
            self.create_rectangle(
                x1 + 1, y1 + 1, x2 - 1, y1 + 8,
                fill=owner_color, outline="", tags="cell"
            )

        # Cell name
        cx = x1 + CELL_SIZE // 2
        name_y = y1 + CELL_SIZE // 2 - 14
        self.create_text(cx, name_y, text=cell.name,
                         font=FONT_CELL_NAME, fill="#333333", tags="cell")

        # Price or corner label
        price_y = y1 + CELL_SIZE // 2 + 14
        if cell.cell_type == CellType.PROPERTY:
            self.create_text(cx, price_y, text=f"¥{cell.price}",
                             font=FONT_CELL_PRICE, fill="#666666", tags="cell")
        elif cell.cell_type == CellType.START:
            self.create_text(cx, price_y, text="← 出发",
                             font=FONT_CELL_PRICE, fill="#2E7D32", tags="cell")
        elif cell.cell_type == CellType.JAIL:
            self.create_text(cx, price_y, text="暂停一回合",
                             font=FONT_CELL_PRICE, fill="#E65100", tags="cell")
        elif cell.cell_type == CellType.FREE_PARKING:
            self.create_text(cx, price_y, text="休息一下",
                             font=FONT_CELL_PRICE, fill="#616161", tags="cell")
        elif cell.cell_type == CellType.BANKRUPTCY:
            self.create_text(cx, price_y, text="罚金 ¥150",
                             font=FONT_CELL_PRICE, fill="#C62828", tags="cell")

    def _draw_center(self):
        """Draw the inner 9×9 area with title and dice display."""
        ix1 = 1 * CELL_SIZE + 2
        iy1 = 1 * CELL_SIZE + 2
        ix2 = 10 * CELL_SIZE - 2
        iy2 = 10 * CELL_SIZE - 2

        # Background
        self.create_rectangle(ix1, iy1, ix2, iy2,
                              fill=CENTER_BG, outline=BOARD_BORDER,
                              width=3, tags="center")

        cx = ix1 + (ix2 - ix1) // 2
        cy_top = iy1 + 160

        # Title
        self.create_text(cx, cy_top - 60, text="🎲 双人大富翁 🎲",
                         font=FONT_CENTER_TITLE, fill="#8B4513", tags="center")
        self.create_text(cx, cy_top, text="Two-Player Monopoly",
                         font=FONT_CENTER_SUB, fill="#A0826D", tags="center")

        # Dice section
        dice_y = cy_top + 80
        self.create_rectangle(cx - 180, dice_y, cx + 180, dice_y + 260,
                              fill="#F5F5DC", outline="#8B4513",
                              width=2, tags="center")
        self.create_text(cx, dice_y + 30, text="🎯 骰子",
                         font=("Microsoft YaHei", 20, "bold"),
                         fill="#8B4513", tags="center")

        # Dice boxes
        self.create_rectangle(cx - 130, dice_y + 60, cx - 10, dice_y + 200,
                              outline="#8B4513", width=3, tags="center")
        self.create_rectangle(cx + 10, dice_y + 60, cx + 130, dice_y + 200,
                              outline="#8B4513", width=3, tags="center")

        # Dice value texts
        self.dice1_text = self.create_text(
            cx - 70, dice_y + 130, text="?",
            font=FONT_DICE_NUM, fill="#999999", tags="center"
        )
        self.dice2_text = self.create_text(
            cx + 70, dice_y + 130, text="?",
            font=FONT_DICE_NUM, fill="#999999", tags="center"
        )

        # Total label
        self.total_text = self.create_text(
            cx, dice_y + 245, text="",
            font=("Microsoft YaHei", 22, "bold"), fill="#8B4513", tags="center"
        )

    def _draw_pieces(self):
        """Draw player pieces on the board."""
        for idx, player in enumerate(self.engine.players):
            self._draw_piece(idx, player)

    def _draw_piece(self, player_idx: int, player: Player):
        """Draw a single player piece."""
        cell = self.engine.get_cell(player.position)
        cx = cell.col * CELL_SIZE + CELL_SIZE // 2
        cy = cell.row * CELL_SIZE + CELL_SIZE // 2

        # Offset for side-by-side display
        if player_idx == 0:
            px = cx - PIECE_OFFSET
            py = cy - PIECE_OFFSET
        else:
            px = cx + PIECE_OFFSET - PIECE_SIZE
            py = cy + PIECE_OFFSET - PIECE_SIZE

        # Delete old piece
        if player_idx in self.piece_ids:
            self.delete(self.piece_ids[player_idx])

        # Draw circle
        piece_id = self.create_oval(
            px, py, px + PIECE_SIZE, py + PIECE_SIZE,
            fill=player.color, outline="white", width=3, tags="piece"
        )
        self.create_text(
            px + PIECE_SIZE // 2, py + PIECE_SIZE // 2,
            text=str(player_idx + 1),
            font=("Microsoft YaHei", 18, "bold"),
            fill="white", tags="piece"
        )
        self.piece_ids[player_idx] = piece_id

    def update_display(self):
        """Refresh the entire board display."""
        self.delete("cell")
        self.delete("piece")
        self.cell_rects.clear()

        for pos in range(40):
            cell = self.engine.get_cell(pos)
            self._draw_cell(cell, pos)

        self._update_dice()
        self.piece_ids.clear()
        self._draw_pieces()
        self.tag_raise("piece")

    def _update_dice(self):
        """Update dice values in center area."""
        if self.engine.dice1 > 0:
            self.itemconfig(self.dice1_text, text=str(self.engine.dice1),
                            fill="#333333")
            self.itemconfig(self.dice2_text, text=str(self.engine.dice2),
                            fill="#333333")
            total = self.engine.dice1 + self.engine.dice2
            self.itemconfig(self.total_text, text=f"合计: {total} 步")
        else:
            self.itemconfig(self.dice1_text, text="?", fill="#999999")
            self.itemconfig(self.dice2_text, text="?", fill="#999999")
            self.itemconfig(self.total_text, text="")

    def animate_move(self, from_pos: int, steps: int, on_complete: callable):
        """
        Animate player piece moving step by step.
        Calls on_complete when animation finishes.
        """
        positions = [(from_pos + i) % 40 for i in range(1, steps + 1)]

        def step_animate(idx: int):
            if idx >= len(positions):
                on_complete()
                return
            pos = positions[idx]
            self.engine.current_player.position = pos
            self.update_display()
            delay = 60 + idx * 5  # Gradual deceleration
            # Use default arg to capture idx value at creation time
            self.after(delay, lambda n=idx+1: step_animate(n))

        step_animate(0)


# ==================== Player Panel ====================

class PlayerPanel(tk.Frame):
    """Right-side panel showing player info and game log."""

    CARD_HEIGHT = 215      # Each player card height
    AVATAR_SIZE = 80       # Avatar canvas size
    CIRCLE_R = 32          # Avatar circle radius

    def __init__(self, parent, engine: GameEngine, **kwargs):
        super().__init__(parent, width=PANEL_WIDTH, height=PANEL_HEIGHT,
                         bg="#F5F0E8", **kwargs)
        self.engine = engine
        self.pack_propagate(False)

        # Widget refs for updates
        self.p1_frame: Optional[tk.Frame] = None
        self.p2_frame: Optional[tk.Frame] = None
        self.p1_cash: Optional[tk.Label] = None
        self.p2_cash: Optional[tk.Label] = None
        self.p1_prop: Optional[tk.Label] = None
        self.p2_prop: Optional[tk.Label] = None
        self.p1_pos: Optional[tk.Label] = None
        self.p2_pos: Optional[tk.Label] = None
        self.p1_status: Optional[tk.Label] = None
        self.p2_status: Optional[tk.Label] = None
        self.turn_label: Optional[tk.Label] = None
        self.log_text: Optional[ScrolledText] = None

        self._build()

    # ── Build ──────────────────────────────────────────────

    def _build(self):
        """Build all panel widgets."""
        # Panel title
        tk.Label(self, text="📋 玩家信息", font=FONT_SUBTITLE,
                 bg="#F5F0E8", fg="#5D4037").pack(pady=(12, 6))

        # Player 1 card
        self.p1_frame = self._make_card_frame()
        self.p1_frame.pack(fill="x", padx=18, pady=6)
        self._build_card_content(self.p1_frame, 0)

        # Player 2 card
        self.p2_frame = self._make_card_frame()
        self.p2_frame.pack(fill="x", padx=18, pady=6)
        self._build_card_content(self.p2_frame, 1)

        # Turn indicator
        self.turn_label = tk.Label(self, text="", font=FONT_STATUS,
                                    bg="#F5F0E8", fg="#5D4037")
        self.turn_label.pack(pady=4)

        # Separator
        tk.Frame(self, height=2, bg="#BDBDBD").pack(fill="x", padx=25, pady=4)

        # Log section
        log_header = tk.Frame(self, bg="#F5F0E8")
        log_header.pack(fill="x", padx=18, pady=(4, 2))
        tk.Label(log_header, text="📜 游戏日志", font=FONT_SUBTITLE,
                 bg="#F5F0E8", fg="#5D4037").pack(side="left")

        self.log_text = ScrolledText(self, font=FONT_LOG, bg="#FFFDE7",
                                      fg="#333333", wrap=tk.WORD,
                                      state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=18, pady=(0, 15))

    def _make_card_frame(self) -> tk.Frame:
        """Create a styled frame for a player card."""
        frame = tk.Frame(self, bg="white", bd=2, relief="solid",
                         highlightbackground="#BDBDBD", highlightthickness=1)
        frame.pack_propagate(False)
        frame.configure(height=self.CARD_HEIGHT)
        return frame

    def _build_card_content(self, frame: tk.Frame, player_idx: int):
        """Build the content of a player card using a clean horizontal layout."""
        player = self.engine.players[player_idx]
        card_w = PANEL_WIDTH - 36   # Card inner width

        # ── Left: Avatar ──
        avatar_size = self.AVATAR_SIZE
        avatar = tk.Canvas(frame, width=avatar_size, height=avatar_size,
                           bg="white", highlightthickness=0)
        avatar.place(x=18, y=(self.CARD_HEIGHT - avatar_size) // 2)

        r = self.CIRCLE_R
        cx_a = avatar_size // 2
        cy_a = avatar_size // 2
        avatar.create_oval(cx_a - r, cy_a - r, cx_a + r, cy_a + r,
                           fill=player.color, outline=player.color, width=2)
        # Highlight ring on avatar
        avatar.create_oval(cx_a - r + 2, cy_a - r + 2, cx_a + r - 2, cy_a + r - 2,
                           fill="", outline="#FFFFFF", width=1)
        avatar.create_text(cx_a, cy_a, text=str(player_idx + 1),
                           font=("Microsoft YaHei", 26, "bold"), fill="white")

        # ── Right: Info labels stacked vertically ──
        info_x = 130   # Start x for info text (well clear of avatar circle edge at ~90)
        line_h = 38    # Vertical spacing between lines

        # Name
        name_lbl = tk.Label(frame, text=player.name, font=FONT_PLAYER,
                            bg="white", fg=player.color, anchor="w")
        name_lbl.place(x=info_x, y=24, width=card_w - info_x - 15)

        # Cash
        cash_lbl = tk.Label(frame, text="", font=FONT_PLAYER_INFO,
                            bg="white", fg="#333333", anchor="w")
        cash_lbl.place(x=info_x, y=24 + line_h, width=card_w - info_x - 15)

        # Properties
        prop_lbl = tk.Label(frame, text="", font=FONT_PLAYER_SMALL,
                            bg="white", fg="#555555", anchor="w")
        prop_lbl.place(x=info_x, y=24 + line_h * 2, width=card_w - info_x - 15)

        # Position
        pos_lbl = tk.Label(frame, text="", font=FONT_PLAYER_SMALL,
                           bg="white", fg="#888888", anchor="w")
        pos_lbl.place(x=info_x, y=24 + line_h * 3, width=card_w - info_x - 15)

        # Jail/warning indicator (shown when relevant)
        status_lbl = tk.Label(frame, text="", font=("Microsoft YaHei", 15, "bold"),
                              bg="white", fg="#E65100", anchor="w")
        status_lbl.place(x=info_x, y=24 + line_h * 4, width=card_w - info_x - 15)

        # Store refs & set initial values
        if player_idx == 0:
            self.p1_cash = cash_lbl
            self.p1_prop = prop_lbl
            self.p1_pos = pos_lbl
            self.p1_status = status_lbl
        else:
            self.p2_cash = cash_lbl
            self.p2_prop = prop_lbl
            self.p2_pos = pos_lbl
            self.p2_status = status_lbl

        # Populate initial values
        self._set_card_values(player_idx, cash_lbl, prop_lbl, pos_lbl, status_lbl)

    # ── Update ─────────────────────────────────────────────

    def update_display(self):
        """Refresh all panel information."""
        self._update_card(0, self.p1_cash, self.p1_prop, self.p1_pos, self.p1_status)
        self._update_card(1, self.p2_cash, self.p2_prop, self.p2_pos, self.p2_status)

        # Highlight active player
        if self.engine.game_over:
            self.turn_label.config(
                text=f"🏆 {self.engine.winner.name} 获胜！游戏结束！",
                fg="#2E7D32")
            self.p1_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
            self.p2_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
        else:
            current = self.engine.current_player
            self.turn_label.config(text=f"🎯 当前行动: {current.name}", fg=current.color)
            if self.engine.current_player_idx == 0:
                self.p1_frame.configure(highlightbackground=PLAYER1_COLOR, highlightthickness=4)
                self.p2_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)
            else:
                self.p2_frame.configure(highlightbackground=PLAYER2_COLOR, highlightthickness=4)
                self.p1_frame.configure(highlightbackground="#BDBDBD", highlightthickness=1)

        self._update_log()

    def _set_card_values(self, idx: int, cash_lbl: tk.Label, prop_lbl: tk.Label,
                         pos_lbl: tk.Label, status_lbl: tk.Label):
        """Set initial / updated values on a player card."""
        player = self.engine.players[idx]
        cash_lbl.config(text=f"💰 现金: ¥{player.cash:,}")
        prop_val = self.engine.get_total_property_value(idx)
        prop_lbl.config(text=f"🏠 地产: {len(player.properties)} 处  (总价值 ¥{prop_val:,})")
        pos_lbl.config(text=f"📍 {self.engine.get_cell(player.position).name}")
        # Status line (jail / active)
        if player.skip_turn:
            status_lbl.config(text="⚠ 下回合暂停（监狱中）")
        else:
            status_lbl.config(text="")

    def _update_card(self, idx: int, cash_lbl: tk.Label, prop_lbl: tk.Label,
                     pos_lbl: tk.Label, status_lbl: tk.Label):
        """Update a single player card."""
        self._set_card_values(idx, cash_lbl, prop_lbl, pos_lbl, status_lbl)

    def _update_log(self):
        """Update game log text."""
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        for entry in self.engine.log[-60:]:
            self.log_text.insert(tk.END, entry + "\n")
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")


# ==================== Main Application ====================

class RichManApp(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()

        self.title("双人大富翁 - Two-Player Monopoly")
        self.configure(bg="#3E2723")

        # Set initial window size in tk coordinates
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.resizable(False, False)

        # Game engine
        self.engine = GameEngine()

        # UI state flags
        self._can_roll = True
        self._can_buy = False
        self._animating = False
        self._pending_end_id: Optional[str] = None  # after() ID for scheduled end-turn

        # Button references
        self._btn_widgets: dict = {}

        self._build_ui()
        self.engine.reset()
        self.refresh_all()

        # Center window on screen.
        # With PerMonitorV2 DPI awareness (manifest + ctypes call),
        # tkinter coordinates == physical pixels — simple math works.
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        actual_w = self.winfo_width()
        actual_h = self.winfo_height()

        # If window exceeds screen (DPI fallback), scale down
        if actual_w > screen_w:
            ratio = screen_w / actual_w
            fit_w = int(screen_w * 0.78)
            fit_h = int(actual_h * ratio * 0.82)
            self.geometry(f"{fit_w}x{fit_h}")
            self.update_idletasks()
            actual_w = self.winfo_width()
            actual_h = self.winfo_height()

        x = max(0, (screen_w - actual_w) // 2)
        y = max(0, (screen_h - actual_h) // 2)
        self.geometry(f"+{x}+{y}")

    # ======== UI Construction ========

    def _build_ui(self):
        """Build the complete UI layout."""

        # ---- Title Bar ----
        title_frame = tk.Frame(self, bg="#4E342E", height=65)
        title_frame.pack(fill="x", side="top")
        title_frame.pack_propagate(False)
        tk.Label(title_frame, text="🎲 双 人 大 富 翁 🎲",
                 font=FONT_TITLE, bg="#4E342E", fg="#FFCC80").pack(expand=True)

        # ---- Main Content Area ----
        content = tk.Frame(self, bg="#3E2723")
        content.pack(fill="both", expand=True, side="top")

        # Board canvas
        self.board_canvas = BoardCanvas(content, self.engine)
        self.board_canvas.place(x=BOARD_X, y=BOARD_Y)

        # Player panel
        self.player_panel = PlayerPanel(content, self.engine)
        self.player_panel.place(x=PANEL_X, y=PANEL_Y)

        # ---- Bottom Bar (status + buttons) ----
        bottom_frame = tk.Frame(self, bg="#3E2723", height=155)
        bottom_frame.pack(fill="x", side="bottom")
        bottom_frame.pack_propagate(False)

        # Status label
        self.status_label = tk.Label(bottom_frame, text="",
                                     font=FONT_STATUS, bg="#3E2723",
                                     fg="#FFCC80")
        self.status_label.pack(pady=(10, 4))

        # Button container
        btn_container = tk.Frame(bottom_frame, bg="#3E2723")
        btn_container.pack(expand=True)

        buttons_spec = [
            ("roll", "🎲 掷骰子", BTN_ROLL, self.on_roll),
            ("buy", "🏠 购买地产", BTN_BUY, self.on_buy),
            ("end", "⏭️ 结束回合", BTN_END, self.on_end_turn),
            ("restart", "🔄 重新开始", BTN_RESTART, self.on_restart),
            ("rules", "📖 规则说明", BTN_RULES, self.on_rules),
        ]

        for key, text, color, cmd in buttons_spec:
            btn = self._make_button(btn_container, text, color, cmd)
            btn.pack(side="left", padx=12)
            self._btn_widgets[key] = btn

    def _make_button(self, parent, text: str, color: str,
                     command: callable) -> tk.Button:
        """Create a styled button matching 200×80 target with padding."""
        btn = tk.Button(
            parent, text=text, font=FONT_BUTTON,
            fg="white", bg=color,
            activeforeground="white",
            activebackground=self._darken(color, 0.85),
            bd=0, padx=30, pady=20, cursor="hand2",
            command=command, width=12,
            disabledforeground="#CCCCCC",
        )
        # Hover effects (only when enabled)
        def on_enter(e, b=btn, c=color):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=self._lighten(c, 0.2))
        def on_leave(e, b=btn, c=color):
            if str(b.cget("state")) != "disabled":
                b.configure(bg=c)

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    # ======== Color Utilities ========

    @staticmethod
    def _lighten(hex_color: str, factor: float) -> str:
        """Lighten a hex color by factor (0-1)."""
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    @staticmethod
    def _darken(hex_color: str, factor: float) -> str:
        """Darken a hex color by factor (0-1)."""
        c = hex_color.lstrip('#')
        r, g, b = int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)
        return f"#{int(r*factor):02x}{int(g*factor):02x}{int(b*factor):02x}"

    # ======== Button State Management ========

    def _update_button_states(self):
        """Enable/disable buttons based on game state."""
        if self.engine.game_over:
            self._set_buttons(roll=False, buy=False, end=False,
                              restart=True, rules=True)
            self.status_label.config(text="🏆 游戏结束！点击「重新开始」再来一局")
        elif self._animating:
            self._set_buttons(roll=False, buy=False, end=False,
                              restart=False, rules=True)
            self.status_label.config(text="🎲 移动中...")
        elif self._can_roll:
            self._set_buttons(roll=True, buy=False, end=False,
                              restart=True, rules=True)
            self.status_label.config(
                text=f"🎯 {self.engine.current_player.name} 的回合，请掷骰子！")
        elif self._can_buy:
            self._set_buttons(roll=False, buy=True, end=True,
                              restart=True, rules=True)
            cell = self.engine.get_cell(self.engine.current_player.position)
            self.status_label.config(
                text=f"💡 可购买「{cell.name}」(¥{cell.price})，或点击结束回合")
        else:
            self._set_buttons(roll=False, buy=False, end=True,
                              restart=True, rules=True)
            self.status_label.config(text="点击「结束回合」继续")

    def _set_buttons(self, roll: bool, buy: bool, end: bool,
                     restart: bool, rules: bool):
        """Set button enabled/disabled states."""
        states = {
            "roll": tk.NORMAL if roll else tk.DISABLED,
            "buy": tk.NORMAL if buy else tk.DISABLED,
            "end": tk.NORMAL if end else tk.DISABLED,
            "restart": tk.NORMAL if restart else tk.DISABLED,
            "rules": tk.NORMAL if rules else tk.DISABLED,
        }
        for key, state in states.items():
            if key in self._btn_widgets:
                btn = self._btn_widgets[key]
                btn.configure(state=state)
                # Restore original color when enabled
                colors = {"roll": BTN_ROLL, "buy": BTN_BUY, "end": BTN_END,
                          "restart": BTN_RESTART, "rules": BTN_RULES}
                if state == tk.DISABLED:
                    btn.configure(bg="#666666")
                else:
                    btn.configure(bg=colors[key])

    # ======== End-Turn Scheduling ========

    def _schedule_end_turn(self, delay_ms: int):
        """Schedule _end_turn after delay, canceling any previous schedule."""
        self._cancel_pending_end()
        self._pending_end_id = self.after(delay_ms, self._end_turn_scheduled)

    def _cancel_pending_end(self):
        """Cancel any pending scheduled end-turn."""
        if self._pending_end_id is not None:
            self.after_cancel(self._pending_end_id)
            self._pending_end_id = None

    def _end_turn_scheduled(self):
        """Wrapper for scheduled end-turn that clears the pending ID."""
        self._pending_end_id = None
        self._end_turn()

    # ======== Button Handlers ========

    def on_roll(self):
        """Handle roll dice button click."""
        if not self._can_roll or self._animating or self.engine.game_over:
            return

        # Check jail skip
        if self.engine.check_jail_skip():
            self._can_roll = False
            self.refresh_all()
            self._schedule_end_turn(1000)
            return

        self._can_roll = False
        self._animating = True
        self._can_buy = False

        # Roll
        d1, d2 = self.engine.roll_dice()
        steps = d1 + d2
        from_pos = self.engine.current_player.position
        self.refresh_all()

        # Start animation after showing dice
        self.after(500, lambda: self.board_canvas.animate_move(
            from_pos, steps, on_complete=self._on_move_complete
        ))

    def _on_move_complete(self):
        """Called after movement animation finishes."""
        self._animating = False
        result = self.engine.process_landing()

        if self.engine.game_over:
            self.refresh_all()
            pname = self.engine.current_player.name
            wname = self.engine.winner.name
            self.update()  # Force UI update before messagebox
            messagebox.showinfo("游戏结束",
                                f"💀 {pname} 破产了！\n\n"
                                f"🏆 {wname} 获胜！")
            return

        if result == "buyable":
            self._can_buy = True
            self.engine.add_log("💡 你可以购买当前地产，或选择结束回合。")
        else:
            self._can_buy = False
            # Auto-end turn after delay for non-buyable cells
            self._schedule_end_turn(800)

        self.refresh_all()

    def on_buy(self):
        """Handle buy property button click."""
        if not self._can_buy or self.engine.game_over:
            return

        success, msg = self.engine.buy_property()
        if success:
            self._can_buy = False
            self.refresh_all()
            self._schedule_end_turn(500)
        else:
            messagebox.showwarning("购买失败", msg, parent=self)

    def on_end_turn(self):
        """Handle end turn button click."""
        if self._animating or self.engine.game_over:
            return

        if self._can_buy:
            # Choosing not to buy
            self.engine.add_log(
                f"{self.engine.current_player.name} 选择不购买，结束回合。")
            self._can_buy = False

        if not self._can_roll:
            self._end_turn()

    def _end_turn(self):
        """Internal: end current player's turn and advance."""
        self._cancel_pending_end()
        if self.engine.game_over:
            return
        self.engine.next_turn()
        self._can_roll = True
        self._can_buy = False
        self.refresh_all()

    def on_restart(self):
        """Handle restart button click."""
        if self._animating:
            return
        ok = messagebox.askyesno("重新开始",
                                 "确定要重新开始游戏吗？\n当前进度将丢失。",
                                 parent=self)
        if ok:
            self._cancel_pending_end()
            self.engine.reset()
            self._can_roll = True
            self._can_buy = False
            self._animating = False
            self.refresh_all()

    def on_rules(self):
        """Show game rules dialog."""
        rules_text = """\
╔══════════════════════════════════════════╗
║         📖 双人大富翁 - 游戏规则         ║
╚══════════════════════════════════════════╝

🎯 游戏目标
━━━━━━━━━━━━━━━━━━━━━━━━━━
让你的对手破产，成为最终赢家！

🎮 游戏流程
━━━━━━━━━━━━━━━━━━━━━━━━━━
1. 两名玩家轮流掷骰子行动
2. 点击「掷骰子」按钮，掷出两个骰子
3. 棋子按骰子点数之和移动对应步数
4. 根据停留的格子触发不同效果

🏠 地产与购买
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 走到空地时可以选择购买
• 点击「购买地产」按钮完成购买
• 购买后地产归你所有
• 对手走到你的地产需要支付过路费

💰 过路费
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 走到对手的地产需支付租金
• 租金 = 地产价格的 10%
• 租金不足导致现金<0则破产

🎁 特殊格子
━━━━━━━━━━━━━━━━━━━━━━━━━━
🟢 起点：到达获得 200 元奖励
🔒 监狱：暂停一回合
🅿️  免费停车：什么都不做
🔴 破产格：缴纳 150 元罚金

💀 破产条件
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 现金 < 0 时立即破产
• 对手自动获胜

💡 提示
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 合理安排资金，平衡购买与储备
• 购买更多地产可增加对手踩雷概率
• 游戏可随时点击「重新开始」
"""

        dialog = tk.Toplevel(self)
        dialog.title("游戏规则说明")
        dialog.configure(bg="#FFF8E1")

        dw, dh = 750, 780
        sx = (self.winfo_screenwidth() - dw) // 2
        sy = (self.winfo_screenheight() - dh) // 2
        dialog.geometry(f"{dw}x{dh}+{sx}+{sy}")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(dialog, text="📖 双人大富翁 - 游戏规则",
                 font=FONT_RULES_TITLE, bg="#FFF8E1", fg="#5D4037").pack(pady=15)

        text_widget = ScrolledText(dialog, font=FONT_RULES_BODY,
                                    bg="#FFFDE7", fg="#333333",
                                    wrap=tk.WORD, width=65, height=26)
        text_widget.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        text_widget.insert("1.0", rules_text)
        text_widget.configure(state="disabled")

        tk.Button(dialog, text="我知道了", font=FONT_BUTTON,
                  fg="white", bg="#795548", bd=0,
                  padx=40, pady=12, cursor="hand2",
                  command=dialog.destroy).pack(pady=(0, 20))

    # ======== Main Refresh ========

    def refresh_all(self):
        """Refresh the entire UI."""
        self.board_canvas.update_display()
        self.player_panel.update_display()
        self._update_button_states()


# ==================== Main Entry Point ====================

def main():
    """Launch the game."""
    app = RichManApp()
    app.mainloop()


if __name__ == "__main__":
    main()
