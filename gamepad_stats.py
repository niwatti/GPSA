import os
import argparse
import datetime

import win32api
import win32con
import win32gui

import pygame
from pygame._sdl2 import Window

from colorama import Style
from threading import Thread, Event
import math
import numpy as np
from functools import reduce
import csv

version = "0.4"

# MEASURE Thread FPS
MEASURE_FRAME_RATE = 1000
SAMPLING_RATE = 10 #every 10 to 11ms

# ANALYZE MAX MSs
MAX_MS = 1000
AGGR_MAX_MS = 10000

# ANALYZE THRESHOLDS
THRESHOLD_STICK_BIG_MOVEMENT = 0.1
THRESHOLD_STICK_KEEP_MOVING = 0.015
THRESHOLD_STICK_ACCELERATION = 0.01

# JOYSTICK Step Accuracy, HISTOGRAM BINS for calculating mode
JOYSTICK_HIST_STEPS = 32

BUTTONS_MAP = {'A': 0, 'B': 1, 'X': 2, 'Y': 3, 'SELECT': 4, 'HOME': 5, 'START': 6, 'LS': 7, 'RS': 8, 'LB': 9, 'RB': 10, 'UP': 11, 'DOWN': 12, 'LEFT': 13, 'RIGHT': 14, 'TOUCHPAD': 15}

PIN_ON_TOP_POS = (1920 - 460, round((1080 + 250)/ 2))

HISTORY_LINE_DEFAULT_COLOR = (200, 200, 200)
HISTORY_LINE_BIG_MVMT_COLOR = (150, 150, 255)
HISTORY_LINE_TURNED_COLOR = (150, 255, 150)
HISTORY_LINE_BIG_TURN_COLOR = (255, 150, 150)

def prepare():
    os.system('cls' if os.name == 'nt' else 'clear')
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"    #get key events while the window is not focused
    print()
    print(f" ____    ____    ____    ______     ")
    print(f"/\  _`\ /\  _`\ /\  _`\ /\  _  \    ")
    print(f"\ \ \L\_\ \ \L\ \ \,\L\_\ \ \L\ \   ")
    print(f" \ \ \L_L\ \ ,__/\/_\__ \\\\ \  __ \  ")
    print(f"  \ \ \/, \ \ \/   /\ \L\ \ \ \/\ \ ")
    print(f"   \ \____/\ \_\   \ `\____\ \_\ \_\\")
    print(f"    \/___/  \/_/    \/_____/\/_/\/_/")
    print(f"v{version} by monoru (https://monoru.trie-marketing.co.jp/)")
    print()

def init_joystick():
    joystick = get_a_joystick()
    if joystick is None:
        print("Please connect a game pad.")
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.JOYDEVICEADDED:
                    joystick = get_a_joystick()
                    if joystick:
                        return joystick
    return joystick

def get_a_joystick():
    joysticks = []

    joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

    if joysticks:
        # List all connected controllers
        for idx, joystick in enumerate(joysticks):
            print(f"{idx + 1}. {joystick.get_name()}")

        # Automatic selection if only one controller is connected
        if len(joysticks) == 1:
            joystick = joysticks[0]
        else:
            # Controller selection for multiple controllers
            selected_index = input("Please enter the index of the controller:")
            try:
                selected_index = int(selected_index) - 1
                if 0 <= selected_index < len(joysticks):
                    joystick = joysticks[selected_index]
                else:
                    print("Invalid index. Defaulting to the first controller.")
                    joystick = joysticks[0]
            except ValueError:
                print("Invalid input. Defaulting to the first controller.")
                joystick = joysticks[0]

        joystick.init()
        print(f"\n{Style.BRIGHT}Connected controller: {joystick.get_name()}{Style.RESET_ALL}")
        return joystick
    return None

def calc_stick_mode(stat):
    """!!!Deprecated!!!
    Calculates Stick Mode of the Histogram.
    It uses a lower value when mode is less than zero and an upper value when mode is more than zero, as DualSense sticks seem to use the algorithm.
    | <- | <- | -> | -> |
    -1        0         1
    """

    #num_bins = round(JOYSTICK_HIST_STEPS / 2)
    #lower_hist, lower_bins = np.histogram(stat, num_bins, [-1, 0])
    #upper_hist, upper_bins = np.histogram(stat, num_bins, [0, 1])
#
    #if lower_hist.max() > upper_hist.max():
    #    return lower_bins[lower_hist.argmax()]
    #else:
    #    upper_mode_idx = upper_hist.argmax() + 1
    #    if upper_mode_idx >= num_bins: return 1.0
    #    mode = upper_bins[upper_mode_idx]
    #    return mode


