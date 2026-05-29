import pygame
import sys
import random

WIDTH, HEIGHT = 480, 640
FPS = 60

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 60, 60)
GREEN = (60, 255, 60)
GOLD = (255, 215, 0)

# --- コンポーネント ---


class PositionComponent:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class VelocityComponent:
    def __init__(self, vx, vy):
        self.vx = vx
        self.vy = vy


class RenderComponent:
    def __init__(self, width, height, color):
        self.width = width
        self.height = height
        self.color = color


class ControlComponent:
    def __init__(self, speed):
        self.speed = speed


class ShotgunComponent:
    def __init__(self):
        self.timer = 0


class HomingModeComponent:
    def __init__(self):
        self.timer = 0


class ActiveItemsComponent:
    def __init__(self):
        self.items = []  # ["shotgun", "homing"] のように順序を保持


class HealthComponent:
    def __init__(self, hp):
        self.hp = hp
        self.max_hp = hp


class BulletComponent:
    pass


class ShotgunBulletComponent:
    pass


class EnemyComponent:
    pass


class ItemComponent:
    def __init__(self, item_type="shotgun"):
        self.item_type = item_type


class HomingBulletComponent:
    def __init__(self):
        self.target = None


class AttackComponent:
    def __init__(self, atk):
        self.atk = atk


class PowerUpComponent:
    def __init__(self):
        self.timer = 0

# --- エンティティマネージャー ---


class Entity:
    _id_counter = 0

    def __init__(self):
        self.id = Entity._id_counter
        Entity._id_counter += 1
        self.components = {}

    def add_component(self, component):
        self.components[type(component)] = component
        return self

    def get_component(self, component_type):
        return self.components.get(component_type)

    def has_component(self, component_type):
        return component_type in self.components

# --- システム ---


class MovementSystem:
    def update(self, entities):
        for entity in entities:
            pos = entity.get_component(PositionComponent)
            vel = entity.get_component(VelocityComponent)
            if pos and vel:
                pos.x += vel.vx
                pos.y += vel.vy


class ControlSystem:
    def update(self, entities, keys):
        for entity in entities:
            if not entity.has_component(ControlComponent):
                continue
            vel = entity.get_component(VelocityComponent)
            control = entity.get_component(ControlComponent)
            if vel:
                vel.vx = 0
                vel.vy = 0
                if keys[pygame.K_LEFT] and entity.get_component(PositionComponent).x > 0:
                    vel.vx = -control.speed
                if keys[pygame.K_RIGHT] and entity.get_component(PositionComponent).x < WIDTH - 40:
                    vel.vx = control.speed
                if keys[pygame.K_UP] and entity.get_component(PositionComponent).y > 0:
                    vel.vy = -control.speed
                if keys[pygame.K_DOWN] and entity.get_component(PositionComponent).y < HEIGHT - 40:
                    vel.vy = control.speed


class ShotgunSystem:
    def update(self, player):
        shotgun = player.get_component(ShotgunComponent)
        if shotgun and shotgun.timer > 0:
            shotgun.timer -= 1
        else:
            shotgun.timer = 0

        homing = player.get_component(HomingModeComponent)
        if homing and homing.timer > 0:
            homing.timer -= 1
        else:
            homing.timer = 0

        power = player.get_component(PowerUpComponent)
        if power and power.timer > 0:
            power.timer -= 1
        else:
            power.timer = 0

        # タイマーが切れたアイテムをアクティブリストから削除
        active = player.get_component(ActiveItemsComponent)
        if shotgun.timer == 0 and "shotgun" in active.items:
            active.items.remove("shotgun")
        if homing.timer == 0 and "homing" in active.items:
            active.items.remove("homing")
        if power.timer == 0 and "power" in active.items:
            active.items.remove("power")


class HomingSystem:
    def update(self, bullets, enemies):
        for bullet in bullets:
            homing = bullet.get_component(HomingBulletComponent)
            if not homing:
                continue

            # ターゲットが死んでいたら新しいターゲットを探す
            if homing.target is None or homing.target not in enemies:
                if enemies:
                    homing.target = enemies[0]
                else:
                    continue

            # ターゲットに向かって移動
            bullet_pos = bullet.get_component(PositionComponent)
            target_pos = homing.target.get_component(PositionComponent)
            vel = bullet.get_component(VelocityComponent)

            dx = target_pos.x - bullet_pos.x
            dy = target_pos.y - bullet_pos.y
            dist = (dx**2 + dy**2)**0.5

            if dist > 0:
                vel.vx = (dx / dist) * 6
                vel.vy = (dy / dist) * 6


