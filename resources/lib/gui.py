
import xbmc, xbmcgui, xbmcaddon
import string, glob, time, array, os, sys, shutil, re
from threading import *

from util import *
import util
import dbupdate, helper, launcher, config
import dialogimportoptions, dialogcontextmenu, dialogprogress, dialogmissinginfo
from config import *
from configxmlupdater import *
import wizardconfigxml
from gamedatabase import *


#Action Codes
# See guilib/Key.h
ACTION_CANCEL_DIALOG = (9,10,51,92,110)
ACTION_PLAYFULLSCREEN = (12,79,227)
ACTION_MOVEMENT_LEFT = (1,)
ACTION_MOVEMENT_RIGHT = (2,)
ACTION_MOVEMENT_UP = (3,)
ACTION_MOVEMENT_DOWN = (4,)
ACTION_MOVEMENT = (1, 2, 3, 4, 5, 6, 159, 160)
ACTION_INFO = (11,)
ACTION_CONTEXT = (117,)


#ControlIds
CONTROL_CONSOLES = 500
CONTROL_GENRE = 600
CONTROL_YEAR = 700
CONTROL_PUBLISHER = 800
CONTROL_CHARACTER = 900
FILTER_CONTROLS = (500, 600, 700, 800, 900,)
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONTROL_SCROLLBARS = (2200, 2201, 60, 61, 62)

CONTROL_GAMES_GROUP_START = 50
CONTROL_GAMES_GROUP_END = 59

CONTROL_BUTTON_CHANGE_VIEW = 2
#CONTROL_BUTTON_FAVORITE = 1000
#CONTROL_BUTTON_SEARCH = 1100
CONTROL_BUTTON_VIDEOFULLSCREEN = (2900, 2901,)
NON_EXIT_RCB_CONTROLS = (500, 600, 700, 800, 900, 2, 1000, 1100)

CONTROL_LABEL_MSG = 4000
CONTROL_BUTTON_MISSINGINFODIALOG = 4001

ACTION_PREVIOUS_MENU = 10

class MyPlayer(xbmc.Player):
    
    gui = None
    
    def onPlayBackEnded(self):
        print 'RCB: onPlaybackEnded'
        
        if(self.gui == None):
            print "RCB_WARNING: gui == None in MyPlayer"
            return
        
        self.gui.setFocus(self.gui.getControl(CONTROL_GAMES_GROUP_START))


class PopupWindow(xbmcgui.Window):

    def __init__(self, *args, **kwargs):
        super(PopupWindow, self).__init__(*args, **kwargs)
        self.url = kwargs.pop('url')
        self.addControl(xbmcgui.ControlLabel(x=190, y=25, width=500, height=25, label="Noooo " + self.url))

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()