def calc_stats(stats):
    """Calculates gamepad stats from raw input time series data.
    
    Args:
        stats(Array): An time series array of a game pad input data.
    
    Returns:
        dict[str, float] or None: Calculation result. None if no data in stats.
    """

    if not stats["timestamps"] or len(stats["timestamps"]) < 0:
        return None
    
    result = {
        "left_stick": {
            "x": {
                "1s": 0,
                "10s": 0,
                "mode": 0,
                "sum": 0,
                "hist": None,
                "min": 0,
                "max": 0,
                "amp": 0,
            },
            "y": {
                "1s": 0,
                "10s": 0,
                "mode": 0,
                "sum": 0,
                "hist": None,
                "min": 0,
                "max": 0,
                "amp": 0,
            },
        },
        "right_stick": {
            "x": {
                "1s": 0,
                "10s": 0,
                "mode": 0,
                "sum": 0,
                "hist": None,
                "min": 0,
                "max": 0,
                "amp": 0,
            },
            "y": {
                "1s": 0,
                "10s": 0,
                "mode": 0,
                "sum": 0,
                "hist": None,
                "min": 0,
                "max": 0,
                "amp": 0,
            },
        },
        "count_1s": 0,
        "count": 0
    }

    cur_ms = stats["timestamps"][-1]
    for idx, stat in enumerate(stats["timestamps"]):
        if cur_ms - stat < 1000:
            result["left_stick"]["x"]["1s"] += stats["lx"][idx]
            result["left_stick"]["y"]["1s"] += stats["ly"][idx]
            result["right_stick"]["x"]["1s"] += stats["rx"][idx]
            result["right_stick"]["y"]["1s"] += stats["ry"][idx]
            result["count_1s"] += 1

        result["left_stick"]["x"]["10s"] += stats["lx"][idx]
        result["left_stick"]["y"]["10s"] += stats["ly"][idx]
        result["right_stick"]["x"]["10s"] += stats["rx"][idx]
        result["right_stick"]["y"]["10s"] += stats["ry"][idx]
        result["count"] += 1

    if result["count"] == 0:
        return None
    
    # 1s Avg.
    if result["count_1s"] > 0:
        result["left_stick"]["x"]["1s"] = result["left_stick"]["x"]["1s"] / result["count_1s"]
        result["left_stick"]["y"]["1s"] = result["left_stick"]["y"]["1s"] / result["count_1s"]
        result["right_stick"]["x"]["1s"] = result["right_stick"]["x"]["1s"] / result["count_1s"]
        result["right_stick"]["y"]["1s"] = result["right_stick"]["y"]["1s"] / result["count_1s"]

    # 10s Avg.
    result["left_stick"]["x"]["10s"] = result["left_stick"]["x"]["10s"] / result["count"]
    result["left_stick"]["y"]["10s"] = result["left_stick"]["y"]["10s"] / result["count"]
    result["right_stick"]["x"]["10s"] = result["right_stick"]["x"]["10s"] / result["count"]
    result["right_stick"]["y"]["10s"] = result["right_stick"]["y"]["10s"] / result["count"]

    # Histogram
    result["left_stick"]["x"]["hist"] = np.histogram(stats["lx"], JOYSTICK_HIST_STEPS)
    result["left_stick"]["y"]["hist"] = np.histogram(stats["ly"], JOYSTICK_HIST_STEPS)
    result["right_stick"]["x"]["hist"] = np.histogram(stats["rx"], JOYSTICK_HIST_STEPS)
    result["right_stick"]["y"]["hist"] = np.histogram(stats["ry"], JOYSTICK_HIST_STEPS)

    # Mode.
    #result["left_stick"]["x"]["mode"] = calc_stick_mode(stats["lx"])
    #result["left_stick"]["y"]["mode"] = calc_stick_mode(stats["ly"])
    #result["right_stick"]["x"]["mode"] = calc_stick_mode(stats["rx"])
    #result["right_stick"]["y"]["mode"] = calc_stick_mode(stats["ry"])
    hist, bins = result["left_stick"]["x"]["hist"]; max_idx = hist.argmax(); result["left_stick"]["x"]["mode"] = (bins[max_idx], bins[max_idx + 1])
    hist, bins = result["left_stick"]["y"]["hist"]; max_idx = hist.argmax(); result["left_stick"]["y"]["mode"] = (bins[max_idx], bins[max_idx + 1])
    hist, bins = result["right_stick"]["x"]["hist"]; max_idx = hist.argmax(); result["right_stick"]["x"]["mode"] = (bins[max_idx], bins[max_idx + 1])
    hist, bins = result["right_stick"]["y"]["hist"]; max_idx = hist.argmax(); result["right_stick"]["y"]["mode"] = (bins[max_idx], bins[max_idx + 1])

    # MIN.
    result["left_stick"]["x"]["min"] = np.min(stats["lx"])
    result["left_stick"]["y"]["min"] = np.min(stats["ly"])
    result["right_stick"]["x"]["min"] = np.min(stats["rx"])
    result["right_stick"]["y"]["min"] = np.min(stats["ry"])

    # MAX.
    result["left_stick"]["x"]["max"] = np.max(stats["lx"])
    result["left_stick"]["y"]["max"] = np.max(stats["ly"])
    result["right_stick"]["x"]["max"] = np.max(stats["rx"])
    result["right_stick"]["y"]["max"] = np.max(stats["ry"])
    
    # AMP.
    result["left_stick"]["x"]["amp"] = result["left_stick"]["x"]["max"] - result["left_stick"]["x"]["min"]
    result["left_stick"]["y"]["amp"] = result["left_stick"]["y"]["max"] - result["left_stick"]["y"]["min"]
    result["right_stick"]["x"]["amp"] = result["right_stick"]["x"]["max"] - result["right_stick"]["x"]["min"]
    result["right_stick"]["y"]["amp"] = result["right_stick"]["y"]["max"] - result["right_stick"]["y"]["min"]

    return result


def plot_txt(screen, font, text, antialias = True, color = (255, 255, 255), transparent = False, **kwargs):
    rendered = font.render(text, antialias, color)
    rect = rendered.get_rect(**kwargs)
    if (transparent):
        transparent_surface = pygame.Surface((rendered.get_width(), rendered.get_height()))
        transparent_surface.fill((128, 128, 128))
        transparent_surface.blit(rendered, pygame.Rect(0, 0, 10, 10))
        transparent_surface.set_alpha(60)
        rendered = transparent_surface

    screen.blit(rendered, rect)

def fix_stick_val(val):
    if 0 < val:
        return (math.ceil(val * 100000) / 100000 + 0.00001) / 0.99998
    elif val < 0:
        return (math.floor(val * 100000) / 100000 + 0.00002) / 0.99998
    return val

def calc_color(rate):
    # |        LB         |         B         |         DB     |            DG          |         G         |           GY        |           Y         |           O         |          R        |          P         |
    # |(128, 128, 255) - 128 - (0, 0, 255) - 128 - (0, 0, 128) - 128 - (0, 128, 128) - 128 - (0, 255, 0) - 128 - (128, 255, 0) - 128 - (255, 255, 0) - 128 - (255, 128, 0) - 128 - (255, 0, 0) - 128 - (255, 0, 128)
    # |(128, 128, 255)(0, 0, 255)         (0, 0, 128)     (0, 128, 128)            (0, 255, 0)          (128, 255, 0)        (255, 255, 0)         (255, 128, 0)         (255, 0, 0)          (255, 0, 128)
    # |                   |                   |                |                        |                   |                     |                     |                     |                   |

    red = 0
    green = 0
    blue = 0
    if rate < 1 / 9:
        red = (0.5 - (rate * 8)) * 255
        green = (0.5 - (rate * 8)) * 255
    elif 4 / 9 <= rate:
        red = (rate - 4 / 9) * 9 / 2 * 255

    if 2 / 9 <= rate and rate < 6 / 9:
        green = (rate - 2 / 9) * 9 / 2 * 255
    elif 6 / 9 <= rate:
        green = (1 - (rate - 6 / 9) * 9 / 2) * 255

    blue = 0
    if rate < 2 / 9:
        blue = ( 1 - (rate - 1 / 9) * 9 / 2) * 255
    elif rate < 3 / 9:
        blue = 128
    elif 8 / 9 <= rate:
        blue = (rate - 8 / 9) * 9 / 2 * 255

    if red < 0: red = 0
    if red > 255: red = 255
    if green < 0: green = 0
    if green > 255: green = 255
    if blue < 0: blue = 0
    if blue > 255: blue = 255
    return (red, green, blue)

