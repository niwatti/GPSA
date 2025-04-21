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

import csv

version = "0.3"

# MEASURE Thread FPS
MEASURE_FRAME_RATE = 120

# JOYSTICK Step Accuracy, HISTOGRAM BINS for calculating mode
JOYSTICK_HIST_STEPS = 32

def prepare():
    os.system('cls' if os.name == 'nt' else 'clear')
    os.environ["SDL_JOYSTICK_ALLOW_BACKGROUND_EVENTS"] = "1"    #get key events while the window are not focused
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
    else:
        return (math.floor(val * 100000) / 100000 + 0.00002) / 0.99998

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
    width = 80

    # Draw Area
    pygame.draw.rect(screen, (200, 200, 200), (left, x_top, guide_radius * 2, width)) #X
    pygame.draw.rect(screen, (200, 200, 200), (left, y_top, guide_radius * 2, width)) #Y
    
    # Labels
    plot_txt(screen, font, f'X', center=(left - 5, x_top + width / 2))
    plot_txt(screen, font, f'Y', center=(left - 5, y_top + width / 2))

    x_count = len(stat_x)
    last_pos = (left, x_top + 10)
    #print(stat_x)
    for idx, x in enumerate(stat_x):
        # idx: 0 -> (count - 1)
        new_pos = (left + (idx / x_count) * guide_radius * 2, x_top + width - ((x + 1)/ 2) * width)
        pygame.draw.line(screen, (100, 100, 100), last_pos, new_pos)
        last_pos = new_pos

    y_count = len(stat_y)
    last_pos = (left, y_top + 10)
    for idx, y in enumerate(stat_y):
        new_pos = (left + (idx / y_count) * guide_radius * 2, y_top + width - (((y + 1) / 2) * width))
        pygame.draw.line(screen, (100, 100, 100), last_pos, new_pos)
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

def recorder_mode_visualize(screen, joystick, stats, stop_event, change_event):
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
    center_left = (70, 70)
    center_right = (250, 70)
    guide_radius = 50
    line_dist = 20
    first_line_dist = 60
    x_first_line_dist = 30

    # Main loop of the window drawings
    while not stop_event.is_set() and not change_event.is_set():
        screen.fill((128, 128, 128))

        # draw water mark
        plot_txt(screen, font_label, 'GPSA by monoru', True, (255, 255, 255), 145, midright = (350, 10))

        # draw timestamp
        cur_ms = pygame.time.get_ticks()
        plot_txt(screen, font_avg, f'{cur_ms}', midright = (350, 140))

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

        # 1s Sum of Vector Size
        sum_vec_l = 0
        sum_vec_r = 0
        for idx, stat in enumerate(stats["timestamps"]):
            # could be deleted by another thread
            if len(stats["lx"]) <= idx or len(stats["ly"]) <= idx or len(stats["rx"]) <= idx or len(stats["ry"] <= idx):
                continue

            try:
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


def measure_stats(joystick, stats, cur_ms, max_ms):
    while len(stats["timestamps"]) > 0:
        if cur_ms - stats["timestamps"][0] <= max_ms:
            break
        del stats["timestamps"][0]
        del stats["lx"][0]
        del stats["ly"][0]
        del stats["rx"][0]
        del stats["ry"][0]

    dt = datetime.datetime.now()
    lx = fix_stick_val(joystick.get_axis(0))
    ly = fix_stick_val(joystick.get_axis(1))
    rx = fix_stick_val(joystick.get_axis(2))
    ry = fix_stick_val(joystick.get_axis(3))

    stats["timestamps"].append(cur_ms)
    stats["lx"].append(lx)
    stats["ly"].append(ly)
    stats["rx"].append(rx)
    stats["ry"].append(ry)

    return lx, ly, rx, ry, dt.isoformat()

def recorder_mode_measure(joystick, stats, cur_ms, writer):
    lx, ly, rx, ry, ts = measure_stats(joystick, stats, cur_ms, 1000)
    writer.writerow([ts, cur_ms, lx, ly, rx, ry])

