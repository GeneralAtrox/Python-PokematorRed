#! /usr/bin/env python

import math
import os
import queue
import re
import shutil
import threading
import time
from enum import Enum
import cv2
import numpy as np
import pytesseract
import win32con
import win32gui
import pyautogui
from PIL import ImageGrab
from win32gui import GetForegroundWindow
import KeyInput

pytesseract.pytesseract.tesseract_cmd = r"C:\Tools\Tesseract-OCR\tesseract.exe"

pid = None
windowname = None
windowpos = None

# Controls
## Movement
UP_ARROW = KeyInput.DIK_UP
RIGHT_ARROW = KeyInput.DIK_RIGHT
LEFT_ARROW = KeyInput.DIK_LEFT
DOWN_ARROW = KeyInput.DIK_DOWN
## Actions, Enter, Exit
X_KEY = KeyInput.DIK_X
Z_KEY = KeyInput.DIK_Z

Key_Delay = 0.1

class WindowChecker(threading.Thread):
    '''
    Helper class to implement asynchronous reading of a file
    in a separate thread. Pushes read lines on a queue to
    be consumed in another thread.
    '''

    def __init__(self):
        threading.Thread.__init__(self)

    def run(self):
        '''Make sure our foreground window is running, then restart'''
        while GetForegroundWindow():
            pass

        else:
            print("Focus Lost - Minimizing Application then exiting")
            #win32gui.ShowWindow(pid, win32con.SW_MINIMIZE)
            exit()


