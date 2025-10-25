import pygame
import numpy as np
import pandas as pd
import fastf1 as ff1
import sys
import os
from datetime import timedelta

# Initialize pygame
pygame.init()

# Parameters
year = 2025
wknd = 9
ses = "R"
drivers = ["HAM", "VER", "LEC"]

# Screen settings
NATIVE_WIDTH, NATIVE_HEIGHT = 640, 400
SCALE_FACTOR = 2
WIDTH = NATIVE_WIDTH * SCALE_FACTOR
HEIGHT = NATIVE_HEIGHT * SCALE_FACTOR

screen = pygame.display.set_mode((WIDTH, HEIGHT))
canvas = pygame.Surface((NATIVE_WIDTH, NATIVE_HEIGHT))
pygame.display.set_caption(f"TRACKSHIFT - RACE REPLAY")
clock = pygame.time.Clock()

# Driver colors
DRIVER_COLORS = {
    'HAM': (0, 200, 200),
    'VER': (30, 65, 255),
    'LEC': (220, 0, 0),
    'NOR': (255, 135, 0),
    'SAI': (220, 0, 0),
    'PER': (30, 65, 255),
    'RUS': (0, 200, 200),
    'ALO': (0, 120, 40),
}

# Retro color palette
COLORS = {
    'bg_dark': (5, 5, 15),
    'text_yellow': (255, 255, 100),
    'text_cyan': (100, 255, 255),
    'text_magenta': (255, 100, 255),
    'text_white': (220, 220, 220),
    'text_dim': (120, 120, 140),
    'panel_bg': (15, 10, 30),
    'panel_border': (100, 50, 150),
    'control_box_bg': (10, 8, 25),
    'control_box_border': (80, 40, 100),
    'leaderboard_bg': (10, 8, 25),
    'leaderboard_border': (100, 50, 150),
    'scanline': (0, 0, 0, 80),
}

# Layout
MAP_WIDTH = 480
PANEL_WIDTH = NATIVE_WIDTH - MAP_WIDTH
PANEL_X = MAP_WIDTH

# Load and prepare circuit background image
print(">>> LOADING CIRCUIT MAP...")
try:
    circuit_img = pygame.image.load('circuit.png')
    
    img_width, img_height = circuit_img.get_size()
    aspect_ratio = img_width / img_height
    
    if aspect_ratio > (MAP_WIDTH / NATIVE_HEIGHT):
        new_width = MAP_WIDTH
        new_height = int(MAP_WIDTH / aspect_ratio)
    else:
        new_height = NATIVE_HEIGHT
        new_width = int(NATIVE_HEIGHT * aspect_ratio)
    
    circuit_img = pygame.transform.scale(circuit_img, (new_width, new_height))
    circuit_x = (MAP_WIDTH - new_width) // 2
    circuit_y = (NATIVE_HEIGHT - new_height) // 2
    
    print(f">>> Circuit map loaded: {new_width}x{new_height}")
except Exception as e:
    print(f">>> WARNING: Could not load circuit image: {e}")
    circuit_img = None

# Load F1 data
print(">>> INITIALIZING TRACKSHIFT...")
cache_dir = 'cache'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
ff1.Cache.enable_cache(cache_dir)

session = ff1.get_session(year, wknd, ses)
session.load()

# Get event name
event_info = session.event
if hasattr(event_info, 'EventName'):
    event_name = str(event_info.EventName)
elif hasattr(event_info, 'Location'):
    event_name = str(event_info.Location)
else:
    event_name = "RACE"

# Fonts
font_large = pygame.font.SysFont('courier', 24, bold=True)
font_med = pygame.font.SysFont('courier', 20, bold=True)
font_small = pygame.font.SysFont('courier', 16, bold=True)
font_tiny = pygame.font.SysFont('courier', 12, bold=True)

# Global normalization parameters
track_x_min = None
track_x_max = None
track_y_min = None
track_y_max = None
track_scale = None
track_x_offset = None
track_y_offset = None

def normalize_coords_single(x, y):
    """Normalize a single coordinate using global track parameters"""
    if track_scale is None:
        return 0, 0
    
    x_scaled = int((x - track_x_min) * track_scale + track_x_offset)
    y_scaled = int((y - track_y_min) * track_scale + track_y_offset)
    
    return x_scaled, y_scaled