class UIGameDB(xbmcgui.WindowXML):
    
    gdb = None
    
    selectedControlId = 0
    selectedConsoleId = 0
    selectedGenreId = 0
    selectedYearId = 0
    selectedPublisherId = 0
    selectedCharacter = util.localize(40020)
    
    selectedConsoleIndex = 0
    selectedGenreIndex = 0
    selectedYearIndex = 0
    selectedPublisherIndex = 0
    selectedCharacterIndex = 0
        
    rcb_playList = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)
    playlistOffsets = {}
    
    applyFilterThread = None
    applyFilterThreadStopped = False
    applyFiltersInProgress = False
    
    filterChanged = False
    
    
    #last selected game position (prevent invoke showgameinfo twice)
    lastPosition = -1
        
    #dummy to be compatible with ProgressDialogGUI
    itemCount = 0
        
    # set flag if we are watching fullscreen video
    fullScreenVideoStarted = False
    # set flag if we opened GID
    gameinfoDialogOpen = False
            
    #cachingOption will be overwritten by config. Don't change it here.
    cachingOption = 3
    
    useRCBService = False
    searchTerm = ''
    
    #HACK: just used to determine if we are on Dharma or Eden.
    xbmcVersionEden = False
    try:
        from sqlite3 import dbapi2 as sqlite
        xbmcVersionEden = True
        Logutil.log("XBMC version: Assuming we are on Eden", util.LOG_LEVEL_INFO)
    except:     
        Logutil.log("XBMC version: Assuming we are on Dharma", util.LOG_LEVEL_INFO)
    
    
    def __init__(self, strXMLname, strFallbackPath, strDefaultName, forceFallback):
        Logutil.log("Init Rom Collection Browser: " + util.RCBHOME, util.LOG_LEVEL_INFO)
        
        addon = xbmcaddon.Addon(id='%s' %util.SCRIPTID)
        Logutil.log("RCB version: " + addon.getAddonInfo('version'), util.LOG_LEVEL_INFO)
            
        #check if RCB service is available, otherwise we will use autoexec.py
        try:
            serviceAddon = xbmcaddon.Addon(id=util.SCRIPTID)
            Logutil.log("RCB service addon: " + str(serviceAddon), util.LOG_LEVEL_INFO)
            self.useRCBService = True
        except:
            Logutil.log("No RCB service addon available. Will use autoexec.py for startup features.", util.LOG_LEVEL_INFO)
            
        self.initialized = False
        self.Settings = util.getSettings()
        
        #Make sure that we don't start RCB in cycles
        self.Settings.setSetting('rcb_launchOnStartup', 'false')
            
        
        #check if background game import is running
        if self.checkUpdateInProgress():
            self.quit = True
            return
        
        #timestamp1 = time.clock()
        
        self.quit = False
                
        self.config, success = self.initializeConfig()
        if not success:
            self.quit = True
            return
        
        success = self.initializeDataBase()
        if not success:
            self.quit = True
            return
        
        cachingOptionStr = self.Settings.getSetting(util.SETTING_RCB_CACHINGOPTION)
        if(cachingOptionStr == 'CACHEALL'):
            self.cachingOption = 0
        #elif(cachingOptionStr == 'CACHESELECTION'):
        #   self.cachingOption = 1
        elif(cachingOptionStr == 'CACHEITEM'):
            self.cachingOption = 2
        elif(cachingOptionStr == 'CACHEITEMANDNEXT'):
            self.cachingOption = 3
        
        self.cacheItems()
        
        #load video fileType for later use in showGameInfo
        self.fileTypeGameplay, errorMsg = self.config.readFileType('gameplay', self.config.tree)        
        if(self.fileTypeGameplay == None):
            Logutil.log("Error while loading fileType gameplay: " +errorMsg, util.LOG_LEVEL_WARNING)            
        
        #timestamp2 = time.clock()
        #diff = (timestamp2 - timestamp1) * 1000        
        #print "RCB startup time: %d ms" % (diff)
        
        self.player = MyPlayer()
        self.player.gui = self
                
        self.initialized = True
        
        
    def initializeConfig(self):     
        Logutil.log("initializeConfig", util.LOG_LEVEL_INFO)
        
        config = Config(None)
        createNewConfig = False
        
        #check if we have config file
        configFile = util.getConfigXmlPath()
        if(not os.path.isfile(configFile)):
            Logutil.log("No config file available. Create new one.", util.LOG_LEVEL_INFO)
            dialog = xbmcgui.Dialog()
            createNewConfig = dialog.yesno(util.SCRIPTNAME, util.localize(40000), util.localize(40001))
            if(not createNewConfig):
                return config, False
        else:
            rcAvailable, message = config.checkRomCollectionsAvailable()
            if(not rcAvailable):
                Logutil.log("No Rom Collections found in config.xml.", util.LOG_LEVEL_INFO)
                dialog = xbmcgui.Dialog()
                createNewConfig = dialog.yesno(util.SCRIPTNAME, util.localize(40000), util.localize(40001))
                if(not createNewConfig):
                    return config, False
        
        if (createNewConfig):
            statusOk, errorMsg = wizardconfigxml.ConfigXmlWizard().createConfigXml(configFile)
            if(statusOk == False):
                xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(35001), errorMsg)
                return config, False
        else:
            #check if config.xml is up to date
            returnCode, message = ConfigxmlUpdater().updateConfig(self)
            if(returnCode == False):
                xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(35001), message)
        
        #read config.xml        
        statusOk, errorMsg = config.readXml()
        if(statusOk == False):
            xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(35002), errorMsg)
            
        return config, statusOk
        
        
    def initializeDataBase(self):
        try:
            self.gdb = GameDataBase(util.getAddonDataPath())
            self.gdb.connect()
        except Exception, (exc):
            xbmcgui.Dialog().ok(util.SCRIPTNAME, util.localize(35000), str(exc))
            Logutil.log('Error accessing database: ' +str(exc), util.LOG_LEVEL_ERROR)
            return False
       
        return True
                        
        
    def onInit(self):
        
        Logutil.log("Begin onInit", util.LOG_LEVEL_INFO)
        
        if(self.quit):
            Logutil.log("RCB decided not to run. Bye.", util.LOG_LEVEL_INFO)
            self.close()
            return
        
        self.clearList()
        self.rcb_playList.clear()
        xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
                
        self.showGames()
        
        #
        #always set focus on game list on start
        focusControl = self.getControlById(CONTROL_GAMES_GROUP_START)
        if(focusControl != None):
            self.setFocus(focusControl)
        
        self.showGameInfo()

        Logutil.log("End onInit", util.LOG_LEVEL_INFO)

    
    def onAction(self, action):
        
        Logutil.log("onAction: " +str(action.getId()), util.LOG_LEVEL_INFO)
        
        if(action.getId() == 0):
            Logutil.log("actionId == 0. Input ignored", util.LOG_LEVEL_INFO)
            return
                            
        try:
            if(action.getId() in ACTION_CANCEL_DIALOG):
                Logutil.log("onAction: ACTION_CANCEL_DIALOG", util.LOG_LEVEL_INFO)
                    
                #don't exit RCB here. Just close the filters        
                if(self.selectedControlId in NON_EXIT_RCB_CONTROLS):
                    Logutil.log("selectedControl in NON_EXIT_RCB_CONTROLS: %s" %self.selectedControlId, util.LOG_LEVEL_INFO)
                    #HACK: when list is empty, focus sits on other controls than game list
                    if(self.getListSize() > 0):
                        self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
                        return
                    
                    Logutil.log("ListSize == 0 in onAction. Assume that we have to exit.", util.LOG_LEVEL_WARNING)
                            
                if(self.player.isPlayingVideo()):
                    self.player.stop()
                    xbmc.sleep(util.WAITTIME_PLAYERSTOP)
                                
                self.exit()
            elif(action.getId() in ACTION_MOVEMENT):
                                                        
                Logutil.log("onAction: ACTION_MOVEMENT", util.LOG_LEVEL_DEBUG)
                
                control = self.getControlById(self.selectedControlId)
                if(control == None):
                    Logutil.log("control == None in onAction", util.LOG_LEVEL_WARNING)                  
                    return
                    
                if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):
                    if(not self.fullScreenVideoStarted):
                        if(self.cachingOption > 0):
                            #HACK: check last position in list (prevent loading game info)
                            pos = self.getCurrentListPosition()
                            Logutil.log('onAction: current position = ' +str(pos), util.LOG_LEVEL_DEBUG)
                            Logutil.log('onAction: last position = ' +str(self.lastPosition), util.LOG_LEVEL_DEBUG)
                            if(pos != self.lastPosition):                           
                                self.showGameInfo()
                            
                            self.lastPosition = pos
                                    
                if(self.selectedControlId in FILTER_CONTROLS):
                    
                    if(self.player.isPlayingVideo()):
                        self.player.stop()
                        xbmc.sleep(util.WAITTIME_PLAYERSTOP)
                    
                    label = str(control.getSelectedItem().getLabel())
                    label2 = str(control.getSelectedItem().getLabel2())
                    
                    if (self.selectedControlId == CONTROL_CONSOLES):
                        if(self.selectedConsoleIndex != control.getSelectedPosition()):
                            self.selectedConsoleId = int(label2)
                            self.selectedConsoleIndex = control.getSelectedPosition()
                            self.filterChanged = True
                            
                    elif (self.selectedControlId == CONTROL_GENRE):
                        if(self.selectedGenreIndex != control.getSelectedPosition()):
                            self.selectedGenreId = int(label2)
                            self.selectedGenreIndex = control.getSelectedPosition()
                            self.filterChanged = True
                            
                    elif (self.selectedControlId == CONTROL_YEAR):
                        if(self.selectedYearIndex != control.getSelectedPosition()):
                            self.selectedYearId = int(label2)
                            self.selectedYearIndex = control.getSelectedPosition()
                            self.filterChanged = True
                            
                    elif (self.selectedControlId == CONTROL_PUBLISHER):
                        if(self.selectedPublisherIndex != control.getSelectedPosition()):
                            self.selectedPublisherId = int(label2)
                            self.selectedPublisherIndex = control.getSelectedPosition()
                            self.filterChanged = True
                            
                    elif (self.selectedControlId == CONTROL_CHARACTER):
                        if(self.selectedCharacterIndex != control.getSelectedPosition()):
                            self.selectedCharacter = label
                            self.selectedCharacterIndex = control.getSelectedPosition()
                            self.filterChanged = True
                
            elif(action.getId() in ACTION_INFO):
                Logutil.log("onAction: ACTION_INFO", util.LOG_LEVEL_DEBUG)
                
                control = self.getControlById(self.selectedControlId)
                if(control == None):
                    Logutil.log("control == None in onAction", util.LOG_LEVEL_WARNING)
                    return
                if(CONTROL_GAMES_GROUP_START <= self.selectedControlId <= CONTROL_GAMES_GROUP_END):
                    self.showGameInfoDialog()
            elif (action.getId() in ACTION_CONTEXT):
                
                if(self.player.isPlayingVideo()):
                    self.player.stop()
                    xbmc.sleep(util.WAITTIME_PLAYERSTOP)
                
                self.showContextMenu()
                
                self.setFocus(self.getControl(CONTROL_GAMES_GROUP_START))
                
                Logutil.log('onAction: ACTION_CONTEXT', util.LOG_LEVEL_INFO)                                
            elif (action.getId() in ACTION_PLAYFULLSCREEN):
                #HACK: check if we are in Eden mode
                if(self.xbmcVersionEden):
                    Logutil.log('onAction: ACTION_PLAYFULLSCREEN', util.LOG_LEVEL_INFO)
                    self.startFullscreenVideo()
                else:
                    Logutil.log('fullscreen video in Dharma is not supported.', util.LOG_LEVEL_WARNING)
                
        except Exception, (exc):
            Logutil.log("RCB_ERROR: unhandled Error in onAction: " +str(exc), util.LOG_LEVEL_ERROR)
            

    def onClick(self, controlId):
        
        Logutil.log("onClick: " + str(controlId), util.LOG_LEVEL_DEBUG)
        
        if (controlId in GAME_LISTS):
            Logutil.log("onClick: Launch Emu", util.LOG_LEVEL_DEBUG)
            self.launchEmu()

    def onFocus(self, controlId):
        Logutil.log("onFocus: " + str(controlId), util.LOG_LEVEL_DEBUG)
        self.selectedControlId = controlId
        
        
    def showGames(self):
        Logutil.log("Begin showGames" , util.LOG_LEVEL_INFO)
        
        self.lastPosition = -1
        
        preventUnfilteredSearch = self.Settings.getSetting(util.SETTING_RCB_PREVENTUNFILTEREDSEARCH).upper() == 'TRUE'          
        
        if(preventUnfilteredSearch):            
            if(self.selectedCharacter == util.localize(40020) and self.selectedConsoleId == 0 and self.selectedGenreId == 0 and self.selectedYearId == 0 and self.selectedPublisherId == 0):
                Logutil.log("preventing unfiltered search", util.LOG_LEVEL_WARNING)
                return              
        
        timestamp1 = time.clock()
        
        # build statement for character search (where name LIKE 'A%')
        likeStatement = helper.buildLikeStatement(self.selectedCharacter, self.searchTerm)
        
        #build statement for missing filters
        missingFilterStatement = helper.builMissingFilterStatement(self.config)
        if(missingFilterStatement != ''):
            likeStatement = likeStatement + ' AND ' +missingFilterStatement
        
        games = Game(self.gdb).getFilteredGames(self.selectedConsoleId, self.selectedGenreId, self.selectedYearId, self.selectedPublisherId, 0, likeStatement)
        
        if(games == None):
            Logutil.log("games == None in showGames", util.LOG_LEVEL_WARNING)
            return      
                
        fileDict = self.getFileDictForGamelist()
                
        timestamp2 = time.clock()
        diff = (timestamp2 - timestamp1) * 1000
        print "showGames: load games from db in %d ms" % (diff)
    
        self.writeMsg(util.localize(40021))
        
        if(not self.xbmcVersionEden):
            xbmcgui.lock()
        
        self.clearList()
        self.rcb_playList.clear()       
       
        
        count = 0

        from xml.dom.minidom import parse, Document, _write_data, Node, Element
        RssFeedsPath = xbmc.translatePath('special://userdata/RssFeeds.xml').decode("utf-8")
        feedsTree = parse(RssFeedsPath)
        feeds = feedsTree.getElementsByTagName('feed')
        #feed.firstChild.toxml()

        for feed in feeds:
            name = feed.firstChild.toxml()
            item = xbmcgui.ListItem(name, name)
            item.setProperty('url', name)
            #item.setProperty(util.IMAGE_CONTROL_BACKGROUND, '/home/media/ninja-parade.png')
            #item.setProperty(util.IMAGE_CONTROL_GAMEINFO_BIG, '/home/media/ninja-parade.png')
            self.addItem(item)
            count +=1
       
        '''
        for gameRow in games:
                        
            romCollection = None
            try:
                romCollection = self.config.romCollections[str(gameRow[util.GAME_romCollectionId])]
            except:
                Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
        
            try:
                #images for gamelist
                imageGameList = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForGameList, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
                imageGameListSelected = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForGameListSelected, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
                
                #create ListItem
                item = xbmcgui.ListItem(gameRow[util.ROW_NAME], str(gameRow[util.ROW_ID]), imageGameList, imageGameListSelected)            
                item.setProperty('gameId', str(gameRow[util.ROW_ID]))
                
                #favorite handling
                showFavoriteStars = self.Settings.getSetting(util.SETTING_RCB_SHOWFAVORITESTARS).upper() == 'TRUE'
                isFavorite = helper.saveReadString(gameRow[util.GAME_isFavorite])
                if(isFavorite == '1' and showFavoriteStars):
                    item.setProperty('isfavorite', '1')
                else:
                    item.setProperty('isfavorite', '')
                #0 = cacheAll: load all game data at once
                if(self.cachingOption == 0):
                    self.setAllItemData(item, gameRow, self.fileDict, romCollection)                            
                                
                self.addItem(item, False)
                
                # add video to playlist for fullscreen support
                self.loadVideoFiles(item, gameRow, imageGameList, imageGameListSelected, count, fileDict, romCollection)
                    
                count = count + 1

                #if item == 2:
                #    imagemainViewBackground = u'/home/hedley/emulators/mame/artwork/boxfront/mk2.png'
                #    item.setProperty(util.IMAGE_CONTROL_BACKGROUND, imagemainViewBackground)

            except Exception, (exc):
                Logutil.log('Error loading game: %s' % str(exc), util.LOG_LEVEL_ERROR)
       
        '''

        xbmc.executebuiltin("Container.SortDirection")
        if(not self.xbmcVersionEden):
            xbmcgui.unlock()
        
        self.writeMsg("")
        
        Logutil.log("End showGames" , util.LOG_LEVEL_INFO)
        
    
    def showGameInfo(self):
        Logutil.log("Begin showGameInfo" , util.LOG_LEVEL_INFO)
        
        self.writeMsg("")
        
        if(self.getListSize() == 0):
            Logutil.log("ListSize == 0 in showGameInfo", util.LOG_LEVEL_WARNING)            
            return
                    
        pos = self.getCurrentListPosition()
        if(pos == -1):
            pos = 0
        
        selectedGame, gameRow = self.getGameByPosition(self.gdb, pos)
        if(selectedGame == None or gameRow == None):
            Logutil.log("game == None in showGameInfo", util.LOG_LEVEL_WARNING)         
            return
        
        romCollection = None
        try:
            romCollection = self.config.romCollections[str(gameRow[util.GAME_romCollectionId])]
        except:
            Logutil.log('Cannot get rom collection with id: ' +str(gameRow[util.GAME_romCollectionId]), util.LOG_LEVEL_ERROR)
            
        if(self.cachingOption == 0):
            fileDict = self.fileDict
        else:
            fileDict = self.getFileDictByGameRow(gameRow)
        
        #gameinfos are already loaded with cachingOption 0 (cacheAll)
        if(self.cachingOption > 0):
            self.loadGameInfos(gameRow, selectedGame, pos, romCollection, fileDict)
        
        video = selectedGame.getProperty('gameplaymain')
        if(video == "" or video == None or not romCollection.autoplayVideoMain):
            if(self.player.isPlayingVideo()):
                self.player.stop()
                
        Logutil.log("End showGameInfo" , util.LOG_LEVEL_INFO)
        
        
    def launchEmu(self):

        Logutil.log("Begin launchEmu" , util.LOG_LEVEL_INFO)

        if(self.getListSize() == 0):
            Logutil.log("ListSize == 0 in launchEmu", util.LOG_LEVEL_WARNING)
            return

        pos = self.getCurrentListPosition()
        if(pos == -1):
            pos = 0
        selectedGame = self.getListItem(pos)
        
        if(selectedGame == None):
            Logutil.log("selectedGame == None in launchEmu", util.LOG_LEVEL_WARNING)
            return
                    
        url = selectedGame.getProperty('url')
        Logutil.log("launching game with url: " + str(url), util.LOG_LEVEL_INFO)
        
        window = PopupWindow(url=url)
        window.doModal()
        del window
   
        #launcher.launchEmu(self.gdb, self, gameId, self.config, self.Settings, selectedGame)
        Logutil.log("End launchEmu" , util.LOG_LEVEL_INFO)
        
        
       
        
       
        
       
        
        
    """
    ******************
    * HELPER METHODS *
    ******************
    """
    
    def getFileDictForGamelist(self):
        # 0 = cacheAll
        if(self.cachingOption == 0):
            fileDict = self.fileDict
        else:
            fileRows = File(self.gdb).getFilesForGamelist(self.config.fileTypeIdsForGamelist)
            if(fileRows == None):
                Logutil.log("fileRows == None in showGames", util.LOG_LEVEL_WARNING)
                return
                    
            fileDict = helper.cacheFiles(fileRows)
        
        return fileDict
        
        
    def getFileForControl(self, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict):
        files = helper.getFilesByControl_Cached(self.gdb, fileTypes, gameId, publisherId, developerId, romCollectionId, fileDict)       
        if(files != None and len(files) != 0):
            file = files[0]
        else:
            file = ""
            
        return file
    
        
    def loadVideoFiles(self, listItem, gameRow, imageGameList, imageGameListSelected, count, fileDict, romCollection):
        
        #check if we should use autoplay video
        if(romCollection.autoplayVideoMain):
            listItem.setProperty('autoplayvideomain', 'true')
        else:
            listItem.setProperty('autoplayvideomain', '')
            
        #get video window size
        if (romCollection.imagePlacingMain.name.startswith('gameinfosmall')):
            listItem.setProperty('videosizesmall', 'small')
            listItem.setProperty('videosizebig', '')
        else:
            listItem.setProperty('videosizebig', 'big')
            listItem.setProperty('videosizesmall', '')
        
        #get video
        video = ""

        if(self.fileTypeGameplay == None):
            Logutil.log("fileType gameplay == None. No video loaded.", util.LOG_LEVEL_INFO)
        
        #load gameplay videos
        #HACK: other video types are not supported
        videos = helper.getFilesByControl_Cached(self.gdb, (self.fileTypeGameplay,), gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        if(videos != None and len(videos) != 0):
            video = videos[0]
            #make video accessable via UI
            listItem.setProperty('gameplaymain', video)
        
            #create dummy ListItem for playlist
            dummyItem = xbmcgui.ListItem(gameRow[util.ROW_NAME], str(gameRow[util.ROW_ID]), imageGameList, imageGameListSelected)
        
            #add video to playlist and compute playlistOffset (missing videos must be skipped)
            self.rcb_playList.add(video, dummyItem)
            try:
                if(len(self.playlistOffsets) == 0 or count == 0):
                    self.playlistOffsets[count] = 0                 
                else:
                    offset = self.playlistOffsets[count - 1]                    
                    self.playlistOffsets[count] = offset + 1                    
            except:
                Logutil.log("Error while creating playlist offset", util.LOG_LEVEL_WARNING)
        else:
            if(len(self.playlistOffsets) == 0 or count == 0):
                self.playlistOffsets[count] = 0             
            else:
                offset = self.playlistOffsets[count - 1]
                self.playlistOffsets[count] = offset
        
    
    def getGameByPosition(self, gdb, pos):
        Logutil.log("size = %i" % self.getListSize(), util.LOG_LEVEL_DEBUG)
        Logutil.log("pos = %s" % pos, util.LOG_LEVEL_DEBUG)
                
        selectedGame = self.getListItem(pos)
        if(selectedGame == None):
            Logutil.log("selectedGame == None in getGameByPosition", util.LOG_LEVEL_WARNING)
            return None, None
        
        gameId = selectedGame.getProperty('gameId')
        if(gameId == ''):
            Logutil.log("gameId is empty in getGameByPosition", util.LOG_LEVEL_WARNING)
            return None, None
        
        gameRow = Game(gdb).getObjectById(gameId)

        if(gameRow == None):            
            Logutil.log("gameId = %s" % gameId, util.LOG_LEVEL_WARNING)
            Logutil.log("gameRow == None in getGameByPosition", util.LOG_LEVEL_WARNING)
            return None, None
            
        return selectedGame, gameRow

        
    def getGameId(self, gdb, pos):
        Logutil.log("pos = %s" % pos, util.LOG_LEVEL_INFO)
        
        selectedGame = self.getListItem(pos)

        if(selectedGame == None):
            Logutil.log("selectedGame == No game selected", util.LOG_LEVEL_WARNING)
            return None
        
        gameId = selectedGame.getProperty('gameId')

        if(gameId == None):         
            Logutil.log("No Game Id Found", util.LOG_LEVEL_WARNING)
            return None
        
        Logutil.log("gameId = " + gameId, util.LOG_LEVEL_INFO)
        
        return gameId
        
        
    def loadGameInfos(self, gameRow, selectedGame, pos, romCollection, fileDict):
        Logutil.log("begin loadGameInfos", util.LOG_LEVEL_DEBUG)
        Logutil.log("gameRow = " +str(gameRow), util.LOG_LEVEL_DEBUG)
        
        if(self.getListSize() == 0):
            Logutil.log("ListSize == 0 in loadGameInfos", util.LOG_LEVEL_WARNING)
            return
        
        # > 1: cacheItem, cacheItemAndNext 
        if(self.cachingOption > 1):
            self.setAllItemData(selectedGame, gameRow, fileDict, romCollection)

        # > 2: cacheItemAndNext 
        if(self.cachingOption > 2):
            #prepare items before and after actual position     
            posBefore = pos - 1
            if(posBefore < 0):
                posBefore = self.getListSize() - 1
                            
            selectedGame, gameRow = self.getGameByPosition(self.gdb, posBefore)
            if(selectedGame == None or gameRow == None):
                return
            fileDict = self.getFileDictByGameRow(gameRow)
            self.setAllItemData(selectedGame, gameRow, fileDict, romCollection)
            
            posAfter = pos + 1
            if(posAfter >= self.getListSize()):
                posAfter = 0
                            
            selectedGame, gameRow = self.getGameByPosition(self.gdb, posAfter)
            if(selectedGame == None or gameRow == None):
                return
            fileDict = self.getFileDictByGameRow(gameRow)
            self.setAllItemData(selectedGame, gameRow, fileDict, romCollection)
            
        Logutil.log("end loadGameInfos", util.LOG_LEVEL_DEBUG)

    
    def getFileDictByGameRow(self, gameRow):                
        
        files = File(self.gdb).getFilesByParentIds(gameRow[util.ROW_ID], gameRow[util.GAME_romCollectionId], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId])
                
        fileDict = helper.cacheFiles(files)
        
        return fileDict
        
        
    def setAllItemData(self, item, gameRow, fileDict, romCollection):               
        
        # all other images in mainwindow
        imagemainViewBackground = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewBackground, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoBig = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoBig, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoUpperLeft = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoUpperLeft, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoUpperRight = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoUpperRight, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoLowerLeft = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoLowerLeft, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoLowerRight = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoLowerRight, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        
        imageGameInfoUpper = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoUpper, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoLower = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoLower, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoLeft = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoLeft, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageGameInfoRight = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainViewGameInfoRight, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        
        imageMainView1 = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainView1, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageMainView2 = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainView2, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)
        imageMainView3 = self.getFileForControl(romCollection.imagePlacingMain.fileTypesForMainView3, gameRow[util.ROW_ID], gameRow[util.GAME_publisherId], gameRow[util.GAME_developerId], gameRow[util.GAME_romCollectionId], fileDict)       
       
        print 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
        print imagemainViewBackground
        print imageGameInfoBig
        print imageGameInfoUpperLeft
        print imageGameInfoUpperRight
        print imageGameInfoLowerLeft
        print imageGameInfoLowerRight
        print imageGameInfoUpper, imageGameInfoLower, imageGameInfoLeft, imageGameInfoRight, imageMainView1, imageMainView2, imageMainView3
        #set images as properties for use in the skin
        #item.setProperty(util.IMAGE_CONTROL_BACKGROUND, '/home/media/ninja-parade.png')
        #item.setProperty(util.IMAGE_CONTROL_GAMEINFO_BIG, '/home/hedley/emulators/mame/artwork/boxfront/mk2.png')
        #item.setProperty(util.IMAGE_CONTROL_GAMEINFO_BIG, '/home/media/ninja-parade.png')

        imagemainViewBackground = u'/home/hedley/emulators/zsnes/artwork/boxfront/Super Adventure Island (US).jpg'
        item.setProperty(util.IMAGE_CONTROL_BACKGROUND, imagemainViewBackground)
        Logutil.log("BACKGROUND = %s" % imagemainViewBackground, util.LOG_LEVEL_INFO)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_BIG, imageGameInfoBig)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_UPPERLEFT, imageGameInfoUpperLeft)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_UPPERRIGHT, imageGameInfoUpperRight)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_LOWERLEFT, imageGameInfoLowerLeft)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_LOWERRIGHT, imageGameInfoLowerRight)       
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_UPPER, imageGameInfoUpper)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_LOWER, imageGameInfoLower)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_LEFT, imageGameInfoLeft)
        item.setProperty(util.IMAGE_CONTROL_GAMEINFO_RIGHT, imageGameInfoRight)
        item.setProperty(util.IMAGE_CONTROL_1, imageMainView1)
        item.setProperty(util.IMAGE_CONTROL_2, imageMainView2)
        item.setProperty(util.IMAGE_CONTROL_3, imageMainView3)
        
        
        #set additional properties
        description = gameRow[util.GAME_description]
        if(description == None):
            description = ""            
        item.setProperty('plot', description)
        
        try:            
            item.setProperty('romcollection', romCollection.name)           
            item.setProperty('console', romCollection.name)
        except:
            pass                                    
        
        item.setProperty('year', helper.getPropertyFromCache(gameRow, self.yearDict, util.GAME_yearId, util.ROW_NAME))
        item.setProperty('year', str(imagemainViewBackground.__class__))
        item.setProperty('publisher', helper.getPropertyFromCache(gameRow, self.publisherDict, util.GAME_publisherId, util.ROW_NAME))
        item.setProperty('developer', helper.getPropertyFromCache(gameRow, self.developerDict, util.GAME_developerId, util.ROW_NAME))
        item.setProperty('reviewer', helper.getPropertyFromCache(gameRow, self.reviewerDict, util.GAME_reviewerId, util.ROW_NAME))
        
        genre = ""          
        try:
            #0 = cacheAll: load all game data at once
            if(self.cachingOption == 0):
                genre = self.genreDict[gameRow[util.ROW_ID]]
            else:               
                genres = Genre(self.gdb).getGenresByGameId(gameRow[util.ROW_ID])
                if (genres != None):
                    for i in range(0, len(genres)):
                        genreRow = genres[i]
                        genre += genreRow[util.ROW_NAME]
                        if(i < len(genres) -1):
                            genre += ", "           
        except:             
            pass                            
        item.setProperty('genre', genre)
        
        item.setProperty('maxplayers', helper.saveReadString(gameRow[util.GAME_maxPlayers]))
        item.setProperty('rating', helper.saveReadString(gameRow[util.GAME_rating]))
        item.setProperty('votes', helper.saveReadString(gameRow[util.GAME_numVotes]))
        item.setProperty('url', helper.saveReadString(gameRow[util.GAME_url]))  
        item.setProperty('region', helper.saveReadString(gameRow[util.GAME_region]))
        item.setProperty('media', helper.saveReadString(gameRow[util.GAME_media]))              
        item.setProperty('perspective', helper.saveReadString(gameRow[util.GAME_perspective]))
        item.setProperty('controllertype', helper.saveReadString(gameRow[util.GAME_controllerType]))
        item.setProperty('originaltitle', helper.saveReadString(gameRow[util.GAME_originalTitle]))
        item.setProperty('alternatetitle', helper.saveReadString(gameRow[util.GAME_alternateTitle]))
        item.setProperty('translatedby', helper.saveReadString(gameRow[util.GAME_translatedBy]))
        item.setProperty('version', helper.saveReadString(gameRow[util.GAME_version]))
        
        item.setProperty('playcount', helper.saveReadString(gameRow[util.GAME_launchCount]))
        
        return item
    
    
    def checkImport(self, doImport, romCollections, isRescrape):
        
        #doImport: 0=nothing, 1=import Settings and Games, 2=import Settings only, 3=import games only
        if(doImport == 0):
            return
        
        #Show options dialog if user wants to see it
        #Import is started from dialog
        showImportOptionsDialog = self.Settings.getSetting(util.SETTING_RCB_SHOWIMPORTOPTIONSDIALOG).upper() == 'TRUE'
        if(showImportOptionsDialog):
            constructorParam = "720p"
            iod = dialogimportoptions.ImportOptionsDialog("script-RCB-importoptions.xml", util.getAddonInstallPath(), "Default", constructorParam, gui=self, romCollections=romCollections, isRescrape=isRescrape)
            del iod
        else:
            message = util.localize(40018)
        
            dialog = xbmcgui.Dialog()
            retGames = dialog.yesno(util.localize(30000), util.localize(51000), message)
            if(retGames == True):
                
                scrapingMode = util.getScrapingMode(self.Settings)
                #Import Games
                if(romCollections == None):
                    self.doImport(scrapingMode, self.config.romCollections, isRescrape)
                else:
                    self.doImport(scrapingMode, romCollections, isRescrape)
        
        
    def doImport(self, scrapingmode, romCollections, isRescrape):
        return
        progressDialog = dialogprogress.ProgressDialogGUI()
        progressDialog.writeMsg(util.localize(40011), "", "")
        
        updater = dbupdate.DBUpdate()
        updater.updateDB(self.gdb, progressDialog, scrapingmode, romCollections, self.Settings, isRescrape)
        del updater
        progressDialog.writeMsg("", "", "", -1)
        del progressDialog


    def checkUpdateInProgress(self):
        
        Logutil.log("checkUpdateInProgress" , util.LOG_LEVEL_INFO)
        
        scrapeOnStartupAction = self.Settings.getSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION)
        Logutil.log("scrapeOnStartupAction = " +str(scrapeOnStartupAction) , util.LOG_LEVEL_INFO)
        
        if (scrapeOnStartupAction == 'update'):
            retCancel = xbmcgui.Dialog().yesno(util.localize(30000), util.localize(40012), util.localize(40013))
            if(retCancel == True):
                self.Settings.setSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION, 'cancel')
            return True
        
        elif (scrapeOnStartupAction == 'cancel'):
            xbmcgui.Dialog().ok(util.localize(30000), util.localize(40014), util.localize(40015))
            
            #HACK: Assume that there is a problem with canceling the action
            #self.Settings.setSetting(util.SETTING_RCB_SCRAPEONSTARTUPACTION, 'nothing')
            
            return True
        
        return False


    # Handle autoexec.py script to add/remove background scraping on startup
    def checkScrapStart(self):
        Logutil.log("Begin checkScrapStart" , util.LOG_LEVEL_INFO)
        
        autoexecFile = util.getAutoexecPath()
        path = os.path.join(util.RCBHOME, 'dbUpLauncher.py')
        if(util.getEnvironment() == 'win32'):
            #HACK: There is an error with "\a" in autoexec.py on winidows, so we need "\A"
            path = path.replace('\\addons', '\\Addons')
        launchLine = 'xbmc.executescript("%s")' % path
        try:
            fp = open(autoexecFile, 'r+')
        except:
            Logutil.log("Error opening autoexec.py" , util.LOG_LEVEL_WARNING)
            return
        xbmcImported = False
        alreadyCreated = False
        for line in fp:
            if line.startswith('import xbmc'):
                Logutil.log("import xbmc line found!" , util.LOG_LEVEL_INFO)
                xbmcImported = True
            if launchLine in line:
                Logutil.log("executescript line found!", util.LOG_LEVEL_INFO)
                alreadyCreated = True
                
        if self.Settings.getSetting(util.SETTING_RCB_SCRAPONSTART) == 'true':
            
            if not xbmcImported:
                Logutil.log("adding import xbmc line", util.LOG_LEVEL_INFO)
                fp.write('\nimport xbmc')
            if not alreadyCreated:
                Logutil.log("adding executescript line", util.LOG_LEVEL_INFO)
                fp.write('\n' + launchLine)
                
            fp.close()
        elif alreadyCreated:
            Logutil.log("Deleting executescript line" , util.LOG_LEVEL_INFO)
            if alreadyCreated:
                fp.seek(0)
                lines = fp.readlines()
                fp.close()
                os.remove(autoexecFile)
                fp = open(autoexecFile, 'w')
                for line in lines:
                    if not path in line:
                        fp.write(line)
                fp.close()
        Logutil.log("End checkScrapStart" , util.LOG_LEVEL_INFO)
                
                
    def checkAutoExec(self):
        Logutil.log("Begin checkAutoExec" , util.LOG_LEVEL_INFO)
        
        autoexec = util.getAutoexecPath()       
        Logutil.log("Checking path: " + autoexec, util.LOG_LEVEL_INFO)
        if (os.path.isfile(autoexec)):  
            lines = ""
            try:
                fh = fh = open(autoexec, "r")
                lines = fh.readlines()
                fh.close()
            except Exception, (exc):
                Logutil.log("Cannot access autoexec.py: " + str(exc), util.LOG_LEVEL_ERROR)
                return
                
            if(len(lines) > 0):
                firstLine = lines[0]
                #check if it is our autoexec
                if(firstLine.startswith('#Rom Collection Browser autoexec')):
                    try:
                        os.remove(autoexec)
                    except Exception, (exc):
                        Logutil.log("Cannot remove autoexec.py: " + str(exc), util.LOG_LEVEL_ERROR)
                        return
                else:
                    return
        else:
            Logutil.log("No autoexec.py found at given path.", util.LOG_LEVEL_INFO)
        
        rcbSetting = helper.getRCBSetting(self.gdb)
        if (rcbSetting == None):
            print "RCB_WARNING: rcbSetting == None in checkAutoExec"
            return
                    
        #check if we have to restore autoexec backup 
        autoExecBackupPath = rcbSetting[util.RCBSETTING_autoexecBackupPath]
        if (autoExecBackupPath == None):
            return
            
        if (os.path.isfile(autoExecBackupPath)):
            try:
                os.rename(autoExecBackupPath, autoexec)
                os.remove(autoExecBackupPath)
            except Exception, (exc):
                Logutil.log("Cannot rename autoexec.py: " + str(exc), util.LOG_LEVEL_ERROR)
                return
            
        RCBSetting(self.gdb).update(('autoexecBackupPath',), (None,), rcbSetting[0], True)
        self.gdb.commit()
        
        Logutil.log("End checkAutoExec" , util.LOG_LEVEL_INFO)      
        
        
    def backupConfigXml(self):
        #backup config.xml for later use (will be overwritten in case of an addon update)
        configXml = util.getConfigXmlPath()
        configXmlBackup = os.path.join(util.getAddonDataPath(), 'config.xml.backup')
        
        if os.path.isfile(configXmlBackup):
            try:
                os.remove(configXmlBackup)
            except Exception, (exc):
                Logutil.log("Cannot remove config.xml backup: " +str(exc), util.LOG_LEVEL_ERROR)
                return
        
        try:
            shutil.copy(configXml, configXmlBackup)
        except Exception, (exc):
            Logutil.log("Cannot backup config.xml: " +str(exc), util.LOG_LEVEL_ERROR)
            return
        
    def cacheItems(self):       
        Logutil.log("Begin cacheItems" , util.LOG_LEVEL_INFO)
        
        #cacheAll
        if(self.cachingOption == 0):
            fileRows = File(self.gdb).getAll()
            if(fileRows == None):
                Logutil.log("fileRows == None in cacheItems", util.LOG_LEVEL_WARNING)
                return
            self.fileDict = helper.cacheFiles(fileRows)
        
        self.yearDict = helper.cacheYears(self.gdb)
        
        self.publisherDict = helper.cachePublishers(self.gdb)
        
        self.developerDict = helper.cacheDevelopers(self.gdb)
        
        self.reviewerDict = helper.cacheReviewers(self.gdb)
        
        #0 = cacheAll: load all game data at once
        if(self.cachingOption == 0):
            self.genreDict = helper.cacheGenres(self.gdb)
        else:
            self.genreDict = None
        
        Logutil.log("End cacheItems" , util.LOG_LEVEL_INFO)
        
        
    def clearCache(self):
        Logutil.log("Begin clearCache" , util.LOG_LEVEL_INFO)
                
        self.fileDict = None        
        self.yearDict = None
        self.publisherDict = None
        self.developerDict = None
        self.reviewerDict = None
        self.genreDict = None
        
        Logutil.log("End clearCache" , util.LOG_LEVEL_INFO)
        
        
    
    
    
    def getControlById(self, controlId):
        try:
            control = self.getControl(controlId)
        except Exception, (exc):
            #HACK there seems to be a problem with recognizing the scrollbar controls
            if(controlId not in (CONTROL_SCROLLBARS)):
                Logutil.log("Control with id: %s could not be found. Check WindowXML file. Error: %s" % (str(controlId), str(exc)), util.LOG_LEVEL_ERROR)
                self.writeMsg(util.localize(35025) % str(controlId))
            return None
        
        return control
    
    
    def writeMsg(self, msg, count=0):
        
        control = self.getControlById(CONTROL_LABEL_MSG)
        if(control == None):
            Logutil.log("RCB_WARNING: control == None in writeMsg", util.LOG_LEVEL_WARNING)
            return
        try:
            control.setLabel(msg)
        except:
            pass
    
    
    def exit(self):             
        
        Logutil.log("exit" , util.LOG_LEVEL_INFO)
                    
        
        """
        if self.memDB:
            Logutil.log("Saving DB to disk", util.LOG_LEVEL_INFO)
            if self.gdb.toDisk():
                Logutil.log("Database saved ok!", util.LOG_LEVEL_INFO)
            else:
                Logutil.log("Failed to save database!", util.LOG_LEVEL_INFO)
        """
                
        self.gdb.close()
        self.close()
        


def main():
    
    settings = util.getSettings()
    skin = settings.getSetting(util.SETTING_RCB_SKIN)
    if(skin == "Confluence"):
        skin = "Default"
    
    ui = UIGameDB("script-Rom_Collection_Browser-main.xml", util.getAddonInstallPath(), skin, "720p")
    ui.doModal()
    del ui

main()