def draw_histogram(screen, center_x, center_y, hist, font, guide_radius, first_line_dist, line_dist, horizontal=True):
    if (horizontal):
        pygame.draw.rect(screen, (0, 0, 0), (center_x - guide_radius, center_y + first_line_dist + line_dist * 5, guide_radius * 2, 20))
    else:
        pygame.draw.rect(screen, (0, 0, 0), (center_x + first_line_dist + line_dist * 4, center_y - guide_radius, 20, guide_radius * 2))

    nonzero_idxs = np.nonzero(hist[0])[0]
    if np.count_nonzero(hist[0]) > 0:
        max_count = hist[0].max()
        start_value = hist[1][nonzero_idxs[0]]
        amp = hist[1][nonzero_idxs[-1] + 1] - start_value

        for idx in nonzero_idxs:
            count = hist[0][idx]
            color = calc_color(count / max_count)

            frm = hist[1][idx]
            to = hist[1][idx + 1]
            if (horizontal):
                left = center_x - guide_radius + guide_radius * 2 * ((frm - start_value) / amp)
                top = center_y + first_line_dist + line_dist * 5
                width = guide_radius * 2 * ((to - frm) / amp)
                pygame.draw.rect(screen, color, (left, top, width, 20))
            else:
                left = center_x + first_line_dist + line_dist * 4
                height = guide_radius * 2 * ((to - frm) / amp)
                top = center_y + guide_radius - guide_radius * 2 * ((frm - start_value) / amp) - height
                pygame.draw.rect(screen, color, (left, top, 20, height))

def draw_history_lines(screen, stat_x, stat_y, center_x, center_y, font, guide_radius, first_line_dist, line_dist):
    left = center_x + guide_radius + 20
    x_top = center_y + first_line_dist - 30
    y_top = x_top + line_dist * 4.5
    height = 80

    draw_history_line(screen, stat_x, x_top, left, guide_radius * 2, height)
    draw_history_line(screen, stat_y, y_top, left, guide_radius * 2, height)

    plot_txt(screen, font, f'X', center=(left - 5, x_top + height / 2))
    plot_txt(screen, font, f'Y', center=(left - 5, y_top + height / 2))


def draw_history_line(screen, stat, top, left, width, height, transparent=False, horizontal=True, colors = None):
    if len(stat) <= 0:
        return

    # Draw Area
    if not transparent:
        pygame.draw.rect(screen, (50, 50, 50), (left, top, width, height))

    x_count = len(stat)
    last_pos = (left + width, top + height - ((- stat[0] + 1) / 2) * height)
    if not horizontal:
        last_pos = (left + width - ((- stat[0] + 1) / 2) * width, top + height)

    # Draw Line

    for idx, val in enumerate(stat):
        # idx: 0 -> (count - 1)
        new_pos = (0, 0)
        if horizontal:
            new_pos = (left + width - (idx / x_count) * width, top + height - ((-val + 1)/ 2) * height)
        else:
            new_pos = (left + width - ((-val + 1)/ 2) * width, top + height - (idx / x_count) * height)

        color = HISTORY_LINE_DEFAULT_COLOR
        if colors:
            color = colors[idx]

        pygame.draw.line(screen, color, last_pos, new_pos, 2)
        last_pos = new_pos