def setup_normalization(all_x, all_y, margin=30):
    """Setup global normalization parameters from track data"""
    global track_x_min, track_x_max, track_y_min, track_y_max
    global track_scale, track_x_offset, track_y_offset
    
    track_x_min = np.min(all_x)
    track_x_max = np.max(all_x)
    track_y_min = np.min(all_y)
    track_y_max = np.max(all_y)
    
    x_range = track_x_max - track_x_min
    y_range = track_y_max - track_y_min
    
    track_scale = min((MAP_WIDTH - 2*margin) / x_range, (NATIVE_HEIGHT - 2*margin) / y_range)
    
    x_scaled_range = x_range * track_scale
    y_scaled_range = y_range * track_scale
    
    track_x_offset = (MAP_WIDTH - x_scaled_range) / 2
    track_y_offset = (NATIVE_HEIGHT - y_scaled_range) / 2

# Load complete race timeline for each driver
print(">>> LOADING RACE DATA...")
driver_data = {}
all_x = []
all_y = []
lap_distances = {}  # Store distance per lap for accurate position calculation

for driver in drivers:
    try:
        laps = session.laps.pick_drivers(driver)
        
        if len(laps) > 0:
            all_telemetry = []
            cumulative_time = 0
            lap_distance_list = []
            
            for lap_num, lap in laps.iterlaps():
                try:
                    tel = lap.get_car_data().add_distance()
                    pos = lap.get_pos_data()
                    
                    lap_time = lap['LapTime']
                    if pd.isna(lap_time):
                        continue
                    
                    lap_duration = lap_time.total_seconds()
                    
                    tel_data = pd.merge(tel, pos, left_index=True, right_index=True, how='inner')
                    
                    if len(tel_data) == 0:
                        continue
                    
                    # Get max distance for this lap (lap length)
                    lap_length = tel_data['Distance'].max()
                    lap_distance_list.append(lap_length)
                    
                    num_points = len(tel_data)
                    time_per_point = lap_duration / num_points
                    
                    for idx, row in tel_data.iterrows():
                        all_telemetry.append({
                            'time': cumulative_time + (idx * time_per_point),
                            'x': row['X'],
                            'y': row['Y'],
                            'speed': row['Speed'],
                            'distance': row['Distance'],
                            'lap': lap_num
                        })
                    
                    cumulative_time += lap_duration
                    
                except Exception as e:
                    continue
            
            if all_telemetry:
                telemetry_df = pd.DataFrame(all_telemetry)
                
                driver_data[driver] = {
                    'telemetry': telemetry_df,
                    'color': DRIVER_COLORS.get(driver, (255, 255, 255)),
                    'total_time': cumulative_time
                }
                
                lap_distances[driver] = lap_distance_list
                
                all_x.extend(telemetry_df['x'].values)
                all_y.extend(telemetry_df['y'].values)
                
                print(f">>> {driver}: {len(laps)} laps, {len(telemetry_df)} points, {cumulative_time:.1f}s")
        
    except Exception as e:
        print(f">>> Failed to load {driver}: {e}")

if not driver_data:
    print(">>> ERROR: No driver data loaded!")
    sys.exit(1)

# Calculate average lap distance
avg_lap_distance = np.mean([dist for distances in lap_distances.values() for dist in distances])
print(f">>> Average lap distance: {avg_lap_distance:.1f}m")

# Setup global normalization
setup_normalization(np.array(all_x), np.array(all_y))

# Find maximum race duration
max_race_time = max([data['total_time'] for data in driver_data.values()])
print(f">>> Race duration: {max_race_time:.1f}s ({max_race_time/60:.1f} minutes)")

# CRT scanlines
def apply_crt_effect(surface):
    scanline_surface = pygame.Surface(surface.get_size(), pygame.SRCALPHA)
    for y in range(0, surface.get_height(), 2):
        pygame.draw.line(scanline_surface, COLORS['scanline'], 
                        (0, y), (surface.get_width(), y), 1)
    surface.blit(scanline_surface, (0, 0))