class RenderSystem:
    def __init__(self, screen):
        self.screen = screen

    def update(self, entities):
        for entity in entities:
            pos = entity.get_component(PositionComponent)
            render = entity.get_component(RenderComponent)
            if pos and render:
                x = int(pos.x - render.width // 2)
                y = int(pos.y - render.height // 2)
                pygame.draw.rect(self.screen, render.color,
                                 (x, y, render.width, render.height))


class CollisionSystem:
    def check_enemy_bullet_collision(self, enemies, bullets):
        hits = []
        for enemy in enemies:
            enemy_pos = enemy.get_component(PositionComponent)
            for bullet in bullets:
                bullet_pos = bullet.get_component(PositionComponent)
                if (abs(enemy_pos.x - bullet_pos.x) < 25 and
                        abs(enemy_pos.y - bullet_pos.y) < 25):
                    hits.append((enemy, bullet))
        return hits

    def check_player_item_collision(self, player, items):
        player_pos = player.get_component(PositionComponent)
        hits = []
        for item in items:
            item_pos = item.get_component(PositionComponent)
            if (abs(player_pos.x - item_pos.x) < 30 and
                    abs(player_pos.y - item_pos.y) < 30):
                hits.append(item)
        return hits

    def check_player_enemy_collision(self, player, enemies):
        player_pos = player.get_component(PositionComponent)
        for enemy in enemies:
            enemy_pos = enemy.get_component(PositionComponent)
            if (abs(player_pos.x - enemy_pos.x) < 35 and
                    abs(player_pos.y - enemy_pos.y) < 27):
                return True
        return False


class BulletLifeSystem:
    def update(self, bullets):
        dead = []
        for bullet in bullets:
            pos = bullet.get_component(PositionComponent)
            if pos.y < -10 or pos.x < -10 or pos.x > WIDTH + 10:
                dead.append(bullet)
        return dead


class EnemyLifeSystem:
    def update(self, enemies):
        dead = []
        for enemy in enemies:
            pos = enemy.get_component(PositionComponent)
            if pos.y > HEIGHT + 10:
                dead.append(enemy)
        return dead


class ItemLifeSystem:
    def update(self, items):
        dead = []
        for item in items:
            pos = item.get_component(PositionComponent)
            if pos.y > HEIGHT + 10:
                dead.append(item)
        return dead


class HUDSystem:
    def __init__(self, screen):
        self.screen = screen
        self._icons = {}
        self._build_icons()

    def _build_icons(self):
        size = 48
        font = pygame.font.SysFont(None, 22)

        # ショットガンアイコン: 金色グラデーション正方形
        sg = pygame.Surface((size, size), pygame.SRCALPHA)
        for row in range(size):
            r = min(255, 180 + row * 75 // size)
            g = min(255, 130 + row * 85 // size)
            pygame.draw.line(sg, (r, g, 0, 255), (0, row), (size - 1, row))
        pygame.draw.rect(sg, (255, 240, 80), (0, 0, size, size), 2)
        label = font.render("SG", True, (60, 40, 0))
        sg.blit(label, label.get_rect(center=(size // 2, size // 2)))
        self._icons["shotgun"] = sg

        # ホーミングアイコン: 緑グラデーション正方形 + クロスヘア
        hm = pygame.Surface((size, size), pygame.SRCALPHA)
        for row in range(size):
            g = min(255, 140 + row * 115 // size)
            pygame.draw.line(hm, (0, g, 40, 255), (0, row), (size - 1, row))
        pygame.draw.rect(hm, (80, 255, 100), (0, 0, size, size), 2)
        cx, cy, r = size // 2, size // 2, size // 3
        pygame.draw.circle(hm, (0, 80, 20), (cx, cy), r, 2)
        pygame.draw.line(hm, (0, 80, 20), (cx, 3), (cx, size - 3), 1)
        pygame.draw.line(hm, (0, 80, 20), (3, cy), (size - 3, cy), 1)
        label = font.render("HM", True, (0, 50, 10))
        hm.blit(label, label.get_rect(center=(cx, cy)))
        self._icons["homing"] = hm

        # パワーアップアイコン: 炎のようなオレンジ〜赤グラデーション
        pw = pygame.Surface((size, size), pygame.SRCALPHA)
        for row in range(size):
            r = 255
            g = max(0, 160 - row * 160 // size)
            pygame.draw.line(pw, (r, g, 0, 255), (0, row), (size - 1, row))
        pygame.draw.rect(pw, (255, 200, 60), (0, 0, size, size), 2)
        label = font.render("PW", True, (80, 20, 0))
        pw.blit(label, label.get_rect(center=(size // 2, size // 2)))
        self._icons["power"] = pw

    def draw_item_icon(self, player, frame):
        shotgun = player.get_component(ShotgunComponent)
        homing = player.get_component(HomingModeComponent)
        power = player.get_component(PowerUpComponent)
        active = player.get_component(ActiveItemsComponent)

        size = 48
        spacing = 56
        start_x = WIDTH - 56

        for idx, item_type in enumerate(reversed(active.items)):
            cx = start_x - idx * spacing
            cy = size // 2 + 8

            if item_type == "shotgun" and shotgun.timer > 0:
                self._draw_icon(cx, cy, size, "shotgun",
                                shotgun.timer, 300, frame)
            elif item_type == "homing" and homing.timer > 0:
                self._draw_icon(cx, cy, size, "homing",
                                homing.timer, 300, frame)
            elif item_type == "power" and power.timer > 0:
                self._draw_icon(cx, cy, size, "power",
                                power.timer, 300, frame)

    def _draw_icon(self, cx, cy, size, item_type, timer, max_timer, frame):
        # 最後の1秒で点滅
        if timer < 60 and (frame // 10) % 2 == 0:
            return

        x = cx - size // 2
        y = cy - size // 2

        # 正方形アイコンを描画
        self.screen.blit(self._icons[item_type], (x, y))

        # 水面エフェクト: 上から透明エリアが増える（水面が下がる）
        progress = timer / max_timer          # 1.0=満タン, 0.0=空
        drained_h = int((1.0 - progress) * size)

        if drained_h > 0:
            overlay = pygame.Surface((size, drained_h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 200))
            self.screen.blit(overlay, (x, y))

        # 水面ライン（シマー）
        if 0 < drained_h < size:
            line_y = y + drained_h
            shimmer = (frame % 8) < 4
            line_col = (200, 230, 255) if shimmer else (140, 190, 240)
            pygame.draw.line(self.screen, line_col,
                             (x, line_y), (x + size - 1, line_y), 2)

# --- ファクトリー ---


def create_player():
    player = Entity()
    player.add_component(PositionComponent(WIDTH // 2, HEIGHT - 30))
    player.add_component(VelocityComponent(0, 0))
    player.add_component(RenderComponent(40, 30, GREEN))
    player.add_component(ControlComponent(5))
    player.add_component(ShotgunComponent())
    player.add_component(HomingModeComponent())
    player.add_component(PowerUpComponent())
    player.add_component(ActiveItemsComponent())
    return player


_ENEMY_HP_COLORS = {1: (255, 60, 60), 2: (255, 130, 30), 3: (180, 30, 255)}


def create_enemy(x, y):
    hp = random.randint(1, 3)
    color = _ENEMY_HP_COLORS[hp]
    enemy = Entity()
    enemy.add_component(PositionComponent(x, y))
    enemy.add_component(VelocityComponent(0, 2))
    enemy.add_component(RenderComponent(30, 24, color))
    enemy.add_component(HealthComponent(hp))
    enemy.add_component(EnemyComponent())
    return enemy


def create_bullet(player_pos, shotgun_active, angle=0, atk=1):
    bullet = Entity()
    color = (255, 160, 40) if atk > 1 else WHITE
    if shotgun_active:
        bullet.add_component(PositionComponent(player_pos.x, player_pos.y))
        bullet.add_component(VelocityComponent(angle * 3, -10))
        bullet.add_component(RenderComponent(3, 8, color))
        bullet.add_component(ShotgunBulletComponent())
    else:
        bullet.add_component(PositionComponent(player_pos.x, player_pos.y))
        bullet.add_component(VelocityComponent(0, -8))
        bullet.add_component(RenderComponent(4, 10, color))
        bullet.add_component(BulletComponent())
    bullet.add_component(AttackComponent(atk))
    return bullet


def create_homing_bullet(player_pos, atk=1):
    bullet = Entity()
    color = (255, 200, 60) if atk > 1 else (100, 255, 100)
    bullet.add_component(PositionComponent(player_pos.x, player_pos.y))
    bullet.add_component(VelocityComponent(0, -6))
    bullet.add_component(RenderComponent(5, 5, color))
    bullet.add_component(HomingBulletComponent())
    bullet.add_component(AttackComponent(atk * 2))
    return bullet


_ITEM_COLORS = {"shotgun": GOLD, "homing": (
    100, 255, 100), "power": (255, 140, 0)}


def create_item(x, y, item_type="shotgun"):
    item = Entity()
    item.add_component(PositionComponent(x, y))
    item.add_component(VelocityComponent(0, 2))
    item.add_component(RenderComponent(
        20, 20, _ITEM_COLORS.get(item_type, WHITE)))
    item.add_component(ItemComponent(item_type))
    return item


def spawn_wave(rows=2, columns=6):
    enemies = []
    margin_x, margin_y = 40, 40
    gap = 60
    for row in range(rows):
        for col in range(columns):
            x = margin_x + col * gap
            y = margin_y + row * gap
            enemies.append(create_enemy(x, y))
    return enemies


def draw_enemy_hp_bars(screen, enemies):
    for enemy in enemies:
        health = enemy.get_component(HealthComponent)
        if health.max_hp <= 1:
            continue
        pos = enemy.get_component(PositionComponent)
        bar_w, bar_h = 28, 4
        x = int(pos.x - bar_w // 2)
        y = int(pos.y - 20)
        ratio = max(0, health.hp / health.max_hp)
        pygame.draw.rect(screen, (80, 0, 0), (x, y, bar_w, bar_h))
        pygame.draw.rect(screen, (255, 80, 80),
                         (x, y, int(bar_w * ratio), bar_h))


def draw_text(surf, text, size, x, y, color=WHITE):
    font = pygame.font.SysFont(None, size)
    img = font.render(text, True, color)
    rect = img.get_rect(center=(x, y))
    surf.blit(img, rect)


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple Shooter ECS")
    clock = pygame.time.Clock()

    player = create_player()
    enemies = spawn_wave()
    bullets = []
    items = []

    score = 0

    # システム初期化
    movement = MovementSystem()
    control = ControlSystem()
    shotgun_sys = ShotgunSystem()
    render = RenderSystem(screen)
    collision = CollisionSystem()
    bullet_life = BulletLifeSystem()
    enemy_life = EnemyLifeSystem()
    item_life = ItemLifeSystem()
    homing = HomingSystem()
    hud = HUDSystem(screen)

    shoot_cooldown = 0
    paused = False
    restart = False
    quit_from_pause = False
    running = True
    while running:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()
        frame = pygame.time.get_ticks() // 33  # フレームカウント

        # イベント
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    paused = not paused
                elif paused:
                    if event.key == pygame.K_r:
                        restart = True
                        running = False
                    elif event.key == pygame.K_q:
                        quit_from_pause = True
                        running = False

        if paused:
            # ポーズ中はゲームロジックをスキップ
            screen.fill(BLACK)
            render.update([player] + enemies + bullets + items)
            draw_enemy_hp_bars(screen, enemies)
            draw_text(screen, f"Score: {score}", 28, WIDTH // 2, 20)
            hud.draw_item_icon(player, frame)
            draw_text(screen, f"FPS: {clock.get_fps():.0f}", 20, 36, 12)
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            draw_text(screen, "PAUSE", 64, WIDTH // 2, HEIGHT // 2 - 70)
            draw_text(screen, "ESC  resume", 30, WIDTH // 2, HEIGHT // 2)
            draw_text(screen, "R  restart", 30, WIDTH // 2, HEIGHT // 2 + 40)
            draw_text(screen, "Q  end", 30, WIDTH // 2, HEIGHT // 2 + 80)
            pygame.display.flip()
            continue

        # スペース押しっぱなし射撃
        if shoot_cooldown > 0:
            shoot_cooldown -= 1
        if keys[pygame.K_SPACE] and shoot_cooldown == 0:
            player_pos = player.get_component(PositionComponent)
            shotgun = player.get_component(ShotgunComponent)
            homing_mode = player.get_component(HomingModeComponent)
            power_comp = player.get_component(PowerUpComponent)
            atk = 2 if power_comp.timer > 0 else 1
            if shotgun.timer > 0:
                for angle in range(-3, 4):
                    bullets.append(create_bullet(player_pos, True, angle, atk))
                shoot_cooldown = 10
            elif homing_mode.timer > 0:
                bullets.append(create_homing_bullet(player_pos, atk))
                shoot_cooldown = 20
            else:
                bullets.append(create_bullet(player_pos, False, atk=atk))
                shoot_cooldown = 12

        # システム実行順序（レイヤー化）
        # 1. 入力処理
        control.update([player], keys)

        # 2. 物理演算
        movement.update([player] + enemies + bullets + items)

        # 3. 追尾弾の更新
        homing.update(bullets, enemies)

        # 4. ショットガン更新
        shotgun_sys.update(player)

        # 4. ライフシステム（画面外判定）
        bullets = [b for b in bullets if b not in bullet_life.update(bullets)]
        enemies = [e for e in enemies if e not in enemy_life.update(enemies)]
        items = [it for it in items if it not in item_life.update(items)]

        # 5. 衝突判定
        # 敵 vs 弾
        hits = collision.check_enemy_bullet_collision(enemies, bullets)
        to_remove_bullets = set()
        to_kill_enemies = set()
        for enemy, bullet in hits:
            if bullet in to_remove_bullets:
                continue
            health = enemy.get_component(HealthComponent)
            if health.hp <= 0:
                continue
            atk_comp = bullet.get_component(AttackComponent)
            health.hp -= atk_comp.atk if atk_comp else 1
            to_remove_bullets.add(bullet)
            if health.hp <= 0:
                to_kill_enemies.add(enemy)
        for bullet in to_remove_bullets:
            if bullet in bullets:
                bullets.remove(bullet)
        for enemy in to_kill_enemies:
            if enemy in enemies:
                enemies.remove(enemy)
            enemy_pos = enemy.get_component(PositionComponent)
            item_type = random.choices(
                ["shotgun", "homing", "power"], weights=[4, 4, 2])[0]
            if random.random() < 0.1:  # 10%の確率でアイテムドロップ
                items.append(create_item(enemy_pos.x, enemy_pos.y, item_type))
            score += 10

        # プレイヤー vs アイテム
        item_hits = collision.check_player_item_collision(player, items)
        for item in item_hits:
            items.remove(item)
            item_comp = item.get_component(ItemComponent)
            active = player.get_component(ActiveItemsComponent)

            if item_comp.item_type == "shotgun":
                shotgun = player.get_component(ShotgunComponent)
                shotgun.timer = 300
                if "shotgun" in active.items:
                    active.items.remove("shotgun")
                active.items.append("shotgun")

            elif item_comp.item_type == "homing":
                homing_mode = player.get_component(HomingModeComponent)
                homing_mode.timer = 300
                if "homing" in active.items:
                    active.items.remove("homing")
                active.items.append("homing")

            elif item_comp.item_type == "power":
                power_up = player.get_component(PowerUpComponent)
                power_up.timer = 300
                if "power" in active.items:
                    active.items.remove("power")
                active.items.append("power")

        # プレイヤー vs 敵
        if collision.check_player_enemy_collision(player, enemies):
            running = False

        # 敵がいなくなったら新しい波
        if not enemies:
            enemies = spawn_wave(rows=3)

        # 描画
        screen.fill(BLACK)
        render.update([player] + enemies + bullets + items)
        draw_enemy_hp_bars(screen, enemies)
        draw_text(screen, f"Score: {score}", 28, WIDTH//2, 20)
        hud.draw_item_icon(player, frame)
        fps = clock.get_fps()
        draw_text(screen, f"FPS: {fps:.0f}", 20, 36, 12)
        pygame.display.flip()

    if restart:
        return True

    if quit_from_pause:
        return False

    # ゲームオーバー
    draw_text(screen, "GAME OVER", 64, WIDTH//2, HEIGHT//2 - 40, RED)
    draw_text(screen, "R  restart", 30, WIDTH//2, HEIGHT//2 + 20)
    draw_text(screen, "Q  end", 30, WIDTH//2, HEIGHT//2 + 60)
    pygame.display.flip()
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    return True
                if event.key == pygame.K_q:
                    return False


if __name__ == "__main__":
    while main():
        pass
    pygame.quit()