def stick_mode_visualize(screen, joystick, stats, stop_event, change_event):
    """GPSA stick mode visualize function.
    Main loop of the window drawings.
    Use this with a new Thread.

    Args:
        screen - 
        joystick - 
        stats - 
        stop_event (Event):
        change_event (Event):

    Returns:
        None

    """

    clock = pygame.time.Clock()
    font_label = pygame.font.Font(None, 16)
    font_avg = pygame.font.Font(None, 24)
    center_left = (160, 130)
    center_right = (680, 130)
    guide_radius = 100
    line_dist = 20
    first_line_dist = 140

    # Main loop of the window drawings
    while not stop_event.is_set() and not change_event.is_set():
        screen.fill((30, 30, 30))

        # Draws stick circles
        #   RIGHT
        pygame.draw.circle(screen, (200, 200, 200), center_right, guide_radius, 1)
        pygame.draw.line(screen, (200, 200, 200), (center_right[0] - guide_radius, center_right[1]), (center_right[0] + guide_radius, center_right[1]), 1)
        pygame.draw.line(screen, (200, 200, 200), (center_right[0], center_right[1] - guide_radius), (center_right[0], center_right[1] + guide_radius), 1)
        #   LEFT
        pygame.draw.circle(screen, (200, 200, 200), center_left, guide_radius, 1)
        pygame.draw.line(screen, (200, 200, 200), (center_left[0] - guide_radius, center_left[1]), (center_left[0] + guide_radius, center_left[1]), 1)
        pygame.draw.line(screen, (200, 200, 200), (center_left[0], center_left[1] - guide_radius), (center_left[0], center_left[1] + guide_radius), 1)

        # Get current positions of the sticks
        lx = fix_stick_val(joystick.get_axis(0))
        ly = fix_stick_val(joystick.get_axis(1))
        rx = fix_stick_val(joystick.get_axis(2))
        ry = fix_stick_val(joystick.get_axis(3))


        # Draws current position of the sticks

        #   LEFT
        left_stick_position = (center_left[0] + int(lx * guide_radius), center_left[1] + int(ly * guide_radius))
        pygame.draw.circle(screen, (255, 255, 255), left_stick_position, 3)
        plot_txt(screen, font_avg, f'{lx:.5f}', center = (center_left[0], center_left[1] + first_line_dist))
        plot_txt(screen, font_avg, f'{ly:.5f}', center =(center_left[0] + guide_radius + 70, center_left[1]))

        #   RIGHT
        right_stick_position = (center_right[0] + int(rx * guide_radius), center_right[1] + int(ry * guide_radius))
        pygame.draw.circle(screen, (255, 255, 255), right_stick_position, 3)
        plot_txt(screen, font_avg, f'{rx:.5f}', center=(center_right[0], center_right[1] + first_line_dist))
        plot_txt(screen, font_avg, f'{ry:.5f}', center=(center_right[0] + guide_radius + 70, center_right[1]))

        #   BAR
        #     RX
        pygame.draw.rect(screen, (200, 200, 200), (center_right[0] - guide_radius, center_right[1] + guide_radius + 10, guide_radius * 2, 20))
        if rx < 0:
            pygame.draw.rect(screen, (100, 100, 100), (center_right[0] - guide_radius * (- rx), center_right[1] + guide_radius + 10, guide_radius * (- rx), 20))
        else:
            pygame.draw.rect(screen, (100, 100, 100), (center_right[0], center_right[1] + guide_radius + 10, guide_radius * (rx), 20))

        #     RY
        pygame.draw.rect(screen, (200, 200, 200), (center_right[0] + guide_radius + 10, center_right[1] - guide_radius, 20, guide_radius * 2))
        if ry < 0:
            pygame.draw.rect(screen, (100, 100, 100), (center_right[0] + guide_radius + 10, center_right[1] - guide_radius * (- ry), 20, guide_radius * (- ry)))
        else:
            pygame.draw.rect(screen, (100, 100, 100), (center_right[0] + guide_radius + 10, center_right[1], 20, guide_radius * (ry)))

        #     LX
        pygame.draw.rect(screen, (200, 200, 200), (center_left[0] - guide_radius, center_left[1] + guide_radius + 10, guide_radius * 2, 20))
        if lx < 0:
            pygame.draw.rect(screen, (100, 100, 100), (center_left[0] - guide_radius * (- lx), center_left[1] + guide_radius + 10, guide_radius * (- lx), 20))
        else:
            pygame.draw.rect(screen, (100, 100, 100), (center_left[0], center_left[1] + guide_radius + 10, guide_radius * (lx), 20))

        #     LY
        pygame.draw.rect(screen, (200, 200, 200), (center_left[0] + guide_radius + 10, center_left[1] - guide_radius, 20, guide_radius * 2))
        if ly < 0:
            pygame.draw.rect(screen, (100, 100, 100), (center_left[0] + guide_radius + 10, center_left[1] - guide_radius * (- ly), 20, guide_radius * (- ly)))
        else:
            pygame.draw.rect(screen, (100, 100, 100), (center_left[0] + guide_radius + 10, center_left[1], 20, guide_radius * (ly)))


        # Draws statistics
        analyzed_stats = calc_stats(stats)
        if analyzed_stats:
            # Labels
            plot_txt(screen, font_label, f'10s Histogram of {JOYSTICK_HIST_STEPS} bins.', center=(center_left[0], center_left[1] + first_line_dist + line_dist * 4.5))

            # 1s Avg.
            plot_txt(screen, font_label, "1s Avg.", center=(center_left[0] - 120, center_left[1] + first_line_dist + line_dist))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["left_stick"]["x"]["1s"], 5):.5f}', center=(center_left[0] - 50, center_left[1] + first_line_dist + line_dist))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["left_stick"]["y"]["1s"], 5):.5f}', center=(center_left[0] + 50, center_left[1] + first_line_dist + line_dist))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["right_stick"]["x"]["1s"], 5):.5f}', center=(center_right[0] - 50, center_right[1] + first_line_dist + line_dist))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["right_stick"]["y"]["1s"], 5):.5f}', center=(center_right[0] + 50, center_right[1] +first_line_dist + line_dist))

            # 10s Avg.
            plot_txt(screen, font_label, "10s Avg.", center=(center_left[0] - 120, center_left[1] + first_line_dist + line_dist * 2))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["left_stick"]["x"]["10s"], 5):.5f}', center=(center_left[0] - 50, center_left[1] + first_line_dist + line_dist * 2))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["left_stick"]["y"]["10s"], 5):.5f}', center=(center_left[0] + 50, center_left[1] + first_line_dist + line_dist * 2))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["right_stick"]["x"]["10s"], 5):.5f}', center=(center_right[0] - 50, center_right[1] + first_line_dist + line_dist * 2))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["right_stick"]["y"]["10s"], 5):.5f}', center=(center_right[0] + 50, center_right[1] +first_line_dist + line_dist * 2))

            # Amp.
            plot_txt(screen, font_label, f'Amp.', center=(center_left[0] - 120, center_left[1] + first_line_dist + line_dist * 3))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["left_stick"]["x"]["amp"], 5):.5f}', center=(center_left[0] - 50, center_left[1] + first_line_dist + line_dist * 3))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["left_stick"]["y"]["amp"], 5):.5f}', center=(center_left[0] + 50, center_left[1] + first_line_dist + line_dist * 3))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["right_stick"]["x"]["amp"], 5):.5f}', center=(center_right[0] - 50, center_right[1] + first_line_dist + line_dist * 3))
            plot_txt(screen, font_avg, f'{round(analyzed_stats["right_stick"]["y"]["amp"], 5):.5f}', center=(center_right[0] + 50, center_right[1] +first_line_dist + line_dist * 3))

            # Mode.
            plot_txt(screen, font_label, f'Mode', center=(center_left[0] - 120, center_left[1] + first_line_dist + line_dist * 7))
            plot_txt(screen, font_avg, f'[ {round(analyzed_stats["left_stick"]["x"]["mode"][0], 5):.5f}, {round(analyzed_stats["left_stick"]["x"]["mode"][1], 5):.5f} )', center=(center_left[0], center_left[1] + first_line_dist + line_dist * 7))
            plot_txt(screen, font_avg, f'[ {round(analyzed_stats["left_stick"]["y"]["mode"][0], 5):.5f}, {round(analyzed_stats["left_stick"]["y"]["mode"][1], 5):.5f} )', center=(center_left[0] + first_line_dist + line_dist * 9, center_left[1]))
            plot_txt(screen, font_avg, f'[ {round(analyzed_stats["right_stick"]["x"]["mode"][0], 5):.5f}, {round(analyzed_stats["right_stick"]["x"]["mode"][1], 5):.5f} )', center=(center_right[0], center_right[1] + first_line_dist + line_dist * 7))
            plot_txt(screen, font_avg, f'[ {round(analyzed_stats["right_stick"]["y"]["mode"][0], 5):.5f}, {round(analyzed_stats["right_stick"]["y"]["mode"][0], 5):.5f} )', center=(center_right[0] + first_line_dist + line_dist * 9, center_right[1]))

            # Histogram Bar
            draw_histogram(screen, center_left[0], center_left[1], analyzed_stats["left_stick"]["x"]["hist"], font_avg, guide_radius, first_line_dist, line_dist)
            draw_histogram(screen, center_left[0], center_left[1], analyzed_stats["left_stick"]["y"]["hist"], font_avg, guide_radius, first_line_dist, line_dist, False)
            draw_histogram(screen, center_right[0], center_right[1], analyzed_stats["right_stick"]["x"]["hist"], font_avg, guide_radius, first_line_dist, line_dist)
            draw_histogram(screen, center_right[0], center_right[1], analyzed_stats["right_stick"]["y"]["hist"], font_avg, guide_radius, first_line_dist, line_dist, False)


        #Draw history lines
        draw_history_lines(screen, stats["lx"], stats["ly"], center_left[0], center_left[1], font_label, guide_radius, first_line_dist, line_dist)
        draw_history_lines(screen, stats["rx"], stats["ry"], center_right[0], center_right[1], font_label, guide_radius, first_line_dist, line_dist)

        # Reflects to the window
        pygame.display.flip()

        # Sets window reflesh rate to 60FPS
        clock.tick(60)

