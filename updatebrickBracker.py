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
 
   # ---------- setup ----------
    def new_game(self):
        if self.pending is not None:
            self.after_cancel(self.pending)
            self.pending = None
        self.canvas.delete('all')
        self.msg_items = []
        self.draw_background()
 
        self.score = 0
        self.lives = 3
        self.level = 1
        self.balls = []
        self.bricks = []
        self.powerups = []
        self.particles = []
        self.effects = {}
        self.state = 'ready'
 
        self.paddle = Paddle(self.canvas, WIDTH / 2, PADDLE_Y)
        self.hud_score = self.canvas.create_text(10, 14, anchor='w', fill='white',
                                                 font=(FONT, 12, 'bold'))
        self.hud_level = self.canvas.create_text(WIDTH / 2, 14, fill='white',
                                                 font=(FONT, 12, 'bold'))
        self.hud_lives = self.canvas.create_text(WIDTH - 10, 14, anchor='e',
                                                 fill='#ff6b81',
                                                 font=(FONT, 12, 'bold'))
        self.start_level()
 
    def draw_background(self):
        rnd = random.Random(7)
        for _ in range(60):
            x, y = rnd.randint(0, WIDTH), rnd.randint(0, HEIGHT)
            c = rnd.choice(['#2b2b55', '#3a3a70', '#4a4a88'])
            self.canvas.create_oval(x, y, x + 2, y + 2, fill=c, outline='')
 
    def base_speed(self):
        return min(5.0 + 0.5 * (self.level - 1), 9.0)
 
    def current_speed(self):
        return self.base_speed() * (0.7 if 'slow' in self.effects else 1.0)
 
    def start_level(self):
        for b in self.balls:
            b.delete()
        for p in self.powerups:
            p.delete()
        self.balls, self.powerups = [], []
        self.effects = {}
        self.paddle.set_width(Paddle.NORMAL_WIDTH)
        self.build_bricks()
        self.spawn_ball_on_paddle()
        self.state = 'ready'
        self.show_message(f'Level {self.level}',
                          'Spasi / klik = luncurkan   |   ← → / mouse = gerak   |   P = jeda   |   R = ulang')
        self.update_hud()
 
    def build_bricks(self):
        cols = 8
        rows = min(4 + self.level, 8)
        pattern = (self.level - 1) % 4
        for r in range(rows):
            if pattern == 3 and r % 2 == 1:           # garis-garis
                continue
            for c in range(cols):
                if pattern == 1 and (r + c) % 2:      # papan catur
                    continue
                if pattern == 2 and abs(c - 3.5) > 1.5 + r * 0.5:   # segitiga
                    continue
                if self.level >= 3 and r == 0:
                    hits = 3
                elif r < 2:
                    hits = 2
                else:
                    hits = 1
                x = 20 + c * 75 + 37.5
                y = 60 + r * 24
                self.bricks.append(Brick(self.canvas, x, y, hits))
 
    def spawn_ball_on_paddle(self):
        ball = Ball(self.canvas, self.paddle.center_x,
                    PADDLE_Y - self.paddle.height / 2 - 8, self.current_speed())
        self.balls.append(ball)

