import pygame
import numpy as np
import pandas as pd
import fastf1 as ff1
import sys
import os

# Initialize pygame
pygame.init()

# Parameters
year = 2025
wknd = "MANOS"
ses = "R"
driver = "HAM"

# Screen settings - Optimized for 1920x1080
NATIVE_WIDTH, NATIVE_HEIGHT = 640, 400
SCALE_FACTOR = 2
WIDTH = NATIVE_WIDTH * SCALE_FACTOR
HEIGHT = NATIVE_HEIGHT * SCALE_FACTOR

screen = pygame.display.set_mode((WIDTH, HEIGHT))
canvas = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
pygame.display.set_caption(f"TRACKSHIFT - {driver}")
clock = pygame.time.Clock()

# Retro color palette
COLORS = {
    'bg_dark': (5, 5, 15),
    'track': (45, 45, 65),
    'track_bright': (65, 65, 95),
    'text_yellow': (255, 255, 100),
    'text_cyan': (100, 255, 255),
    'text_magenta': (255, 100, 255),
    'text_white': (220, 220, 220),
    'text_dim': (120, 120, 140),
    'panel_bg': (15, 10, 30),
    'panel_border': (100, 50, 150),
    'control_box_bg': (10, 8, 25),
    'control_box_border': (80, 40, 100),
    'speed_gradient': [
        (50, 100, 255),
        (0, 255, 150),
        (255, 255, 50),
        (255, 100, 150)
    ],
    'scanline': (0, 0, 0, 80),
}

# Layout
MAP_WIDTH = 480
PANEL_WIDTH = NATIVE_WIDTH - MAP_WIDTH
PANEL_X = MAP_WIDTH

# Load F1 data
print(">>> INITIALIZING TRACKSHIFT...")
session = ff1.get_session(year, wknd, ses)
session.load()

# Get event name properly
event_info = session.event
if hasattr(event_info, 'EventName'):
    event_name = str(event_info.EventName)
elif hasattr(event_info, 'Location'):
    event_name = str(event_info.Location)
else:
    event_name = "RACE"

laps = session.laps.pick_drivers(driver)
print(f">>> {len(laps)} LAPS LOADED")

# Retro fonts
font_large = pygame.font.SysFont('courier', 24, bold=True)
font_med = pygame.font.SysFont('courier', 20, bold=True)
font_small = pygame.font.SysFont('courier', 16, bold=True)
font_tiny = pygame.font.SysFont('courier', 12, bold=True)  # For controls

# Normalize coordinates
def normalize_coords(x_data, y_data, margin=30):
    x_min, x_max = np.min(x_data), np.max(x_data)
    y_min, y_max = np.min(y_data), np.max(y_data)
    
    x_range = x_max - x_min
    y_range = y_max - y_min
    scale = min((MAP_WIDTH - 2*margin) / x_range, (NATIVE_HEIGHT - 2*margin) / y_range)
    
    x_scaled = (x_data - x_min) * scale
    y_scaled = (y_data - y_min) * scale
    
    x_offset = (MAP_WIDTH - (x_scaled.max() - x_scaled.min())) / 2
    y_offset = (NATIVE_HEIGHT - (y_scaled.max() - y_scaled.min())) / 2
    
    x_scaled = (x_scaled + x_offset).astype(int)
    y_scaled = (y_scaled + y_offset).astype(int)
    
    return x_scaled, y_scaled

# Speed to color
def speed_to_color(speed, min_speed, max_speed):
    if max_speed <= min_speed:
        return COLORS['speed_gradient'][0]
    
    normalized = (speed - min_speed) / (max_speed - min_speed)
    normalized = max(0, min(1, normalized))
    
    num_colors = len(COLORS['speed_gradient'])
    idx = normalized * (num_colors - 1)
    idx1 = int(idx)
    idx2 = min(idx1 + 1, num_colors - 1)
    blend = idx - idx1
    
    c1 = COLORS['speed_gradient'][idx1]
    c2 = COLORS['speed_gradient'][idx2]
    
    return tuple(int(c1[i] + (c2[i] - c1[i]) * blend) for i in range(3))

# CRT scanlines
def apply_crt_effect(surface):
    scanline_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for y in range(0, surface.get_height(), 2):
        pygame.draw.line(scanline_surface, COLORS['scanline'], 
                        (0, y), (surface.get_width(), y), 1)
    surface.blit(scanline_surface, (0, 0))