def recorder_mode_visualize(screen, joystick, stats, stop_event, change_event, is_record):
    """GPSA recorder mode visualize function.
    Main loop of the window drawings.
    Use this with a new Thread.

    Args:
        screen - 
        joystick - 
        stats - 
        stop_event (Event):
        change_event (Event):

    Returns:
        None

    """
    clock = pygame.time.Clock()
    font_label = pygame.font.Font(None, 16)
    font_avg = pygame.font.Font(None, 18)
    font_max = pygame.font.Font(None, 22)
    center_left = (70, 70)
    center_right = (300, 70)
    guide_radius = 50
    line_dist = 20
    first_line_dist = 60
    x_first_line_dist = 30

    # Main loop of the window drawings
    while not stop_event.is_set() and not change_event.is_set():
        screen.fill((128, 128, 128))

        # draw water mark
        plot_txt(screen, font_label, 'GPSA by monoru', True, (255, 255, 255), 145, midright = (450, 10))

        # draw timestamp
        if is_record:
            cur_ms = pygame.time.get_ticks()
            plot_txt(screen, font_avg, f'{cur_ms}', midright = (450, 240))
            plot_txt(screen, font_avg, f'{stats["fps"]:.0f}', topright = (450, 20))


        # Draws history lines of the sticks
        #   LEFT
        draw_history_line(screen, stats["lx"], center_left[1] + guide_radius, center_left[0] - guide_radius, guide_radius * 2, 100, True, False, colors=stats["max"]["lx"][ANALYZE_COLOR_KEY])
        draw_history_line(screen, stats["ly"], center_left[1] - guide_radius, center_left[0] + guide_radius, 100, guide_radius * 2, True, True, colors=stats["max"]["ly"][ANALYZE_COLOR_KEY])
        #   RIGHT
        draw_history_line(screen, stats["rx"], center_right[1] + guide_radius, center_right[0] - guide_radius, guide_radius * 2, 100, True, False, colors=stats["max"]["rx"][ANALYZE_COLOR_KEY])
        draw_history_line(screen, stats["ry"], center_right[1] - guide_radius, center_right[0] + guide_radius, 100, guide_radius * 2, True, True, colors=stats["max"]["ry"][ANALYZE_COLOR_KEY])


        # Get current positions of the sticks
        lx = fix_stick_val(joystick.get_axis(0))
        ly = fix_stick_val(joystick.get_axis(1))
        rx = fix_stick_val(joystick.get_axis(2))
        ry = fix_stick_val(joystick.get_axis(3))

        # Draws current position of the sticks
        #   LEFT
        left_stick_position = (center_left[0] + int(lx * guide_radius), center_left[1] + int(ly * guide_radius))
        pygame.draw.circle(screen, (255, 255, 255), left_stick_position, 3)
        plot_txt(screen, font_avg, f'{lx:.5f}', center = (center_left[0], center_left[1] + first_line_dist))
        plot_txt(screen, font_avg, f'{ly:.5f}', center =(center_left[0] + guide_radius + x_first_line_dist, center_left[1]))

        #   RIGHT
        right_stick_position = (center_right[0] + int(rx * guide_radius), center_right[1] + int(ry * guide_radius))
        pygame.draw.circle(screen, (255, 255, 255), right_stick_position, 3)
        plot_txt(screen, font_avg, f'{rx:.5f}', center=(center_right[0], center_right[1] + first_line_dist))
        plot_txt(screen, font_avg, f'{ry:.5f}', center=(center_right[0] + guide_radius + x_first_line_dist, center_right[1]))
        plot_txt(screen, font_avg, f'{stats["max"]["rx"]["last_speed"]:.5f}/ms', center=(center_right[0], center_right[1] + first_line_dist + line_dist))
        plot_txt(screen, font_max, f'10sMAX, MAX: {max(stats["max"]["rx"]["max_speeds"], default=0):.5f}, {stats["max"]["rx"]["max_speed"]:.5f}/ms', center=(center_right[0], center_right[1] + first_line_dist + line_dist * 2))

 
        # 1s Sum of Vector Size
        sum_vec_l = 0
        sum_vec_r = 0
        for idx, stat in enumerate(stats["timestamps"]):
            try: # stats could be deleted by another thread
                vector_size_l = np.sqrt(np.square(stats["lx"][idx]) + np.square(stats["ly"][idx]**2))
                vector_size_r = np.sqrt(np.square(stats["rx"][idx]) + np.square(stats["ry"][idx]**2))
                sum_vec_l += vector_size_l
                sum_vec_r += vector_size_r
            except:
                #just ignore thread race condition.
                continue

        if 0 < len(stats["timestamps"]):
            # regularize max values to 100 when sticks always set to like (0, 1.0)
            # can be over 100 due to sticks' circularity.
            sum_vec_l = sum_vec_l / len(stats["timestamps"]) * 100
            sum_vec_r = sum_vec_r / len(stats["timestamps"]) * 100

        l_color = calc_color(sum_vec_l / 100.0)
        r_color = calc_color(sum_vec_r / 100.0)


        # Comment outed to avoid annoying numbers.
        #plot_txt(screen, font_avg, f'{round(sum_vec_l, 5):.5f}', center = (center_left[0], center_left[1] + first_line_dist + line_dist))
        #plot_txt(screen, font_avg, f'{round(sum_vec_r, 5):.5f}', center = (center_right[0], center_right[1] + first_line_dist + line_dist))


        # Draws stick circles
        #   RIGHT
        pygame.draw.circle(screen, (*r_color, 187), center_right, guide_radius, 2)
        pygame.draw.line(screen, (200, 200, 200, 128), (center_right[0] - guide_radius, center_right[1]), (center_right[0] + guide_radius, center_right[1]), 1)
        pygame.draw.line(screen, (200, 200, 200, 128), (center_right[0], center_right[1] - guide_radius), (center_right[0], center_right[1] + guide_radius), 1)
        #   LEFT
        pygame.draw.circle(screen, (*l_color, 187), center_left, guide_radius, 2)
        pygame.draw.line(screen, (200, 200, 200, 128), (center_left[0] - guide_radius, center_left[1]), (center_left[0] + guide_radius, center_left[1]), 1)
        pygame.draw.line(screen, (200, 200, 200, 128), (center_left[0], center_left[1] - guide_radius), (center_left[0], center_left[1] + guide_radius), 1)


        # Reflects to the window
        pygame.display.flip()


        # Sets window reflesh rate to 60FPS
        clock.tick(60)

