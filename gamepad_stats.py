import pygame
from colorama import Style
from threading import Thread, Event
import os
import numpy as np

version = "0.1"

# MEASURE Thread FPS
MEASURE_FRAME_RATE = 120

# JOYSTICK Step Accuracy, HISTOGRAM BINS for calculating mode
JOYSTICK_HIST_STEPS = 32

def prepare():
    os.system('cls' if os.name == 'nt' else 'clear')
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


def plot_txt(screen, font, text, **kwargs):
    rendered = font.render(text, True, (255, 255, 255))
    rect = rendered.get_rect(**kwargs)
    screen.blit(rendered, rect)

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

            # |        LB         |         B         |         DB     |            DG          |         G         |           GY        |           Y         |           O         |          R        |          P         |
            # |(128, 128, 255) - 128 - (0, 0, 255) - 128 - (0, 0, 128) - 128 - (0, 128, 128) - 128 - (0, 255, 0) - 128 - (128, 255, 0) - 128 - (255, 255, 0) - 128 - (255, 128, 0) - 128 - (255, 0, 0) - 128 - (255, 0, 128)
            # |(128, 128, 255)(0, 0, 255)         (0, 0, 128)     (0, 128, 128)            (0, 255, 0)          (128, 255, 0)        (255, 255, 0)         (255, 128, 0)         (255, 0, 0)          (255, 0, 128)
            # |                   |                   |                |                        |                   |                     |                     |                     |                   |
            color_rate = count / max_count

            red = 0
            green = 0
            blue = 0
            if color_rate < 1 / 9:
                red = (0.5 - (color_rate * 8)) * 255
                green = (0.5 - (color_rate * 8)) * 255
            elif 4 / 9 <= color_rate:
                red = (color_rate - 4 / 9) * 9 / 2 * 255

            if 2 / 9 <= color_rate and color_rate < 6 / 9:
                green = (color_rate - 2 / 9) * 9 / 2 * 255
            elif 6 / 9 <= color_rate:
                green = (1 - (color_rate - 6 / 9) * 9 / 2) * 255

            blue = 0
            if color_rate < 2 / 9:
                blue = ( 1 - (color_rate - 1 / 9) * 9 / 2) * 255
            elif color_rate < 3 / 9:
                blue = 128
            elif 8 / 9 <= color_rate:
                blue = (color_rate - 8 / 9) * 9 / 2 * 255

            if red < 0: red = 0
            if red > 255: red = 255
            if green < 0: green = 0
            if green > 255: green = 255
            if blue < 0: blue = 0
            if blue > 255: blue = 255
            color = (red, green, blue)

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

def draw_lines(screen, stat_x, stat_y, center_x, center_y, font, guide_radius, first_line_dist, line_dist):
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



def visualize(screen, joystick, stats, stop_event, change_event):
    """GPSA visualize function.
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
        lx = joystick.get_axis(0)
        ly = joystick.get_axis(1)
        rx = joystick.get_axis(2)
        ry = joystick.get_axis(3)


        # Draws current position of the sticks

        #   LEFT
        left_stick_position = (center_left[0] + int(lx * guide_radius), center_left[1] + int(ly * guide_radius))
        pygame.draw.circle(screen, (255, 255, 255), left_stick_position, 3)
        plot_txt(screen, font_avg, f'{round(lx, 5):.5f}', center = (center_left[0], center_left[1] + first_line_dist))
        plot_txt(screen, font_avg, f'{round(ly, 5):.5f}', center =(center_left[0] + guide_radius + 70, center_left[1]))

        #   RIGHT
        right_stick_position = (center_right[0] + int(rx * guide_radius), center_right[1] + int(ry * guide_radius))
        pygame.draw.circle(screen, (255, 255, 255), right_stick_position, 3)
        plot_txt(screen, font_avg, f'{round(rx, 5):.5f}', center=(center_right[0], center_right[1] + first_line_dist))
        plot_txt(screen, font_avg, f'{round(ry, 5):.5f}', center=(center_right[0] + guide_radius + 70, center_right[1]))

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
        draw_lines(screen, stats["lx"], stats["ly"], center_left[0], center_left[1], font_label, guide_radius, first_line_dist, line_dist)
        draw_lines(screen, stats["rx"], stats["ry"], center_right[0], center_right[1], font_label, guide_radius, first_line_dist, line_dist)

        # Reflects to the window
        pygame.display.flip()

        # Sets window reflesh rate to 60FPS
        clock.tick(60)

def measure(joystick, stats, stop_event, change_event):
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
        
        while len(stats["timestamps"]) > 0:
            if cur_ms - stats["timestamps"][0] <= 10000:
                break
            del stats["timestamps"][0]
            del stats["lx"][0]
            del stats["ly"][0]
            del stats["rx"][0]
            del stats["ry"][0]
    
        lx = joystick.get_axis(0)
        ly = joystick.get_axis(1)
        rx = joystick.get_axis(2)
        ry = joystick.get_axis(3)

        stats["timestamps"].append(cur_ms)
        stats["lx"].append(lx)
        stats["ly"].append(ly)
        stats["rx"].append(rx)
        stats["ry"].append(ry)
        
        # Wait until next measure frame
        clock.tick(MEASURE_FRAME_RATE)

def main():
    prepare()

    stats = {"timestamps": [], "lx": [], "ly": [], "rx": [], "ry": []}
    
    stop_event = Event()
    change_event = Event()
    
    while True:
        pygame.init()
        joystick = init_joystick()
        if joystick is None:
            print("Couldn't find Controller.")
            input("Press Enter to exit...")
            return
            
        screen = pygame.display.set_mode((1100, 450))
        pygame.display.set_caption("GPSA: Game Pad Stats Analyzer")

        visualization_thread = Thread(target=visualize, args=(screen, joystick, stats, stop_event, change_event))
        visualization_thread.start()
        
        measure(joystick, stats, stop_event, change_event)
        visualization_thread.join()

        if stop_event.is_set():
            pygame.quit()
            return
        
        if change_event.is_set():
            pygame.quit()
            change_event.clear()

if __name__ == "__main__":
    main()