# ---------- UI helpers ----------
    def show_message(self, title, sub=''):
        self.clear_message()
        self.msg_items.append(self.canvas.create_text(
            WIDTH / 2, HEIGHT / 2 + 30, text=title, fill='white',
            font=(FONT, 32, 'bold')))
        if sub:
            self.msg_items.append(self.canvas.create_text(
                WIDTH / 2, HEIGHT / 2 + 75, text=sub, fill='#bbbbdd',
                font=(FONT, 11)))
 
    def clear_message(self):
        for i in self.msg_items:
            self.canvas.delete(i)
        self.msg_items = []
 
    def update_hud(self):
        self.canvas.itemconfig(
            self.hud_score, text=f'Skor: {self.score}   Rekor: {self.high_score}')
        self.canvas.itemconfig(self.hud_level, text=f'Level {self.level}')
        self.canvas.itemconfig(self.hud_lives, text='♥ ' * self.lives)
 # ---------- input ----------
    def on_key_press(self, e):
        k = e.keysym
        self.keys.add(k)
        if k == 'space':
            self.action()
        elif k in ('p', 'P'):
            self.toggle_pause()
        elif k in ('r', 'R'):
            self.new_game()
 
    def on_mouse(self, e):
        if self.state in ('ready', 'playing'):
            self.paddle.move_to(e.x)
 
    def action(self):
        if self.state == 'ready':
            self.launch()
        elif self.state == 'over':
            self.new_game()
 
    def launch(self):
        ball = self.balls[0]
        angle = math.radians(random.uniform(-25, 25))
        speed = self.current_speed()
        ball.vx = speed * math.sin(angle)
        ball.vy = -speed * math.cos(angle)
        self.state = 'playing'
        self.clear_message()
 
    def toggle_pause(self):
        if self.state == 'playing':
            self.state = 'paused'
            self.show_message('Jeda', 'Tekan P untuk lanjut')
        elif self.state == 'paused':
            self.state = 'playing'
            self.clear_message()
 # ---------- main loop ----------
    def loop(self):
        if self.state != 'paused':
            self.step()
        self.after(FRAME_MS, self.loop)
 
    def step(self):
        if self.state in ('ready', 'playing'):
            dx = 0
            if self.keys & {'Left', 'a', 'A'}:
                dx -= PADDLE_SPEED
            if self.keys & {'Right', 'd', 'D'}:
                dx += PADDLE_SPEED
            if dx:
                self.paddle.move_by(dx)
 
        self.update_particles()
 
        if self.state == 'ready':
            if self.balls:
                self.balls[0].place(self.paddle.center_x,
                                    PADDLE_Y - self.paddle.height / 2 - 8)
        elif self.state == 'playing':
            self.update_effects()
            self.update_balls()
            self.update_powerups()
 
    def update_balls(self):
        for ball in self.balls[:]:
            ball.update()
            self.collide_paddle(ball)
            if self.state == 'playing':
                self.collide_bricks(ball)
            if self.state != 'playing':
                return
            if ball.get_position()[1] > HEIGHT:
                ball.delete()
                self.balls.remove(ball)
        if self.state == 'playing' and not self.balls:
            self.lose_life()
 
    def collide_paddle(self, ball):
        px1, py1, px2, py2 = self.paddle.get_position()
        cx, cy = ball.center()
        r = ball.radius
        if (ball.vy > 0 and cy + r >= py1 and cy <= py2
                and px1 - r <= cx <= px2 + r):
            offset = (cx - (px1 + px2) / 2) / ((px2 - px1) / 2)
            offset = max(-1.0, min(1.0, offset))
            angle = offset * math.radians(65)
            speed = ball.speed()
            ball.vx = speed * math.sin(angle)
            ball.vy = -speed * math.cos(angle)
            ball.move(0, py1 - (cy + r))
 
    def collide_bricks(self, ball):
        cx, cy = ball.center()
        r = ball.radius
        for brick in self.bricks:
            x1, y1, x2, y2 = brick.get_position()
            nx = max(x1, min(cx, x2))
            ny = max(y1, min(cy, y2))
            if (cx - nx) ** 2 + (cy - ny) ** 2 > r * r:
                continue
            overlap_x = min(cx + r - x1, x2 - (cx - r))
            overlap_y = min(cy + r - y1, y2 - (cy - r))
            if overlap_x < overlap_y:
                ball.vx = -abs(ball.vx) if cx < (x1 + x2) / 2 else abs(ball.vx)
            else:
                ball.vy = -abs(ball.vy) if cy < (y1 + y2) / 2 else abs(ball.vy)
            if brick.hit():
                self.destroy_brick(brick, (x1 + x2) / 2, (y1 + y2) / 2)
            break
 
    def destroy_brick(self, brick, x, y):
        self.bricks.remove(brick)
        self.score += brick.points
        self.high_score = max(self.high_score, self.score)
        self.spawn_particles(x, y, brick.color)
        if random.random() < 0.18:
            kind = random.choice(['W', 'W', 'S', 'M', 'M', 'L'])
            self.powerups.append(PowerUp(self.canvas, x, y, kind))
        self.update_hud()
        if not self.bricks:
            self.level_clear()
 # ---------- power-ups & effects ----------
    def update_powerups(self):
        px1, py1, px2, py2 = self.paddle.get_position()
        for p in self.powerups[:]:
            p.move(0, 2.5)
            x1, y1, x2, y2 = p.get_position()
            if y1 > HEIGHT:
                p.delete()
                self.powerups.remove(p)
            elif y2 >= py1 and y1 <= py2 and x2 >= px1 and x1 <= px2:
                self.apply_powerup(p.kind)
                p.delete()
                self.powerups.remove(p)
 
    def apply_powerup(self, kind):
        self.score += 25
        if kind == 'W':
            self.effects['wide'] = 600
            self.paddle.set_width(Paddle.WIDE_WIDTH)
        elif kind == 'S':
            self.effects['slow'] = 600
            for b in self.balls:
                b.set_speed(self.current_speed())
        elif kind == 'M':
            for b in self.balls[:2]:
                for angle in (-0.4, 0.4):
                    if len(self.balls) >= 6:
                        break
                    x, y = b.center()
                    nb = Ball(self.canvas, x, y, b.speed(), b.vx, b.vy)
                    nb.rotate(angle)
                    self.balls.append(nb)
        elif kind == 'L':
            self.lives = min(self.lives + 1, 5)
        self.high_score = max(self.high_score, self.score)
        self.update_hud()
 
    def update_effects(self):
        for name in list(self.effects):
            self.effects[name] -= 1
            if self.effects[name] <= 0:
                del self.effects[name]
                if name == 'wide':
                    self.paddle.set_width(Paddle.NORMAL_WIDTH)
                elif name == 'slow':
                    for b in self.balls:
                        b.set_speed(self.current_speed())
 
    # ---------- particles ----------
    def spawn_particles(self, x, y, color):
        for _ in range(8):
            item = self.canvas.create_rectangle(x, y, x + 4, y + 4,
                                                fill=color, outline='')
            self.particles.append([item, random.uniform(-3, 3),
                                   random.uniform(-4, 1), 28])
 
    def update_particles(self):
        for p in self.particles[:]:
            item, vx, vy, life = p
            self.canvas.move(item, vx, vy)
            p[2] = vy + 0.2
            p[3] = life - 1
            if p[3] <= 0:
                self.canvas.delete(item)
                self.particles.remove(p)
 # ---------- game flow ----------
    def lose_life(self):
        self.lives -= 1
        for p in self.powerups:
            p.delete()
        self.powerups = []
        self.effects = {}
        self.paddle.set_width(Paddle.NORMAL_WIDTH)
        self.update_hud()
        if self.lives <= 0:
            self.state = 'over'
            self.show_message('Game Over',
                              f'Skor akhir: {self.score}   |   Spasi / klik untuk main lagi')
        else:
            self.spawn_ball_on_paddle()
            self.state = 'ready'
            self.show_message('Coba lagi!', 'Spasi / klik untuk meluncurkan bola')
 
    def level_clear(self):
        self.state = 'cleared'
        self.score += 100 * self.level
        self.high_score = max(self.high_score, self.score)
        self.update_hud()
        self.show_message(f'Level {self.level} selesai!', 'Bonus +%d' % (100 * self.level))
        self.pending = self.after(1800, self.next_level)
 
    def next_level(self):
        self.pending = None
        self.level += 1
        self.start_level()
 
 
if __name__ == '__main__':
    root = tk.Tk()
    root.title('Breakout')
    root.resizable(False, False)
    Game(root)
    root.mainloop()
 