ANALYZE_KEYS = ["mvmt_avg", "diff_1", "diff_5", "diff_1_of_5", "diff_1_of_1_of_5", "direction", "big_mvmt", "turned", "sums", "speed", "begin_ms", "end"]
ANALYZE_AGGR_KEYS = ["last_speed", "max_speed"]
ANALYZE_AGGR_MS_KEYS = ["max_speeds", "max_speeds_ms"]
ANALYZE_COLOR_KEY = "colors"

def csv_file_header(joystick):
    header = ['ms_from_init', 'lx', 'ly', 'rx', 'ry', 'lt', 'rt']
    
    for i in range(joystick.get_numbuttons()):
        header.append(f'btn.{i}')

    for key in ['lx', 'ly', 'rx', 'ry']:
        for key2 in ANALYZE_KEYS:
            header.append(f'{key}.{key2}')

    return header


def analyze_stats(stats):
    '''Analyzes stats
    '''

    i = len(stats["timestamps"]) - 1
    
    # needs at least 11 stats
    if i < 11:
        for key in ["lx", "ly", "rx", "ry"]:
            for key2 in ANALYZE_KEYS:
                stats["max"][key][key2].append(0)
            stats["max"][key][ANALYZE_COLOR_KEY].append(HISTORY_LINE_DEFAULT_COLOR)
        return False

    # analyze target
    target = i - 5

    for key in ["lx", "ly", "rx", "ry"]:
        analyze_stick_stats(stats, key, target)

    return True


def analyze_stick_stats(stats, key, target):

    stick_stats = stats[key]
    stick_analyzed_stats = stats["max"][key]

    for key in ANALYZE_KEYS:
        stick_analyzed_stats[key].append(0)
    stick_analyzed_stats[ANALYZE_COLOR_KEY].append(HISTORY_LINE_DEFAULT_COLOR)


    # calc movement average of 100ms
    stick_analyzed_stats["mvmt_avg"][target] = reduce(lambda x, y: x + y, stick_stats[target - 5:target + 5], 0) / 11


    # 1 if stick moves toward 1, -1 if stick moves toward -1, 0 if stick doesn't move.
    direction = 0
    pos_diff_1 = stick_analyzed_stats["mvmt_avg"][target] - stick_analyzed_stats["mvmt_avg"][target - 1]
    if pos_diff_1 < 0:
        direction = -1
    elif pos_diff_1 == 0:
        direction = 0
    else:
        direction = 1
    stick_analyzed_stats["direction"][target] = direction


    # analyzes using stats before
    stick_analyzed_stats["diff_1"][target] = stick_analyzed_stats["mvmt_avg"][target] - stick_analyzed_stats["mvmt_avg"][target - 1]
    stick_analyzed_stats["diff_5"][target] = stick_analyzed_stats["mvmt_avg"][target] - stick_analyzed_stats["mvmt_avg"][target - 5]
    stick_analyzed_stats["diff_1_of_5"][target] = stick_analyzed_stats["diff_5"][target] - stick_analyzed_stats["diff_5"][target - 1]
    stick_analyzed_stats["diff_1_of_1_of_5"][target] = stick_analyzed_stats["diff_1_of_5"][target] - stick_analyzed_stats["diff_1_of_5"][target - 1]


    def is_stick_keep_moved(idx):
        threshold = THRESHOLD_STICK_KEEP_MOVING
        return abs(stick_analyzed_stats["diff_1_of_1_of_5"][idx]) > threshold

    def is_stick_accelerated(idx):
        #return (0 < stick_analyzed_stats["mvmt_avg"][idx] and stick_analyzed_stats["diff_1_of_5"][idx] < -0.01) or\
        #       (stick_analyzed_stats["mvmt_avg"][idx] < 0 and 0.01 < stick_analyzed_stats["diff_1_of_5"][idx])
        return abs(stick_analyzed_stats["diff_1_of_5"][idx]) > THRESHOLD_STICK_ACCELERATION

    def is_stick_big_mvmt(idx):
        return THRESHOLD_STICK_BIG_MOVEMENT < abs(stick_analyzed_stats["diff_5"][idx])
    
    def is_stick_direction_changed(idx):
        return stick_analyzed_stats["direction"][idx - 1] != stick_analyzed_stats["direction"][idx]

    def is_stick_turned(idx):
        stat = stick_analyzed_stats["mvmt_avg"]
        stat_before = stat[idx - 1]
        stat_cur = stat[idx]
        if (stat_before <= 0 and 0 < stat_cur) or\
           (0 <= stat_before and stat_cur < 0) or\
           (stat_before < 0 and 0 <= stat_cur) or\
           (0 < stat_before and stat_cur <= 0):
            return True
        return False
    
    def find_begin_and_set_sums(idx):
        for j in range(idx - 1, 6, -1):
            if is_stick_accelerated(j):
                #print("begin_ms:", len(stick_analyzed_stats["begin_ms"]), idx)
                stick_analyzed_stats["begin_ms"][idx] = stats["timestamps"][j]
                for k in range(j, idx):
                    stick_analyzed_stats[ANALYZE_COLOR_KEY][k] = HISTORY_LINE_BIG_MVMT_COLOR
                return True
        return False
    
    def find_end_and_set_sums(idx):
        begin_ms_index = -1
        begin_ms = 0
        for j in range(idx - 1, 6, -1):
            if stick_analyzed_stats["begin_ms"][j] != 0:
                begin_ms = stick_analyzed_stats["begin_ms"][j]
                stick_analyzed_stats["begin_ms"][idx - 1] = begin_ms
                for k in range(j, 6, -1):
                    if stats["timestamps"][k] == begin_ms:
                        begin_ms_index = k
                        break
                break

        if begin_ms > 0:
            for j in range(idx, target + 5):

                if not is_stick_accelerated(j) or not is_stick_keep_moved(j):
                    end_ms = stats["timestamps"][j]
                    stick_analyzed_stats["end"][idx - 1] = end_ms

                    if j - 1 - begin_ms_index > 0:
                        sums = abs(reduce(lambda x, y: abs(x) + abs(y), stick_stats[begin_ms_index:j - 1], 0))
                        stick_analyzed_stats["sums"][idx - 1] = sums

                        if end_ms - begin_ms > 0:
                            speed = sums / (end_ms - begin_ms)
                            stick_analyzed_stats["speed"][idx - 1] = speed
                            stick_analyzed_stats["last_speed"] = speed
                            if speed > stick_analyzed_stats["max_speed"]:
                                stick_analyzed_stats["max_speed"] = speed
                            stick_analyzed_stats["max_speeds"].append(speed)
                            stick_analyzed_stats["max_speeds_ms"].append(end_ms)

                            for k in range(begin_ms_index, j - 1):
                                stick_analyzed_stats[ANALYZE_COLOR_KEY][k] = HISTORY_LINE_BIG_TURN_COLOR

                    return True

        return False


    # check if the current movement is big or not
    end_big_mvmt = False
    if stick_analyzed_stats["big_mvmt"][target - 1] == 1:
        if is_stick_accelerated(target):
            # continue big movement
            stick_analyzed_stats["big_mvmt"][target] = 1
            stick_analyzed_stats[ANALYZE_COLOR_KEY][target] = HISTORY_LINE_BIG_MVMT_COLOR
        else:
            # end big movement
            stick_analyzed_stats["big_mvmt"][target] = 0
            end_big_mvmt = True

    elif is_stick_big_mvmt(target) and is_stick_accelerated(target):
        # new big movement

        # calculate begin point
        found_begin = find_begin_and_set_sums(target)
        if found_begin:
            stick_analyzed_stats["big_mvmt"][target] = 1


    if stick_analyzed_stats["big_mvmt"][target] == 1:

        if stick_analyzed_stats["turned"][target - 1] == 1:
            if is_stick_direction_changed(target):
                # end turn
                stick_analyzed_stats["big_mvmt"][target] = 0
                end_big_mvmt = True
                find_end_and_set_sums(target)

            else:
                # continue turn
                stick_analyzed_stats["turned"][target] = 1
                stick_analyzed_stats[ANALYZE_COLOR_KEY][target] = HISTORY_LINE_TURNED_COLOR

        elif is_stick_turned(target):
            # new turn
            stick_analyzed_stats["turned"][target] = 1
            stick_analyzed_stats[ANALYZE_COLOR_KEY][target] = HISTORY_LINE_TURNED_COLOR

    elif stick_analyzed_stats["turned"][target - 1] == 1 and end_big_mvmt:
        # finished big mvmt and turn
        find_end_and_set_sums(target)

    return stick_analyzed_stats