# Function to get driver position at specific time
def get_position_at_time(driver_name, current_time):
    """Get driver's position at a specific race time"""
    data = driver_data[driver_name]
    telemetry = data['telemetry']
    
    time_diff = abs(telemetry['time'] - current_time)
    closest_idx = time_diff.idxmin()
    
    if time_diff.iloc[closest_idx] > 5.0:
        return None
    
    row = telemetry.iloc[closest_idx]
    
    # Calculate total race distance (laps completed + current lap distance)
    lap_num = row['lap']
    distance_in_lap = row['distance']
    
    # Total distance = (completed laps * avg lap distance) + distance in current lap
    total_race_distance = ((lap_num - 1) * avg_lap_distance) + distance_in_lap
    
    return {
        'x': row['x'],
        'y': row['y'],
        'speed': row['speed'],
        'distance': distance_in_lap,
        'total_distance': total_race_distance,
        'lap': lap_num,
        'time': row['time']
    }

# Animation state
animation_running = True
paused = False
speed_multiplier = 5.0
current_race_time = 0.0
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
                current_race_time = min(current_race_time + 10, max_race_time)
            elif event.key == pygame.K_LEFT:
                current_race_time = max(current_race_time - 10, 0)
            elif event.key == pygame.K_UP:
                speed_multiplier = min(speed_multiplier + 1, 20)
            elif event.key == pygame.K_DOWN:
                speed_multiplier = max(speed_multiplier - 1, 0.5)
            elif event.key == pygame.K_r:
                current_race_time = 0
    
    if not paused:
        current_race_time += (dt / 1000.0) * speed_multiplier
        if current_race_time >= max_race_time:
            current_race_time = 0
    
    canvas.fill(COLORS['bg_dark'])
    
    # Draw circuit background image
    if circuit_img is not None:
        canvas.blit(circuit_img, (circuit_x, circuit_y))
    
    try:
        # Get positions for all drivers at current race time
        driver_positions = []
        
        for driver_name, data in driver_data.items():
            position = get_position_at_time(driver_name, current_race_time)
            
            if position is not None:
                x_scaled, y_scaled = normalize_coords_single(position['x'], position['y'])
                
                driver_positions.append({
                    'driver': driver_name,
                    'x': x_scaled,
                    'y': y_scaled,
                    'speed': position['speed'],
                    'distance': position['distance'],
                    'total_distance': position['total_distance'],
                    'lap': position['lap'],
                    'time': position['time'],
                    'color': data['color']
                })
        
        # Sort by TOTAL race distance (accounts for lap differences)
        driver_positions.sort(key=lambda x: x['total_distance'], reverse=True)
        
        # Calculate gaps
        if len(driver_positions) > 0:
            leader_distance = driver_positions[0]['total_distance']
            for pos in driver_positions:
                pos['gap'] = leader_distance - pos['total_distance']
        
        # Draw all drivers (NO TRAILS - just the cars)
        for pos_data in driver_positions:
            driver_color = pos_data['color']
            x, y = pos_data['x'], pos_data['y']
            
            # Validate coordinates
            if not (0 <= x < MAP_WIDTH and 0 <= y < NATIVE_HEIGHT):
                continue
            
            # Draw car (larger and more visible)
            pygame.draw.circle(canvas, driver_color, (int(x), int(y)), 7)
            pygame.draw.circle(canvas, COLORS['text_white'], (int(x), int(y)), 7, 2)
            
            # Draw driver label
            label = font_tiny.render(pos_data['driver'], True, driver_color)
            label_bg = pygame.Surface((label.get_width() + 4, label.get_height()), pygame.SRCALPHA)
            label_bg.fill((0, 0, 0, 180))
            canvas.blit(label_bg, (int(x) - label.get_width()//2 - 2, int(y) - 18))
            canvas.blit(label, (int(x) - label.get_width()//2, int(y) - 18))
        
        # # === LEADERBOARD ===
        # leaderboard_width = 150
        # leaderboard_height = 20 + len(driver_positions) * 18 + 10
        # leaderboard_x = 10
        # leaderboard_y = 10
        
        # leaderboard_bg = pygame.Surface((leaderboard_width, leaderboard_height), pygame.SRCALPHA)
        # leaderboard_bg.fill((*COLORS['leaderboard_bg'], 220))
        # canvas.blit(leaderboard_bg, (leaderboard_x, leaderboard_y))
        
        # pygame.draw.rect(canvas, COLORS['leaderboard_border'], 
        #                 (leaderboard_x, leaderboard_y, leaderboard_width, leaderboard_height), 2)
        
        # lb_y = leaderboard_y + 8
        # lb_title = font_small.render("LEADERBOARD", True, COLORS['text_yellow'])
        # canvas.blit(lb_title, (leaderboard_x + 8, lb_y))
        # lb_y += 20
        
        # for idx, pos_data in enumerate(driver_positions):
        #     pos_num = font_tiny.render(f"{idx+1}", True, COLORS['text_dim'])
        #     canvas.blit(pos_num, (leaderboard_x + 8, lb_y))
            
        #     pygame.draw.circle(canvas, pos_data['color'], (leaderboard_x + 25, lb_y + 6), 3)
            
        #     driver_text = font_tiny.render(pos_data['driver'], True, COLORS['text_white'])
        #     canvas.blit(driver_text, (leaderboard_x + 35, lb_y))
            
        #     # Show gap to leader or "LEAD"
        #     if idx == 0:
        #         gap_text = font_tiny.render("LEAD", True, COLORS['text_yellow'])
        #     else:
        #         gap_meters = pos_data['gap']
        #         if gap_meters < 1000:
        #             gap_str = f"+{gap_meters:.0f}m"
        #         else:
        #             gap_str = f"+{gap_meters/1000:.1f}k"
        #         gap_text = font_tiny.render(gap_str, True, COLORS['text_dim'])
        #     canvas.blit(gap_text, (leaderboard_x + 75, lb_y))
            
        #     lb_y += 18
        
        # === RIGHT PANEL ===
        pygame.draw.rect(canvas, COLORS['panel_bg'], (PANEL_X, 0, PANEL_WIDTH, NATIVE_HEIGHT))
        pygame.draw.line(canvas, COLORS['panel_border'], (PANEL_X, 0), (PANEL_X, NATIVE_HEIGHT), 3)
        
        y_pos = 16
        
        title = font_large.render("RACE", True, COLORS['text_yellow'])
        canvas.blit(title, (PANEL_X + 10, y_pos))
        y_pos += 28
        
        event_display = event_name.split(' ')[0][:8] if ' ' in event_name else event_name[:8]
        event_text = font_small.render(event_display.upper(), True, COLORS['text_cyan'])
        canvas.blit(event_text, (PANEL_X + 10, y_pos))
        y_pos += 24
        
        pygame.draw.line(canvas, COLORS['panel_border'], 
                        (PANEL_X + 6, y_pos), (PANEL_X + PANEL_WIDTH - 6, y_pos), 2)
        y_pos += 12
        
        # Race time
        time_label = font_small.render("TIME", True, COLORS['text_dim'])
        canvas.blit(time_label, (PANEL_X + 10, y_pos))
        y_pos += 18
        
        minutes = int(current_race_time // 60)
        seconds = int(current_race_time % 60)
        time_str = f"{minutes:02d}:{seconds:02d}"
        time_value = font_med.render(time_str, True, COLORS['text_white'])
        canvas.blit(time_value, (PANEL_X + 10, y_pos))
        y_pos += 28
        
        # Animation speed
        multi_label = font_small.render("SPEED", True, COLORS['text_dim'])
        canvas.blit(multi_label, (PANEL_X + 10, y_pos))
        y_pos += 18
        multi_value = font_med.render(f"x{speed_multiplier:.1f}", True, COLORS['text_magenta'])
        canvas.blit(multi_value, (PANEL_X + 10, y_pos))
        
        # === CONTROLS BOX ===
        control_box_width = 140
        control_box_height = 80
        control_box_x = 10
        control_box_y = NATIVE_HEIGHT - control_box_height - 10
        
        control_bg = pygame.Surface((control_box_width, control_box_height), pygame.SRCALPHA)
        control_bg.fill((*COLORS['control_box_bg'], 200))
        canvas.blit(control_bg, (control_box_x, control_box_y))
        
        pygame.draw.rect(canvas, COLORS['control_box_border'], 
                        (control_box_x, control_box_y, control_box_width, control_box_height), 2)
        
        ctrl_y = control_box_y + 8
        ctrl_x = control_box_x + 6
        
        ctrl_title = font_tiny.render("CONTROLS", True, COLORS['text_cyan'])
        canvas.blit(ctrl_title, (ctrl_x, ctrl_y))
        ctrl_y += 14
        
        controls = [
            "PAUSE - Space",
            "SKIP - Left/Right",
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
