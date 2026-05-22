import pygame
import sys
import random

WIDTH, HEIGHT = 480, 640
FPS = 60

# --- 色 ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255,  60,  60)
GREEN = (60, 255,  60)

# --- 基本クラス ---


class Player(pygame.sprite.Sprite):
    SPEED = 5

    def __init__(self):
        super().__init__()
        self.image = pygame.Surface((40, 30))
        self.image.fill(GREEN)
        self.rect = self.image.get_rect(midbottom=(WIDTH//2, HEIGHT - 10))

    def update(self, keys):
        if keys[pygame.K_LEFT] and self.rect.left > 0:
            self.rect.x -= self.SPEED
        if keys[pygame.K_RIGHT] and self.rect.right < WIDTH:
            self.rect.x += self.SPEED

    def shoot(self, group):
        bullet = Bullet(self.rect.midtop)
        group.add(bullet)


class Bullet(pygame.sprite.Sprite):
    SPEED = -8

    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface((4, 10))
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(midbottom=pos)

    def update(self, *_):
        self.rect.y += self.SPEED
        if self.rect.bottom < 0:
            self.kill()


class Enemy(pygame.sprite.Sprite):
    SPEED = 2

    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((30, 24))
        self.image.fill(RED)
        self.rect = self.image.get_rect(topleft=(x, y))

    def update(self, *_):
        self.rect.y += self.SPEED
        if self.rect.top > HEIGHT:
            self.kill()

# --- ユーティリティ ---


def spawn_wave(enemies, columns=6, rows=2):
    margin_x, margin_y = 40, 40
    gap = 60
    for row in range(rows):
        for col in range(columns):
            x = margin_x + col * gap
            y = margin_y + row * gap
            enemies.add(Enemy(x, y))


def draw_text(surf, text, size, x, y, color=WHITE):
    font = pygame.font.SysFont(None, size)
    img = font.render(text, True, color)
    rect = img.get_rect(center=(x, y))
    surf.blit(img, rect)

# --- メイン ---


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Simple Shooter")
    clock = pygame.time.Clock()

    player = Player()
    players = pygame.sprite.GroupSingle(player)
    bullets = pygame.sprite.Group()
    enemies = pygame.sprite.Group()

    spawn_wave(enemies)
    score = 0

    while True:
        clock.tick(FPS)
        keys = pygame.key.get_pressed()

        # --- イベント ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                player.shoot(bullets)

        # --- 更新 ---
        players.update(keys)
        bullets.update()
        enemies.update()

        # 衝突: 弾 vs 敵
        hits = pygame.sprite.groupcollide(enemies, bullets, True, True)
        score += len(hits) * 10

        # 新しい敵編隊
        if not enemies:
            spawn_wave(enemies, rows=3)

        # 衝突: 敵 vs プレイヤー
        if pygame.sprite.spritecollide(player, enemies, False):
            break  # ゲームオーバー

        # --- 描画 ---
        screen.fill(BLACK)
        players.draw(screen)
        bullets.draw(screen)
        enemies.draw(screen)
        draw_text(screen, f"Score: {score}", 28, WIDTH//2, 20)
        pygame.display.flip()

    # --- 終了画面 ---
    draw_text(screen, "GAME OVER", 64, WIDTH//2, HEIGHT//2, RED)
    pygame.display.flip()
    pygame.time.wait(2000)
    pygame.quit()


if __name__ == "__main__":
    main()