def measure_stats(joystick, stats, cur_ms):
    lx = fix_stick_val(joystick.get_axis(0))
    ly = fix_stick_val(joystick.get_axis(1))
    rx = fix_stick_val(joystick.get_axis(2))
    ry = fix_stick_val(joystick.get_axis(3))
    lt = fix_stick_val(joystick.get_axis(4))
    rt = fix_stick_val(joystick.get_axis(5))

    stats["timestamps"].append(cur_ms)
    stats["lx"].append(lx)
    stats["ly"].append(ly)
    stats["rx"].append(rx)
    stats["ry"].append(ry)
    stats["lt"].append(lt)
    stats["rt"].append(rt)

    for i in range(joystick.get_numbuttons()):
        btn_state = joystick.get_button(i)
        if btn_state:
            stats["buttons"][i].append(1)
        else:
            stats["buttons"][i].append(0)


def delete_lines(joystick, stats, cur_ms, max_ms, aggr_max_ms):
    lines = []

    below_max_index = -1
    for i in range(len(stats["timestamps"])):
        if cur_ms - stats["timestamps"][i] <= max_ms:
            break
        below_max_index = i

    #print(len(stats["max"]["lx"]["mvmt_avg"]), len(stats["timestamps"]), below_max_index)

    if below_max_index >= 0:
        for i in range(0, below_max_index):
            
            line = []
            try:
                line.append(stats["timestamps"][i])
                del stats["timestamps"][i]
            except:
                pass

            for key in ["lx", "ly", "rx", "ry", "lt", "rt"]:
                try:
                    line.append(stats[key][i])
                    del stats[key][i]
                except:
                    pass

            for j in range(joystick.get_numbuttons()):
                try:
                    line.append(stats["buttons"][j][i])
                    del stats["buttons"][j][i]
                except:
                    pass

            for key in ["lx", "ly", "rx", "ry"]:
                for key2 in ANALYZE_KEYS:
                    if i < len(stats["max"][key][key2]):
                        try:
                            line.append(stats["max"][key][key2][i])
                            del stats["max"][key][key2][i]
                        except:
                            pass
                del stats["max"][key][ANALYZE_COLOR_KEY][i]

            lines.append(line)

    for i in ["lx", "ly", "rx", "ry"]:
        delete_to = -1
        for j in range(len(stats["max"][i]["max_speeds_ms"])):
            old_ms = stats["max"][i]["max_speeds_ms"][j]
            if cur_ms - old_ms <= aggr_max_ms:
                break
            delete_to = j
        if delete_to >= 0:
            try:
                del stats["max"][i]["max_speeds"][:delete_to]
                del stats["max"][i]["max_speeds_ms"][:delete_to]
            except:
                pass

    return lines


def recorder_mode_measure(joystick, stats, cur_ms, writer):
    deleted_lines = delete_lines(joystick, stats, cur_ms, MAX_MS, AGGR_MAX_MS)
    measure_stats(joystick, stats, cur_ms)
    analyze_stats(stats)
    for line in deleted_lines:
        writer.writerow(line)

