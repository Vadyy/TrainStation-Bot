print('Initializing trainstation engine...')
import pyautogui as pygui
import time
import keyboard
import json
from threading import Thread
import queue
import os
import winsound

pygui.FAILSAFE = True
version = 0.5

# time cooldowns
elapsed = None
materialsCooldown = None
destinationDelay = None
bonusTrainCooldown = None
reloadCooldown = None

# seconds to wait for all trains to arrive
reSendCooldown = 12

# variable to start the main thread
start = False
# variable to start a shutdown in the main thread
shutdown = False
# variable to pause the execution of the main thread
paused = False

# variable to pause the train resending
resendPaused = False

# variable to determine if the right destination button was clicked before
clickedRight = False
# same as above
clickedLeft = False

# variable to check if the 7 minute journey is currently active
isJourneyActive = True
# variable to check if the destination is currently changing
isDestinationChanging = False

# setting to turn on or off the Auto Journey System
autoJourney = False
# setting to turn or on off the mouse sensitivty feature
mouseMoving = False

# variable to know what destination is currently ongoing
destination = 5 # default: 5 mins


# mouse coordinates
coords = {
    'train8': (1495, 682),
    'train7': (1520, 673),
    'train6': (1550, 665),
    'train5': (1565, 657),
    'train4': (1532, 656),
    'train3': (1513, 655), # maglev
    'train2': (1547, 643), # maglev
    'train1': (1596, 622), # hyperloop
    'dispatchClose': (1315, 240), # button
    'offerClose': (1262, 331), # button
    'offerExclusiveOffer': (1225, 363), # button
    'journeyEndClose': (952, 687), # button
    'resend': (1726, 697), # button
    'updateClose': (1326, 290),
    'newsClose': (1322, 241),
    '5min': (692, 726),
    '7min': (880, 726),
    '1hour': (880, 726),
    '2hours': (1055, 726)
}

regions = {
    'mainWindow': (0, 188,  1901, 634),
    'trafficLights': (0, 300,  63, 349),
    'city': (77, 378,  1746, 570),
    'city-floor': (81, 555,  1752, 607),
    'destinations': (586, 690,  1306, 770),
    'windowsArea': (468, 195,  1433, 835),
    'leftHalfScreen': (0, 0,  960, 1080),
    'reload': (0, 0,  120, 80)
}

class QueueThread(object):
    '''
        queue thread for running jobs
    '''
    def __init__(self):

        self.q = queue.Queue(maxsize=0)
        threads = 10

        for i in range(threads):
          worker = Thread(target=self.run, args=())
          worker.setDaemon(True)
          worker.start()


    def run(self):
        '''
            background method
        '''
        while True:
            method = self.q.get()
            try:
                method[0](method[1])
            except TypeError:
                method()
            self.q.task_done()