# Collect track data
print(">>> PROCESSING TRACK DATA...")
all_x = []
all_y = []
for _, lap in laps.iterlaps():
    try:
        pos = lap.get_pos_data()
        all_x.extend(pos['X'].values)
        all_y.extend(pos['Y'].values)
    except:
        continue

track_x, track_y = normalize_coords(np.array(all_x), np.array(all_y))

# Animation state
current_lap_idx = 0
animation_running = True
paused = False
speed_multiplier = 2.0
elapsed_time = 0
last_time = pygame.time.get_ticks()

print(">>> TRACKSHIFT READY")

# Main loop
while animation_running:
    current_time = pygame.time.get_ticks()
    dt = current_time - last_time
    last_time = current_time
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            animation_running = False
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                paused = not paused
            elif event.key == pygame.K_RIGHT:
                current_lap_idx = (current_lap_idx + 1) % len(laps)
                elapsed_time = 0
            elif event.key == pygame.K_LEFT:
                current_lap_idx = (current_lap_idx - 1) % len(laps)
                elapsed_time = 0
            elif event.key == pygame.K_UP:
                speed_multiplier = min(speed_multiplier + 0.5, 10)
            elif event.key == pygame.K_DOWN:
                speed_multiplier = max(speed_multiplier - 0.5, 0.5)
            elif event.key == pygame.K_r:
                elapsed_time = 0
    
    if not paused:
        elapsed_time += dt * speed_multiplier
    
    canvas.fill(COLORS['bg_dark'])
    
    # Draw track outline
    if len(track_x) > 1:
        track_points = list(zip(track_x[::3], track_y[::3]))
        pygame.draw.lines(canvas, COLORS['track'], False, track_points, 4)
    
    lap = laps.iloc[current_lap_idx]
    
    try:
        tel = lap.get_car_data().add_distance()
        pos = lap.get_pos_data()
        
        x = pos['X'].values
        y = pos['Y'].values
        speed = tel['Speed'].values
        
        min_len = min(len(x), len(y), len(speed))
        x = x[:min_len]
        y = y[:min_len]
        speed = speed[:min_len]
        
        x_scaled, y_scaled = normalize_coords(x, y)
        
        points_per_second = len(x) / 10
        frame_index = int((elapsed_time / 1000.0) * points_per_second) % len(x)
        
        # Draw trail
        trail_length = min(60, frame_index)
        for i in range(max(0, frame_index - trail_length), frame_index):
            if i > 0 and i < len(speed):
                color = speed_to_color(speed[i], speed.min(), speed.max())
                pygame.draw.line(canvas, color,
                               (x_scaled[i-1], y_scaled[i-1]),
                               (x_scaled[i], y_scaled[i]), 4)
        
        # Draw car
        car_color = speed_to_color(speed[frame_index], speed.min(), speed.max())
        pygame.draw.circle(canvas, car_color, (x_scaled[frame_index], y_scaled[frame_index]), 6)
        pygame.draw.circle(canvas, COLORS['text_yellow'], (x_scaled[frame_index], y_scaled[frame_index]), 6, 2)
        
        # === RIGHT PANEL ===
        pygame.draw.rect(canvas, COLORS['panel_bg'], (PANEL_X, 0, PANEL_WIDTH, NATIVE_HEIGHT))
        pygame.draw.line(canvas, COLORS['panel_border'], (PANEL_X, 0), (PANEL_X, NATIVE_HEIGHT), 3)
        
        lap_num = lap['LapNumber']
        lap_time_obj = lap['LapTime']
        if lap_time_obj is not None and not pd.isna(lap_time_obj):
            lap_time = str(lap_time_obj).split('.')[0][-8:]
        else:
            lap_time = "N/A"
        
        current_speed = speed[frame_index]
        progress_pct = int(frame_index * 100 / len(x))
        
        y_pos = 16
        
        # Driver name
        title = font_large.render(driver, True, COLORS['text_yellow'])
        canvas.blit(title, (PANEL_X + 10, y_pos))
        y_pos += 28
        
        # Event name
        event_display = event_name.split(' ')[0][:8] if ' ' in event_name else event_name[:8]
        event_text = font_small.render(event_display.upper(), True, COLORS['text_cyan'])
        canvas.blit(event_text, (PANEL_X + 10, y_pos))
        y_pos += 24
        
        # Divider
        pygame.draw.line(canvas, COLORS['panel_border'], 
                        (PANEL_X + 6, y_pos), (PANEL_X + PANEL_WIDTH - 6, y_pos), 2)
        y_pos += 12
        
        # Lap number
        lap_label = font_small.render("LAP", True, COLORS['text_dim'])
        canvas.blit(lap_label, (PANEL_X + 10, y_pos))
        y_pos += 18
        lap_value = font_med.render(f"{lap_num}/{len(laps)}", True, COLORS['text_white'])
        canvas.blit(lap_value, (PANEL_X + 10, y_pos))
        y_pos += 28
        
        # Lap time
        time_label = font_small.render("TIME", True, COLORS['text_dim'])
        canvas.blit(time_label, (PANEL_X + 10, y_pos))
        y_pos += 18
        time_value = font_small.render(lap_time, True, COLORS['text_white'])
        canvas.blit(time_value, (PANEL_X + 10, y_pos))
        y_pos += 24
        
        # Speed
        speed_label = font_small.render("SPEED", True, COLORS['text_dim'])
        canvas.blit(speed_label, (PANEL_X + 10, y_pos))
        y_pos += 18
        speed_value = font_large.render(f"{int(current_speed)}", True, car_color)
        canvas.blit(speed_value, (PANEL_X + 10, y_pos))
        speed_unit = font_small.render("KM/H", True, COLORS['text_dim'])
        canvas.blit(speed_unit, (PANEL_X + 10, y_pos + 24))
        y_pos += 52
        
        # Progress bar
        bar_w = PANEL_WIDTH - 24
        bar_h = 10
        bar_x = PANEL_X + 10
        pygame.draw.rect(canvas, COLORS['track'], (bar_x, y_pos, bar_w, bar_h))
        fill_w = int(bar_w * progress_pct / 100)
        pygame.draw.rect(canvas, COLORS['text_cyan'], (bar_x, y_pos, fill_w, bar_h))
        y_pos += 16
        
        prog_text = font_small.render(f"{progress_pct}%", True, COLORS['text_white'])
        canvas.blit(prog_text, (PANEL_X + 10, y_pos))
        y_pos += 24
        
        # Animation speed
        multi_label = font_small.render("ANIM", True, COLORS['text_dim'])
        canvas.blit(multi_label, (PANEL_X + 10, y_pos))
        y_pos += 18
        multi_value = font_med.render(f"x{speed_multiplier:.1f}", True, COLORS['text_magenta'])
        canvas.blit(multi_value, (PANEL_X + 10, y_pos))
        
        # === CONTROLS BOX (Bottom Left) ===
        control_box_width = 130
        control_box_height = 80
        control_box_x = 10
        control_box_y = NATIVE_HEIGHT - control_box_height - 10
        
        # Draw semi-transparent background
        control_bg = pygame.Surface((control_box_width, control_box_height), pygame.SRCALPHA)
        control_bg.fill((*COLORS['control_box_bg'], 200))
        canvas.blit(control_bg, (control_box_x, control_box_y))
        
        # Draw border
        pygame.draw.rect(canvas, COLORS['control_box_border'], 
                        (control_box_x, control_box_y, control_box_width, control_box_height), 2)
        
        # Controls text
        ctrl_y = control_box_y + 8
        ctrl_x = control_box_x + 6
        
        ctrl_title = font_tiny.render("CONTROLS", True, COLORS['text_cyan'])
        canvas.blit(ctrl_title, (ctrl_x, ctrl_y))
        ctrl_y += 14
        
        controls = [
            "PAUSE - Space",
            "LAP - Right/Left",
            "SPEED - Up/Down",
            "RESET - R"
        ]
        for ctrl in controls:
            ctrl_text = font_tiny.render(ctrl, True, COLORS['text_white'])
            canvas.blit(ctrl_text, (ctrl_x, ctrl_y))
            ctrl_y += 13
        
        # Pause indicator
        if paused:
            if (pygame.time.get_ticks() // 400) % 2:
                pause_bg = pygame.Surface((100, 24))
                pause_bg.fill(COLORS['panel_border'])
                canvas.blit(pause_bg, (MAP_WIDTH // 2 - 50, 20))
                pause_text = font_large.render("PAUSE", True, COLORS['text_yellow'])
                canvas.blit(pause_text, (MAP_WIDTH // 2 - 44, 22))
        
    except Exception as e:
        error_text = font_small.render("LOADING", True, COLORS['text_magenta'])
        canvas.blit(error_text, (20, NATIVE_HEIGHT // 2))
        print(f"Error: {e}")
    
    # Apply CRT effect
    apply_crt_effect(canvas)
    
    # Scale up
    scaled_canvas = pygame.transform.scale(canvas, (WIDTH, HEIGHT))
    screen.blit(scaled_canvas, (0, 0))
    
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