def gui_mode_measure(joystick, stats, cur_ms, fd):
    delete_lines(joystick, stats, cur_ms, MAX_MS, AGGR_MAX_MS)
    measure_stats(joystick, stats, cur_ms)
    analyze_stats(stats)

def stick_mode_measure(joystick, stats, cur_ms, fd):
    delete_lines(joystick, stats, cur_ms, MAX_MS, AGGR_MAX_MS)
    measure_stats(joystick, stats, cur_ms)

def measure_main_loop(measure_func, joystick, stats, stop_event, change_event, writer = None):
    clock = pygame.time.Clock()

    last_ms = pygame.time.get_ticks()

    while not stop_event.is_set() and not change_event.is_set():
        quit_event = pygame.event.get(pygame.QUIT)
        if quit_event:
            stop_event.set()
            return
        
        joystick_remove_event = pygame.event.get(pygame.JOYDEVICEREMOVED)
        if joystick_remove_event:
            change_event.set()
            return


        # Get the time from pygame.init() called in ms.
        cur_ms = pygame.time.get_ticks()

        if cur_ms - last_ms >= SAMPLING_RATE:
            measure_func(joystick, stats, cur_ms, writer)
            # Calculating FPS
            stats["fps"] = 1000 / (cur_ms - last_ms)
            last_ms = cur_ms
        
        # Wait until next measure frame
        clock.tick(MEASURE_FRAME_RATE)

def measure(measure_func, joystick, stats, stop_event, change_event, record = False):

    if (record):
        dt = datetime.datetime.now()
        filename = dt.strftime("%Y%m%d_%H%M%S_%f.csv")
        with open(filename, 'w') as fd:
            writer = csv.writer(fd)
            writer.writerow(csv_file_header(joystick))
            measure_main_loop(measure_func, joystick, stats, stop_event, change_event, writer)
    else:
        measure_main_loop(measure_func, joystick, stats, stop_event, change_event)    

def realtime_gui(screen, joystick, stop_event, change_event, stats):
    visualization_thread = None
    
    visualization_thread = Thread(target=recorder_mode_visualize, args=(screen, joystick, stats, stop_event, change_event, False))
    visualization_thread.start()
        
    measure(gui_mode_measure, joystick, stats, stop_event, change_event)
    if visualization_thread:
        visualization_thread.join()

def recorder_with_gui(screen, joystick, stop_event, change_event, stats):
    '''
        RECORDER with GUI
    '''
    recorder(screen, joystick, stop_event, change_event, True, stats)

def recorder_without_gui(screen, joystick, stop_event, change_event, stats):
    '''
        RECORDER without GUI
    '''
    recorder(screen, joystick, stop_event, change_event, False, stats)

def recorder(screen, joystick, stop_event, change_event, with_gui, stats):

    visualization_thread = None
    
    if with_gui:
        visualization_thread = Thread(target=recorder_mode_visualize, args=(screen, joystick, stats, stop_event, change_event, True))
        visualization_thread.start()
        
    measure(recorder_mode_measure, joystick, stats, stop_event, change_event, True)
    if visualization_thread:
        visualization_thread.join()

def stick_analyzer(screen, joystick, stop_event, change_event, stats):
    '''
        STICK ANALYZER
    '''

    visualization_thread = Thread(target=stick_mode_visualize, args=(screen, joystick, stats, stop_event, change_event))
    visualization_thread.start()
        
    measure(stick_mode_measure, joystick, stats, stop_event, change_event)
    visualization_thread.join()

def init_pygame(to_run_func, width, height, transparent, pin_on_top):
    stop_event = Event()
    change_event = Event()
    
    while True:
        pygame.init()
        joystick = init_joystick()
        if joystick is None:
            print("Couldn't find Controller.")
            input("Press Enter to exit...")
            return
            
        screen = None
        if transparent:
            if pin_on_top:
                screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
            else:
                screen = pygame.display.set_mode((width, height))#, pygame.NOFRAME)
            hwnd = pygame.display.get_wm_info()["window"]
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*(128, 128, 128)), 0, win32con.LWA_COLORKEY)
            if pin_on_top:
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, PIN_ON_TOP_POS[0], PIN_ON_TOP_POS[1], 0, 0, win32con.SWP_NOSIZE)
        else:
            if pin_on_top:
                screen = pygame.display.set_mode((width, height), pygame.NOFRAME)
                hwnd = pygame.display.get_wm_info()["window"]
                win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, PIN_ON_TOP_POS[0], PIN_ON_TOP_POS[1], 0, 0, win32con.SWP_NOSIZE)
            else:
                screen = pygame.display.set_mode((width, height))

        pygame.display.set_caption("GPSA: Game Pad Stats Analyzer")

        #prepare stats
        stats = {
            "timestamps": [],
            "lx": [], "ly": [], "rx": [], "ry": [],
            "lt": [], "rt": [],
            "max": {
                "lx": {},
                "ly": {},
                "rx": {},
                "ry": {}
            },
            "buttons": [],
            "fps": 0
        }
        for key in ["lx", "ly", "rx", "ry"]:
            for key2 in ANALYZE_KEYS:
                stats["max"][key][key2] = []
            for key2 in ANALYZE_AGGR_KEYS:
                stats["max"][key][key2] = 0
            for key2 in ANALYZE_AGGR_MS_KEYS:
                stats["max"][key][key2] = []
            stats["max"][key][ANALYZE_COLOR_KEY] = []

        for i in range(joystick.get_numbuttons()):
            stats["buttons"].append([])

        to_run_func(screen, joystick, stop_event, change_event, stats)

        if stop_event.is_set():
            pygame.quit()
            return
        
        if change_event.is_set():
            pygame.quit()
            change_event.clear()


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--stick", help="stick analyzer mode",
                    action="store_true")
    parser.add_argument("-g", "--gui", help="gui mode",
                    action="store_true")
    parser.add_argument("-r", "--record", help="recorder with gui mode",
                    action="store_true")
    parser.add_argument("-p", "--pin", help="pin window on top",
                    action="store_true")
    return parser.parse_args()

def main():
    prepare()
    
    '''
        Determin a mode to run.
    '''
    args = parse_args()
    if args.gui:
        init_pygame(realtime_gui, 460, 250, True, args.pin)
    elif args.record:
        init_pygame(recorder_with_gui, 460, 250, True, args.pin)
    elif args.stick:
        init_pygame(stick_analyzer, 1100, 450, False, args.pin)
    else:
        init_pygame(realtime_gui, 460, 250, True, True)


if __name__ == "__main__":
    main()