def gui_mode_measure(joystick, stats, cur_ms, fd):
    measure_stats(joystick, stats, cur_ms, 1000)

def stick_mode_measure(joystick, stats, cur_ms, fd):
    measure_stats(joystick, stats, cur_ms, 10000)

def measure_main_loop(measure_func, joystick, stats, stop_event, change_event, writer = None):
    clock = pygame.time.Clock()

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
        
        measure_func(joystick, stats, cur_ms, writer)
        
        # Wait until next measure frame
        clock.tick(MEASURE_FRAME_RATE)

def measure(measure_func, joystick, stats, stop_event, change_event, record = False):

    if (record):
        dt = datetime.datetime.now()
        filename = dt.strftime("%Y%m%d_%H%M%S_%f.gpsa")
        with open(filename, 'w') as fd:
            writer = csv.writer(fd)
            measure_main_loop(measure_func, joystick, stats, stop_event, change_event, writer)
    else:
        measure_main_loop(measure_func, joystick, stats, stop_event, change_event)    

def realtime_gui(screen, joystick, stop_event, change_event):
    stats = {"timestamps": [], "lx": [], "ly": [], "rx": [], "ry": []}

    visualization_thread = None
    
    visualization_thread = Thread(target=recorder_mode_visualize, args=(screen, joystick, stats, stop_event, change_event))
    visualization_thread.start()
        
    measure(gui_mode_measure, joystick, stats, stop_event, change_event)
    if visualization_thread:
        visualization_thread.join()

def recorder_with_gui(screen, joystick, stop_event, change_event):
    '''
        RECORDER with GUI
    '''
    recorder(screen, joystick, stop_event, change_event, True)

def recorder_without_gui(screen, joystick, stop_event, change_event):
    '''
        RECORDER without GUI
    '''
    recorder(screen, joystick, stop_event, change_event, False)

def recorder(screen, joystick, stop_event, change_event, with_gui):
    stats = {"timestamps": [], "lx": [], "ly": [], "rx": [], "ry": []}

    visualization_thread = None
    
    if with_gui:
        visualization_thread = Thread(target=recorder_mode_visualize, args=(screen, joystick, stats, stop_event, change_event))
        visualization_thread.start()
        
    measure(recorder_mode_measure, joystick, stats, stop_event, change_event, True)
    if visualization_thread:
        visualization_thread.join()

def stick_analyzer(screen, joystick, stop_event, change_event):
    '''
        STICK ANALYZER
    '''
     
    stats = {"timestamps": [], "lx": [], "ly": [], "rx": [], "ry": []}
    visualization_thread = Thread(target=stick_mode_visualize, args=(screen, joystick, stats, stop_event, change_event))
    visualization_thread.start()
        
    measure(stick_mode_measure, joystick, stats, stop_event, change_event)
    visualization_thread.join()

def init_pygame(to_run_func, width, height, transparent):
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
            screen = pygame.display.set_mode((width, height))#, pygame.NOFRAME)
            hwnd = pygame.display.get_wm_info()["window"]
            win32gui.SetWindowLong(hwnd, win32con.GWL_EXSTYLE, win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE) | win32con.WS_EX_LAYERED)
            win32gui.SetLayeredWindowAttributes(hwnd, win32api.RGB(*(128, 128, 128)), 0, win32con.LWA_COLORKEY)
        else:
            screen = pygame.display.set_mode((width, height))

        pygame.display.set_caption("GPSA: Game Pad Stats Analyzer")
        to_run_func(screen, joystick, stop_event, change_event)

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
    return parser.parse_args()

def main():
    prepare()
    
    '''
        Determin a mode to run.
    '''
    args = parse_args()
    if args.gui:
        init_pygame(realtime_gui, 360, 160, True)
    elif args.record:
        init_pygame(recorder_with_gui, 360, 160, True)
    else:
        init_pygame(stick_analyzer, 1100, 450, False)


if __name__ == "__main__":
    main()