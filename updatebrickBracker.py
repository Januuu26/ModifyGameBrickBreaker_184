import math
import random
import tkinter as tk

WIDTH, HEIGHT = 640, 480
FRAME_MS = 16                 # ~60 FPS
PADDLE_Y = HEIGHT - 50
PADDLE_SPEED = 9
BG = '#12122b'
FONT = 'Helvetica'


class GameObject:
    def __init__(self, canvas, item):
        self.canvas = canvas
        self.item = item
 
    def get_position(self):
        return self.canvas.coords(self.item)
 
    def move(self, x, y):
        self.canvas.move(self.item, x, y)
 
    def delete(self):
        self.canvas.delete(self.item)
 
 
class Ball(GameObject):
    def __init__(self, canvas, x, y, speed, vx=0.0, vy=None):
        self.radius = 8
        self.vx = vx
        self.vy = -speed if vy is None else vy
        item = canvas.create_oval(x - self.radius, y - self.radius,
                                  x + self.radius, y + self.radius,
                                  fill='white', outline='')
        super().__init__(canvas, item)
 
    def center(self):
        x1, y1, x2, y2 = self.get_position()
        return (x1 + x2) / 2, (y1 + y2) / 2
 
    def place(self, x, y):
        r = self.radius
        self.canvas.coords(self.item, x - r, y - r, x + r, y + r)
 
    def speed(self):
        return math.hypot(self.vx, self.vy)
 
    def set_speed(self, new_speed):
        cur = self.speed() or 1
        k = new_speed / cur
        self.vx *= k
        self.vy *= k
 
    def rotate(self, angle):
        c, s = math.cos(angle), math.sin(angle)
        self.vx, self.vy = self.vx * c - self.vy * s, self.vx * s + self.vy * c
 
    def update(self):
        self.move(self.vx, self.vy)
        x1, y1, x2, y2 = self.get_position()
        if x1 < 0:
            self.move(-x1, 0)
            self.vx = abs(self.vx)
        elif x2 > WIDTH:
            self.move(WIDTH - x2, 0)
            self.vx = -abs(self.vx)
        if y1 < 0:
            self.move(0, -y1)
            self.vy = abs(self.vy)
 
 
class Paddle(GameObject):
    NORMAL_WIDTH = 90
    WIDE_WIDTH = 140
 
    def __init__(self, canvas, x, y):
        self.width = self.NORMAL_WIDTH
        self.height = 12
        self.y = y
        item = canvas.create_rectangle(0, 0, 1, 1, fill='#f1c40f', outline='')
        super().__init__(canvas, item)
        self.move_to(x)
 
    @property
    def center_x(self):
        x1, _, x2, _ = self.get_position()
        return (x1 + x2) / 2
 
    def move_to(self, cx):
        half = self.width / 2
        cx = max(half, min(WIDTH - half, cx))
        self.canvas.coords(self.item, cx - half, self.y - self.height / 2,
                           cx + half, self.y + self.height / 2)
 
    def move_by(self, dx):
        self.move_to(self.center_x + dx)
 
    def set_width(self, width):
        cx = self.center_x
        self.width = width
        self.move_to(cx)
 
 
class Brick(GameObject):
    COLORS = {1: '#e74c3c', 2: '#3498db', 3: '#8e44ad'}
    WIDTH = 70
    HEIGHT = 18
 
    def __init__(self, canvas, x, y, hits):
        self.hits = hits
        self.points = 10 * hits
        item = canvas.create_rectangle(x - self.WIDTH / 2, y - self.HEIGHT / 2,
                                       x + self.WIDTH / 2, y + self.HEIGHT / 2,
                                       fill=Brick.COLORS[hits],
                                       outline='#ffffff', width=1)
        super().__init__(canvas, item)
 
    @property
    def color(self):
        return Brick.COLORS[max(self.hits, 1)]
 
    def hit(self):
        """Return True if the brick was destroyed."""
        self.hits -= 1
        if self.hits <= 0:
            self.delete()
            return True
        self.canvas.itemconfig(self.item, fill=Brick.COLORS[self.hits])
        return False
 
 
class PowerUp(GameObject):
    KINDS = {
        'W': ('#2ecc71', 'W'),   # paddle lebar
        'S': ('#f1c40f', 'S'),   # bola pelan
        'M': ('#9b59b6', 'M'),   # multi-ball
        'L': ('#e74c3c', '♥'),   # nyawa tambahan
    }
 
    def __init__(self, canvas, x, y, kind):
        self.kind = kind
        color, label = PowerUp.KINDS[kind]
        item = canvas.create_rectangle(x - 18, y - 9, x + 18, y + 9,
                                       fill=color, outline='white')
        self.label = canvas.create_text(x, y, text=label, fill='white',
                                        font=(FONT, 10, 'bold'))
        super().__init__(canvas, item)
 
    def move(self, x, y):
        super().move(x, y)
        self.canvas.move(self.label, x, y)
 
    def delete(self):
        super().delete()
        self.canvas.delete(self.label)
 
 
class Game(tk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, width=WIDTH, height=HEIGHT, bg=BG,
                                highlightthickness=0)
        self.canvas.pack()
        self.pack()
 
        self.high_score = 0
        self.keys = set()
        self.pending = None
        self.msg_items = []
 
        master.bind('<KeyPress>', self.on_key_press)
        master.bind('<KeyRelease>', lambda e: self.keys.discard(e.keysym))
        self.canvas.bind('<Motion>', self.on_mouse)
        self.canvas.bind('<Button-1>', lambda e: self.action())
 
        self.new_game()
        self.loop()
 
   