class listenForKeys(object):
    '''
        background class for a keyboard listener
    '''

    def __init__(self, interval=.07):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in seconds
        """
        self.interval = interval

        thread = Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.setDaemon(True)
        thread.start()                                  # Start the execution




    def run(self):
        '''
            background method for keyboard listening
        '''

        global start
        global paused
        global shutdown
        global resendPaused
        while True:
            time.sleep(self.interval)
            if mouseMoving:
                checkIfMouseIsMoving()

            # shutdown request
            try:
                if keyboard.is_pressed('esc'):
                    print('shutdown request detected, shutting down...')
                    shutdown = True
                    start = True
                    break
            except:
                pass

            # pause
            if not paused:
                try:
                    if keyboard.is_pressed('alt+p'):
                        print('pause request detected, pausing...')
                        paused = True
                except:
                    pass

            if paused:
                try:
                    if keyboard.is_pressed('alt+r'):
                        print('resume request detected, resuming...')
                        paused = False
                except:
                    pass

            if paused:
                continue

            if not isDestinationChanging:
                try:
                    if keyboard.is_pressed('alt+5'):
                        print('Destination change request detected, initializing...')
                        queueThread.q.put((changeDestination, 5))
                except:
                    pass

                try:
                    if keyboard.is_pressed('alt+7'):
                        print('Destination change request detected, initializing...')
                        queueThread.q.put((changeDestination, 7))
                except:
                    pass

                try:
                    if keyboard.is_pressed('alt+2'): #20 minutes
                        print('Destination change request detected, initializing...')
                        queueThread.q.put((changeDestination, 20))
                except:
                    pass

                try:
                    if keyboard.is_pressed('ctrl+alt+1'): #1 hour
                        print('Destination change request detected, initializing...')
                        queueThread.q.put((changeDestination, 60))
                except:
                    pass

                try:
                    if keyboard.is_pressed('ctrl+alt+2'):
                        print('Destination change request detected, initializing...')
                        queueThread.q.put((changeDestination, 120))
                except:
                    pass

                try:
                    if keyboard.is_pressed('ctrl+alt+3'):
                        print('Destination change request detected, initializing...')
                        queueThread.q.put((changeDestination, 180))
                except:
                    pass

            if not start:
                try:
                    if keyboard.is_pressed('F2'):
                        queueThread.q.put((startBot))
                except:
                    pass
            if not resendPaused:
                try:
                    if keyboard.is_pressed('alt+0'):
                            print('~~ Resending paused!')
                            resendPaused = True
                except:
                    pass
            else:
                try:
                    if keyboard.is_pressed('alt+.'):
                            print('~~ Resending resumed!')
                            resendPaused = False
                except:
                    pass


def oldfindObject(image, gray=True, confidence=0.9):
    '''
        ~~ DEPRECATED ~~
        method to locate an object using pyAutoGui

        string image = object image name
           bool gray = use or not use grayscale
          confidence = percentage of location precision
    '''
    location = pygui.locateCenterOnScreen('data/img/{}.png'.format(image), grayscale=gray, confidence=confidence)
    if location is not None:
        x, y = location
        return (x, y)
    else:
        return None

def findObject(needle, region='mainWindow', gray=True, confidence=0.9):
    '''
        method to locate an object in a specific window using pyAutoGui

        string needle = object image name
               region = region to search in
            bool gray = use or not use grayscale
           confidence = percentage of location precision
    '''
    region = getRegion(region)
    haystackImage = pygui.screenshot(region=region)
    result = pygui.locate('data/img/{}.png'.format(needle), haystackImage, grayscale=gray, confidence=confidence)
    location = None
    if result is not None:
        relativeLocation = pygui.center(result)
        location = (relativeLocation[0] + region[0], relativeLocation[1] + region[1])

    if location is None:
        return None
    else:
        x, y = location
        return (x, y)


def click(object):
    '''
        method to click

        tuple object = (x, y)
    '''
    pygui.click(object[0], object[1])
    clearMouse()

def clearMouse():
    '''
        method to move mouse position to idle zone
    '''
    pygui.moveTo(20, 100)

def setup():
    '''
        method to move and resize the bot console
    '''
    cmd = findObject('cmd', region='leftHalfScreen')
    if cmd:
        # pygui.click(1920, 1080)
        # cmdt = findObject('cmdt')
        # if cmdt:
        #     click(cmdt)
        #window1
        pygui.moveTo(cmd[0], cmd[1])
        pygui.moveRel(20, 0)
        pygui.dragTo(1140, 520, .2)
        pygui.moveRel(0, -16)
        pygui.dragRel(0, 333, .1)
        #
        # explorer = findObject('explorer')
        # if explorer:
        #     click(explorer)
        # time.sleep(.1)

        # tg = findObject('telegram')
        # if tg:
        #     click(tg)
        #     click(tg)
        #     time.sleep(.5)
        #     cmd = findObject('cmd')
        #     if cmd:
        #         #window2
        #         pygui.moveTo(cmd[0], cmd[1])
        #         pygui.moveRel(10, 0)
        #         pygui.dragTo(25, 520, .5)
        #         pygui.moveRel(0, -16)
        #         pygui.dragRel(0, 333, .3)
        # chrome = findObject('chrome')
        # if chrome:
        #     click(chrome)
    else:
        print('no cmd')

def sendNotification():
    '''
        method to send notification information to the telegram bot
    '''
    data = {}
    # data['levelup'].append({
    #     'leveled' = 'yes'
    # })
    data['levelup'] = True

    with open('data/notifications/data.json', 'w') as outfile:
        json.dump(data, outfile)
    print(' ~~~ Leveled up! Sending notification...')

def clickRight():
    '''
        method to click on the dispatch scroll right button
    '''
    global clickedRight, clickedLeft
    rightBtn = findObject('destinationRight', region='windowsArea')
    if rightBtn:
        click(rightBtn)
        clickedRight = True
        clickedLeft = False
    else:
        print("ERROR: can't find the right destination button")

def clickLeft():
    '''
        method to click on the dispatch scroll left button
    '''
    global clickedRight, clickedLeft
    leftBtn = findObject('destinationLeft', region='windowsArea')
    if leftBtn:
        click(leftBtn)
        clickedRight = False
        clickedLeft = True
    else:
        print("ERROR: can't find the left destination button")

def setDestination(type):
    '''
        method
         to set the global variable of what destination is currently active

        integer type = destination's number of minutes
    '''
    global destination

    destination = type

def clickDestination(type):
    '''
        method to click on the dispatch window's destination buttons

        integer type = destination's number of minutes
    '''
    global destinationDelay
    global clickedRight
    global clickedLeft

    if type < 60:
        if clickedRight:
            clickLeft()
    elif type >= 60:
        if not clickedRight:
            clickRight()

    #if type < ...         #todo
    dispatch = findObject('dispatchReference', confidence=0.8, region="windowsArea")

    if dispatch:
        if type == 5:
            #destination = findObject('5min', region='destinations')
            click(getCoord('5min'))
        elif type == 7:
            #destination = findObject('7min', region='destinations', confidence=0.8, gray=False)
            click(getCoord('7min'))
            isJourneyActive = True
        elif type == 20:
            destination = findObject('20min', region='destinations')
        elif type == 60:
            click(getCoord('1hour'))
        elif type == 120:
            click(getCoord('2hours'))

        destinationDelay = time.time()
    # if destination:
    #     click(destination)
    #
    # else:
    #     #print("Can't find the destination")
    #     pass

def getRegion(region):
    '''
        method to retrieve a region coordinate

        tuple return = (x, y,  w, h)
    '''
    return regions[region]

def getCoord(coordinate):
    '''
        method to retrieve a location coordinate

        tuple return = (x, y)
    '''
    return coords[coordinate]

def changeDestination(type):
    '''
        method to change the trains destination

        integer type = destination's number of minutes
    '''
    global destinationDelay, shutdown, paused, start
    paused = True
    isDestinationChanging = True
    print(f'~~~ Changing destination to {type}')
    destinationDelay = time.time()
    setDestination(type)
    while True:
        #print('Clicking trains')
        pygui.doubleClick(getCoord('train8')) # 7th train
        clickDestination(type)
        pygui.doubleClick(getCoord('train7')) # 7th train
        clickDestination(type)
        pygui.doubleClick(getCoord('train6')) # 6th train
        clickDestination(type)
        pygui.doubleClick(getCoord('train5')) # 5th train
        clickDestination(type)
        pygui.doubleClick(getCoord('train4')) # 4th train
        clickDestination(type)
        pygui.doubleClick(getCoord('train3')) # 3rd train maglev
        clickDestination(type)
        pygui.doubleClick(getCoord('train2')) # 2nd train maglev
        clickDestination(type)
        pygui.doubleClick(getCoord('train1')) # 1st train hyperloop
        clickDestination(type)

        closeAll()

        if shutdown:
            break

        if (time.time() - destinationDelay) > 40:
            print(' ~ Hooray! Finished sending trains')
            playBEEP2()
            paused = False
            isDestinationChanging = False
            if not start:
                startBot()
            break

def clickBonusTrain():
    '''
        method to click on all train locations for a possible bonus train
    '''
    pygui.doubleClick(getCoord('train8')) # 7th train
    checkOffer()
    pygui.doubleClick(getCoord('train7')) # 7th train
    checkOffer()
    pygui.doubleClick(getCoord('train6')) # 6th train
    checkOffer()
    pygui.doubleClick(getCoord('train5')) # 5th train
    checkOffer()
    pygui.doubleClick(getCoord('train4')) # 4th train
    checkOffer()
    pygui.doubleClick(getCoord('train3')) # 3rd train maglev
    checkOffer()
    pygui.doubleClick(getCoord('train2')) # 2nd train maglev
    checkOffer()
    pygui.doubleClick(getCoord('train1')) # 1st train hyperloop
    checkOffer()

def checkOffer():
    '''
        method to check if the exclusive offer ad menu is visible and close it
    '''
    offer = findObject('offer', region='windowsArea')
    if offer:
        print('Found advertisement')

        closeOffer()

def checkJourney():
    '''
        method to check if the special 7 minutes destination menu is visible, close it and run autoJourney
    '''
    global isJourneyActive
    journey = findObject('journey', region='windowsArea', confidence=0.8)
    if journey:
        print('~ Journey started!')
        close = findObject('close', region='windowsArea', confidence=0.8)
        if close:
            click(close)


        if autoJourney:
            # change destination to the journey
            isJourneyActive = True
            print('~ Changing destination to the journey')
            time.sleep(1)
            print('~  waiting 5 minutes for all trains to arrive') # job
            time.sleep(300)
            changeDestination(7)

def checkEndJourney():
    '''
        method to check if the special 7 minutes destination end menu is visible, close it and stop autoJourney
    '''
    global isJourneyActive
    if not isJourneyActive:
        return
    journey = findObject('journey-end', region='windowsArea', confidence=0.75)
    if journey:
        print('~ Journey ended!')
        click(getCoord('journeyEndClose'))
        isJourneyActive = False

        playBEEP()

        # change destination back to normal
        print('~ Changing destination back to default')
        print('~  Waiting 7 minutes for all trains to arrive') # job
        time.sleep(420)
        changeDestination(5)

def checkLevelUP():
    '''
        method to check if the level up menu is visible, close it and send a notification
    '''
    levelup = findObject('levelup', region='windowsArea', confidence = 0.85)
    if levelup:
        print('~ Found the level-up menu')
        collect = findObject('collect-lvlup', region='windowsArea', confidence = 0.8)
        if collect:
            click(collect)
        else:
            print("~~~ ERROR: Couldn't find the levelup collect button...")
        sendNotification()

def checkDaily():
    '''
        method to check if daily reward menu is visible and collect it
    '''
    daily = findObject('daily', region='windowsArea', confidence=0.8)
    if daily:
        print('~ Found the daily menu')
        sure = findObject('daily-btn', region='windowsArea', confidence=0.7)
        if sure:
            click(sure)
        else:
            print("~~~ ERROR: Couldn't find the daily sure button...")

def checkForMenus():
    '''
        method to check for all windows
    '''
    # advertisement
    checkOffer()

    # journey unlocked
    checkJourney()

    # journey finished
    checkEndJourney()

    # levelup
    checkLevelUP()

    # daily
    checkDaily()

def resendTrains():
    '''
        method to resend the trains to their destination
    '''
    global elapsed
    greenTrafficLight = findObject('waiting-trains', region='trafficLights', gray=False)
    orangeTrafficLight = findObject('orange-signal', region='trafficLights', gray=False)
    if greenTrafficLight or orangeTrafficLight:
        click(getCoord('resend'))
        time.sleep(.9)
        click(getCoord('resend'))
        time.sleep(.1)
        click(getCoord('resend'))
        elapsed = time.time()

def collectTrains():
    '''
        method to collect the halftime bonus from the trains
    '''
    collect = findObject('collect')
    if collect:
        #print('Found Collect, clicking...')
        click(collect)

def pumpkin():
    '''
        method to find and click on the halloween pumpkin
    '''
    pumpkin = findObject('pumpkin', region='city-floor', confidence = 0.7)
    if pumpkin:
        #print('Found pumpkin')
        click(pumpkin)
        time.sleep(.3)
        collectBtn = findObject('collect-btn', region='windowsArea', confidence = 0.8)
        if collectBtn:
            click(collectBtn)
        else:
            print("~~~ ERROR: Couldn't find the pumpkin collect button...")


def skull():
    '''
        method to find and click on the halloween skull
    '''
    skull = findObject('skull', region='city')
    if skull:
        click(skull)

def screenshotMaterials():
    '''
        method to screenshot the materials window and save it for notifications
    '''
    materials = findObject('materials')
    if materials:
        click(materials)
        time.sleep(.4)
        pygui.click(1311, 329) # scroll down a bit
        time.sleep(.2)
        im = pygui.screenshot(region=(580, 230, 730, 520))
        im.save('data/notifications/materials.jpg')
        im.close()
        close = findObject('close-mats')
        if close:
            click(close)

def requestsCheck():
    '''
        method to check if there is any request from the keyboard
    '''
    global start, paused, shutdown
    if not start:
        return True
    elif paused:
        return True
    elif shutdown:
        os._exit(0)
    else:
        return False

def resetWindow():
    '''
        method to set the trainstation window to default
    '''
    print('Resetting Window...')
    # move to dragging position
    pygui.moveTo(1516, 379)
    pygui.click()

    # drag up
    for x in range(1, 4):
        pygui.dragRel(0, -100, .15)
        pygui.moveTo(1516, 379)


    # drag left
    for x in range(1, 4):
        pygui.dragRel(-100, 0, .15)
        pygui.moveTo(1516, 379)

    # zoom out
    for x in range(1, 8):
        pygui.scroll(-50)



def startBot():
    '''
        method to start the main bot thread
    '''
    global start
    print('~ Starting Bot')
    resetWindow()
    start = True


def closeDispatch():
    '''
        method to click on the x button for the dispatch window
    '''
    click(getCoord('dispatchClose'))

def closeOffer():
    '''
        method to click on the x button for the offer window
    '''
    click(getCoord('offerClose'))

def closeExclusiveOffer():
    '''
        method to click on the x button for the second type of offer window
    '''
    click(getCoord('offerExclusiveOffer'))

def closeNews():
    '''
        method to click on the x button for the news window
    '''
    click(getCoord('newsClose'))

def closeUpdate():
    '''
        method to click on the x button for the update window
    '''
    click(getCoord('updateClose'))

def closeAll():
    """
        method to close all possible windows
    """
    closeDispatch()
    closeOffer()
    closeExclusiveOffer()

def reloadPage():
    """
        method to refresh the browser once an hour
    """
    reload = findObject('reload', region='reload')
    if reload:
        print('RELOAD: waiting one minute to save then reloading')
        time.sleep(60)
        print('RELOAD: refreshing page')
        click(reload)
        print('RELOAD: waiting two minutes after reload')
        time.sleep(120)
        closeUpdate()
        time.sleep(2)
        closeNews()

def setCooldowns():
    """
        method to setup the cooldowns
    """
    global materialsCooldown, bonusTrainCooldown, reloadCooldown
    if materialsCooldown is None:
        materialsCooldown = time.time()

    if bonusTrainCooldown is None:
        bonusTrainCooldown = time.time()

    if reloadCooldown is None:
        reloadCooldown = time.time()

def doCooldownWork():
    """
        method to do the cooldowned work
    """
    global materialsCooldown, bonusTrainCooldown, reloadCooldown
    if materialsCooldown is not None:
        if (time.time() - materialsCooldown) > 600:
            screenshotMaterials()
            materialsCooldown = None

    if bonusTrainCooldown is not None:
        if (time.time() - bonusTrainCooldown) > 500:
            trafficLight = findObject('orange-signal', region='trafficLights')
            if trafficLight:
                clickBonusTrain()
                closeAll() # close all possible windows
            bonusTrainCooldown = None

    if reloadCooldown is not None:
        if (time.time() - reloadCooldown) > 3600:
            reloadPage()
            reloadCooldown = None

def unlockOtherWork():
    """
        method unlock the other work
    """
    global elapsed
    if (time.time() - elapsed) > 25:
        #print('~ Main work done, doing other work...')
        elapsed = None

def checkIfMouseIsMoving():
    global paused
    if not paused and start:
        pos = pygui.position()
        time.sleep(.01)
        superPosition = pygui.position()[0] + pygui.position()[1]
        if abs(superPosition - (pos[0] + pos[1])) > 6 and abs(superPosition - (pos[0] + pos[1])) < 50:
            print('Detected mouse moving, pausing bot')
            paused = True

def playBEEP():
    for x in range(3):
        winsound.PlaySound('data/sounds/beep.wav', winsound.SND_FILENAME)

def playBEEP2():
    for x in range(3):
        winsound.PlaySound('data/sounds/beep2.wav', winsound.SND_FILENAME)

# creating threads
keyListener = listenForKeys()
queueThread = QueueThread()

print(f'Trainstation bot v{version} succesfully started')

# setting up the console
setup()

# main thread
while True:
    time.sleep(0.05)
    if shutdown:
        break

    # ~ checks ~
    # requests check
    if requestsCheck():
        continue


    checkForMenus()
    # ~ end of checks ~

    if requestsCheck():
        continue

    # ~ main work ~
    if not resendPaused:
        resendTrains()

    collectTrains()
    # ~ end of main work ~

    if requestsCheck():
        continue

    # setting up the cooldowns
    setCooldowns()

    # block other work
    if elapsed is not None:
        unlockOtherWork()

    if requestsCheck():
        continue

    # other work
    if elapsed is None:
        #pumpkin
        pumpkin()

        #skull
        skull()

        # materials screenshot
        doCooldownWork()