class GameAutomation(threading.Thread):
    def __init__(self, queue):
        threading.Thread.__init__(self)
        self._queue = queue

        self.CurrentGameState = None
        self.CurrentFile = None
        self.CurrentTarget = None
        self.CurrentImg_RGB = None

        # GAME BOOLS
        self.can_move_up = True
        self.can_move_down = True
        self.can_move_left = True
        self.can_move_right = True

    def run(self):
        print("Running automation")
        while True:
            time.sleep(1)
            self.MainGame()

    class GameState(Enum):
        On_Start_Menu = 'On Start Menu'
        Main_Menu = 'Main Menu'
        Enemy_Appeared = 'Enemy Appeared!'
        Ready_To_Fight = 'Ready_To_Fight'
        Menu_Open = 'On Menu'
        In_World = 'In World'
        In_PokeCenter = 'In PokeCenter'

    def MainGame(self):

        im = Screenshot_Game(windowname)

        self.CurrentFile = os.getcwd() + '\\Images\\full_snap__' + str(int(time.time())) + '.png'
        self.remove_old_image()

        im.save(self.CurrentFile, 'PNG')

        self.CurrentImg_RGB = cv2.imread(self.CurrentFile)
        player_pos = self.find_player_in_image()

        y = player_pos[0] - 70
        x = player_pos[1] - 40

        crop_img = self.CurrentImg_RGB[y: 150 + 75, x: 75 + 150]
        print(crop_img.dtype)
        print(self.CurrentImg_RGB.dtype)



        cv2.imwrite(f'.\\Images\\Close.png', crop_img)

        # RESET BOOLS
        self.can_move_right = True
        self.can_move_down = True
        self.can_move_up = True
        self.can_move_left = True

        self.find_obstacle_near_player()
        #self.do_action()

    def calculate_center_screen(self):
        """
        Center screen adds 10px to negate the offset applied when moving/resizing the window

        :return: Axis of center screen
        """
        temp = win32gui.GetWindowRect(pid)

        X = int(temp[2]/2 + 10)
        Y = int(temp[3]/2 + 10)

        return X, Y

    def get_distance(self, targetX, targetY, startingX, startingY):
        """
        :param targetX:
        :param targetY:
        :param startingX:
        :param startingY:
        :return:
        Using two sets of XY, calculate the shortest distance
        """
        # Get distance
        dist = math.sqrt((targetX - startingX) ** 2 + (targetY - startingY) ** 2)
        return dist

    def calculate_angle(self, startingX, startingY, targetX, targetY):
        """
        :param startingX:
        :param startingY:
        :param targetX:
        :param targetY:
        :return:
        Calculate the angle between two points
        """
        angle = math.atan2(startingY - targetX, startingX - targetY)
        angle = angle * 180 / math.pi

        return angle

    def calculate_movement(self, angle):
        """
        :param angle:
        :return:
        Using the angle, calculate which button needs to be pressed to move along it
        """

        #print(f"Moving, angle: {angle}")
        # Positive Angle
        if angle > 0:
            if angle <= 45:
                print("0-45")
                # Move Left
                KeyInput.PressKey(LEFT_ARROW, Key_Delay)
                KeyInput.ReleaseKey(LEFT_ARROW)

            if angle > 45 and angle <= 90:
                print("45-90")
                # Move Up
                KeyInput.PressKey(UP_ARROW, Key_Delay)
                KeyInput.ReleaseKey(UP_ARROW)

            if angle > 90 and angle <= 135:
                print("90-135")
                # Move up
                KeyInput.PressKey(UP_ARROW, Key_Delay)
                KeyInput.ReleaseKey(UP_ARROW)

            if angle > 135 and angle <= 180:
                print("135-180")
                # Move Right
                KeyInput.PressKey(RIGHT_ARROW, Key_Delay)
                KeyInput.ReleaseKey(RIGHT_ARROW)

        elif angle < 0:
            # Negative Angle
            if angle >= -45:
                print("0--45")
                # Move Left
                KeyInput.PressKey(LEFT_ARROW, Key_Delay)
                KeyInput.ReleaseKey(LEFT_ARROW)

            if angle < -45 and angle >= -90:
                print("-45 - -90")
                # Move Down
                KeyInput.PressKey(DOWN_ARROW, Key_Delay)
                KeyInput.ReleaseKey(DOWN_ARROW)

            if angle < -90 and angle >= -135:
                print("-90 - -135")
                # Move Down
                KeyInput.PressKey(DOWN_ARROW, Key_Delay)
                KeyInput.ReleaseKey(DOWN_ARROW)

            if angle < -135 and angle >= -180:
                print("-135 - -180")
                # Move Right
                KeyInput.PressKey(RIGHT_ARROW, Key_Delay)
                KeyInput.ReleaseKey(RIGHT_ARROW)

    def do_action(self):
        if self.CurrentGameState == self.GameState.In_World:
            print("Doing action in world")
            angle, pt1, pt2 = self.find_object_in_image("grass.png")

            #self.find_obstacle_near_player()
            self.calculate_movement(angle)

        if self.CurrentGameState == self.GameState.Ready_To_Fight:
            print("Doing action in battle")

        if self.CurrentGameState == self.GameState.Menu_Open:
            print("Doing action in menu")

        if self.CurrentGameState == self.GameState.Enemy_Appeared:
            print("Moving fight along")

        if self.CurrentGameState == self.GameState.On_Start_Menu:
            print("Sitting on the start menu")
            # Start Menu -> Continue/New Game
            KeyInput.PressKey(X_KEY, Key_Delay)
            KeyInput.ReleaseKey(X_KEY)

            time.sleep(4)

            # Press Continue -> Accept Load Save Game Prompt
            KeyInput.PressKey(X_KEY, Key_Delay)
            KeyInput.ReleaseKey(X_KEY)
            time.sleep(4)
            KeyInput.PressKey(X_KEY, Key_Delay)
            KeyInput.ReleaseKey(X_KEY)

            # Should now be in-game
            self.CurrentGameState = self.GameState.In_World

        if self.CurrentGameState == self.GameState.Main_Menu:
            print("On the main menu")

        if self.CurrentGameState == self.GameState.In_PokeCenter:
            print("In the Poke Center")

    def find_player_in_image(self):
        player_location = None

        for count, filename in enumerate(os.listdir('.\\Haystack\\Player')):

            template = cv2.imread(f'.\\Haystack\\Player\\{filename}')
            w, h = template.shape[:-1]

            res = cv2.matchTemplate(self.CurrentImg_RGB, template, cv2.TM_CCOEFF_NORMED)

            threshold = 0.4
            loc = np.where(res >= threshold)

            for count, pt in enumerate(zip(*loc[::-1])):  # Switch columns and rows
                # Draw Rectangle around each object found on screen
                #cv2.rectangle(self.CurrentImg_RGB, pt, (pt[0] + w, pt[1] + h + 15), (0, 0, 255), 2)

                # Up
                #above_player = (pt[0], pt[1] - 32, pt[0] + w, pt[1] + h - 32)
                #cv2.rectangle(self.CurrentImg_RGB, (pt[0], pt[1] - 42), (pt[0] + w, pt[1] + h - 32), (0, 0, 255), 2)

                #cv2.rectangle(self.CurrentImg_RGB, (114, 144), (154, 189), (0, 0, 255), 2)
                # Down
                #down_player = (pt[0], pt[1] + 82, pt[0] + w, pt[1] + h + 15)
                #cv2.rectangle(self.CurrentImg_RGB, (pt[0], pt[1] + 82), (pt[0] + w, pt[1] + h + 15), (0, 0, 255), 2)

                # Left
                #left_player = (pt[0] - 42, pt[1], pt[0] + w - 42, pt[1] + h + 15)
                #cv2.rectangle(self.CurrentImg_RGB, (pt[0] - 42, pt[1]), (pt[0] + w - 37, pt[1] + h + 15), (0, 0, 255), 2)

                # Right
                #right_player = (pt[0] + 72, pt[1], pt[0] + w, pt[1] + h + 15)
                #cv2.rectangle(self.CurrentImg_RGB, (pt[0] + 72, pt[1]), (pt[0] + w, pt[1] + h + 15), (0, 0, 255), 2)

                #cv2.rectangle(self.CurrentImg_RGB, (pt[0] - 42, pt[1] - 32), (pt[0] + w + 42, pt[1] + h + 56), (0, 0, 255), 2)

                # Players exact position
                player_location = (pt[0] + round(w/2), pt[1] + round(h/2))
                #cv2.circle(self.CurrentImg_RGB, (pt[0] + round(w/2), pt[1] + round(h/2)), 5, (0, 0, 255), -1)

                if player_location:
                    #print("Found Player")
                    cv2.imwrite(f'result_{filename}', self.CurrentImg_RGB)

                    #Locations_Adjacent = (above_player, down_player, right_player, left_player)

                    return player_location

            # print(f"The shortest distance is: {lowest_value} at index: {lowest_value_index}")
            # cv2.line(self.CurrentImg_RGB, (x,x), (y,y), (0, 0, 255), 2)
            # cv2.line(self.CurrentImg_RGB, (x, y), (y, x), (0, 0, 255), 2)


        if not player_location:
            print("Cant find player")
            return player_location

    def find_obstacle_near_player(self):
        player_position = self.find_player_in_image()

        if player_position:
            player_x = player_position[1]
            player_y = player_position[0]
        else:
            print("Not in-game")
            return 0, 0, 0

        object_location = None
        empty_location = None

        for count, filename in enumerate(os.listdir('.\\Haystack\\Obstacles')):
            template = cv2.imread(f'.\\Haystack\\Obstacles\\{filename}')
            close_img = cv2.imread('\\Images\\Close.png')

            w, h = template.shape[:-1]
            try:
                res = cv2.matchTemplate(close_img, template, cv2.TM_CCOEFF_NORMED)
            except TypeError or cv2.error:
                break

            threshold = 0.65
            loc = np.where(res >= threshold)

            for count, pt in enumerate(zip(*loc[::-1])):  # Switch columns and rows
                # Draw Rectangle around each object found on screen
                cv2.rectangle(close_img, pt, (pt[0] + w * 2, pt[1] + h * 2), (0, 0, 255), 2)

                # Players exact position
                object_location = (pt[0] + round(w / 2), pt[1] + round(h / 2))
                cv2.circle(close_img, (pt[0] + round(w / 2), pt[1] + round(h / 2)), 5, (0, 0, 255), -1)

                if object_location:
                    # print("Found Player")
                    angle = self.calculate_angle(player_x, player_y, pt[0], pt[1])

                    if angle > -22 and angle < 22:
                        print("0-45")
                        # Move Left
                        self.can_move_left = False

                    if angle > 68 and angle <= 112:
                        print("45-90")
                        # Move Up
                        self.can_move_up = False
                        pass

                    if angle > 158 and angle <= 180:
                        print("135-180")
                        # Move Right
                        self.can_move_right = False
                        pass

                    if angle > -68 and angle <= -112:
                        print("45-90")
                        # Move Up
                        self.can_move_down = False
                        pass

                    if angle > -158 and angle <= -180:
                        print("135-180")
                        # Move Right
                        self.can_move_right = False
                        pass

                    return



            # print(f"The shortest distance is: {lowest_value} at index: {lowest_value_index}")
            # cv2.line(self.CurrentImg_RGB, (x,x), (y,y), (0, 0, 255), 2)
            # cv2.line(self.CurrentImg_RGB, (x, y), (y, x), (0, 0, 255), 2)

            cv2.imwrite(f'result_{filename}', img)
        if not object_location:
            print("Cant find obstacles")
            return

    def find_object_in_image(self, filename):
        """
        :type filename: Name of the haystack image
        :return: angle, targetX, targetY
        Using the haystack of image provided, find it on screen
        Once found, find out which object is closest to the player
        Also find out what angle so we can decide how to move towards it
        Finally, save an image with the result, found object will have a red rectangle
        """
        template = cv2.imread(f'.\\Haystack\\{filename}')
        w, h = template.shape[:-1]

        res = cv2.matchTemplate(self.CurrentImg_RGB, template, cv2.TM_CCOEFF_NORMED)
        threshold = 0.65
        loc = np.where(res >= threshold)

        # Where the play will always be.
        # Might need to tweak this to go from the player location as it might be slightly off
        player_position = self.find_player_in_image()


        if player_position:
            player_x = player_position[1]
            player_y = player_position[0]
        else:
            print("Not in-game")
            return 0, 0, 0

        lowest_value = None
        lowest_value_index = None
        angle, ptX, ptY = None, None, None

        for count, pt in enumerate(zip(*loc[::-1])):  # Switch columns and rows
            # Draw Rectangle around each object found on screen
            cv2.rectangle(self.CurrentImg_RGB, pt, (pt[0] + w, pt[1] + h), (0, 0, 255), 2)

            dist = self.get_distance(pt[1], pt[0], player_x, player_y)
            if lowest_value is None or dist < lowest_value:
                # Get closest object
                lowest_value = dist
                lowest_value_index = count
                ptX = pt[1]
                ptY = pt[0]

        #print(f"The shortest distance is: {lowest_value} at index: {lowest_value_index}")
        #cv2.line(self.CurrentImg_RGB, (x,x), (y,y), (0, 0, 255), 2)
        #cv2.line(self.CurrentImg_RGB, (x, y), (y, x), (0, 0, 255), 2)

        # Draw circle on the center of the screen
        #cv2.circle(self.CurrentImg_RGB, (y,x), 5, (0, 0, 255), -1)
        if ptY is None or ptX is None:
           print(f"Didn't find any of {filename}")
           return 0, 0, 0

        # Draw rectangle around object we are targeting
        cv2.rectangle(self.CurrentImg_RGB, (ptY, ptX), ((ptY + w), (ptX + h)), (0, 0, 255), 2)

        # Draw line to target
        cv2.line(self.CurrentImg_RGB, (player_y, player_x), (ptY, ptX), (0, 0, 255), 2)

        angle = self.calculate_angle(player_x, player_y, ptX, ptY)

        cv2.imwrite(f'result_{filename}', self.CurrentImg_RGB)
        return angle, ptX, ptY

    def get_player_screen(self):
        """
        :param gameWindow:
        :return None:

        Takes the snapshot of the game inside self.CurrentFile
        Uses Tesseract to convert any text on screen to a string
        Read that string to decide what the player is up to
        Certain keywords only appear at specific moments,
        e.g. POKEDEX is only readable when the main menu has been opened
        Set our gamestate to one of the enum entries
        """

        text = pytesseract.image_to_string(self.CurrentFile)

        if re.findall("appeare", text):
            self.CurrentGameState = self.GameState.Enemy_Appeared
            print(self.CurrentGameState)
            return

        if re.findall("FIGHT", text):
            self.CurrentGameState = self.GameState.Ready_To_Fight
            print(self.CurrentGameState)
            return

        else:
            found, filename = self.find_other_screens()

            if found:
                print(f"Found screen - {filename}")

                if filename == "PokeCenter.png":
                    self.CurrentGameState = self.GameState.In_PokeCenter
                    return

                if filename == "titlescreen.png":
                    self.CurrentGameState = self.GameState.On_Start_Menu
                    return

            else:
                # Don't take into account the main menu yet, lets assume always in world
                self.CurrentGameState = self.GameState.In_World
                print(self.CurrentGameState)
                return

    def find_other_screens(self):
        """
        Find other locations that the player might be in, such as titlescreen, pokecenter
        :return:
        """

        located = None

        for count, filename in enumerate(os.listdir('.\\Haystack\\Places')):

            template = cv2.imread(f'.\\Haystack\\Places\\{filename}')
            w, h = template.shape[:-1]

            res = cv2.matchTemplate(self.CurrentImg_RGB, template, cv2.TM_CCOEFF_NORMED)
            threshold = 0.65
            loc = np.where(res >= threshold)

            for count, pt in enumerate(zip(*loc[::-1])):  # Switch columns and rows
                # Draw Rectangle around each object found on screen
                cv2.rectangle(self.CurrentImg_RGB, pt, (pt[0] + w * 2, pt[1] + h * 2), (0, 0, 255), 2)

                # Players exact position
                located = True

                cv2.circle(self.CurrentImg_RGB, (pt[0] + round(w / 2), pt[1] + round(h / 2)), 5, (0, 0, 255), -1)

                if located:
                    # print("Found Player")
                    return located, filename

            # print(f"The shortest distance is: {lowest_value} at index: {lowest_value_index}")
            # cv2.line(self.CurrentImg_RGB, (x,x), (y,y), (0, 0, 255), 2)
            # cv2.line(self.CurrentImg_RGB, (x, y), (y, x), (0, 0, 255), 2)

            cv2.imwrite(f'result_{filename}', self.CurrentImg_RGB)
        if not located:
            print("Cant find this location")
            return located, "none"

    def remove_old_image(self):
        folder = './/Images'

        if len(os.listdir(folder)) > 0:
            for filename in os.listdir(folder):
                file_path = os.path.join(folder, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print('Failed to delete %s. Reason: %s' % (file_path, e))


def findgame():

    top_windows = []
    win32gui.EnumWindows(windowEnumerationHandler, top_windows)

    print("Finding RetroArch")
    for i in top_windows:
        if re.findall("RetroArch", i[1]):
            print("Found it! Bringing to foreground...")

            win32gui.ShowWindow(i[0], win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(i[0])

            pid = i[0]

            # Give Windows time to bring it to the front as its not instant
            time.sleep(0.1)
            return pid

    else:
        exit("No App Found")


def Screenshot_Game(window_title=None):
    if window_title:
        hwnd = win32gui.FindWindow(None, window_title)
        if hwnd:
            win32gui.SetForegroundWindow(hwnd)
            x, y, x1, y1 = win32gui.GetClientRect(hwnd)
            x, y = win32gui.ClientToScreen(hwnd, (x, y))
            x1, y1 = win32gui.ClientToScreen(hwnd, (x1 - x, y1 - y))
            im = pyautogui.screenshot(region=(x, y, x1, y1))
            return im
        else:
            print('Window not found!')
    else:
        im = pyautogui.screenshot()
        return im

def getGameWindowSizePos(pid):
    windowref = win32gui.GetForegroundWindow()

    x, y, x1, y1 = win32gui.GetClientRect(windowref)
    x, y = win32gui.ClientToScreen(windowref, (x, y))
    x1, y1 = win32gui.ClientToScreen(windowref, (x1 - x, y1 - y))

    windowPosition = (x, y, x1, y1)

    # Tmp variables are null values
    flags, showcmd, minimizedpos, maximisedpos, windowposition = win32gui.GetWindowPlacement(windowref)

    windowname = win32gui.GetWindowText(pid)

    return windowname, windowPosition


def windowEnumerationHandler(hwnd, top_windows):
    top_windows.append((hwnd, win32gui.GetWindowText(hwnd)))


if __name__ == "__main__":
    pid = findgame()

    if win32gui.GetWindowRect(pid) != (0, 0, 400, 415):
        # Can be a window handle or one of HWND_BOTTOM, HWND_NOTOPMOST, HWND_TOP, or HWND_TOPMOST
        win32gui.SetWindowPos(pid, win32con.HWND_NOTOPMOST, 0, 0, 400, 415, 0)

    windowname, windowpos = getGameWindowSizePos(pid)

    pid_queue = queue.Queue()
    game_queue = queue.Queue()

    print(f"Starting PID Checking for {windowname}, game will stop if out of focus")

    # Main thread
    pid_checker = WindowChecker()
    pid_checker.start()

    # Dependent threads
    gameautomation = GameAutomation(game_queue)
    gameautomation.setDaemon(daemonic=True)
    gameautomation.start()

