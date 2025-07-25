# pacman.py
# ---------
# Licensing Information:  You are free to use or extend these projects for
# educational purposes provided that (1) you do not distribute or publish
# solutions, (2) you retain this notice, and (3) you provide clear
# attribution to UC Berkeley, including a link to http://ai.berkeley.edu.
#
# Attribution Information: The Pacman AI projects were developed at UC Berkeley.
# The core projects and autograders were primarily created by John DeNero
# (denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
# Student side autograding was added by Brad Miller, Nick Hay, and
# Pieter Abbeel (pabbeel@cs.berkeley.edu).


"""Main module for the Pacman game implementation.

This module contains the core game logic and framework for the classic Pacman arcade game.
The implementation is organized into three main sections:

1. Pacman World Interface:
   - Contains the GameState class and related functionality
   - Provides the primary interface for agents to interact with the game
   - Includes key methods for legal moves, state transitions, and scoring
   - Works in conjunction with game.py for core mechanics

2. Game Logic Implementation:
   - Internal game rules and mechanics
   - Collision detection and movement validation
   - Ghost behavior and interactions
   - Power pellet and scoring logic

3. Game Framework:
   - Command-line argument parsing and game configuration
   - Graphics and display management
   - Agent loading and initialization
   - Main game loop and control flow

Usage:
    Run 'python pacman.py' to start a game with default settings
    Use WASD or arrow keys for movement
    See README for additional command line options

Changes by George Rudolph 30 Nov 2024:
- Verified compatibility with Python 3.13
- Improved module documentation structure
- Added section descriptions and usage details
- Enhanced code organization documentation
- Standardized docstring formatting
"""
from game import GameStateData
from game import Game
from game import Directions
from game import Actions
from util import nearestPoint
from util import manhattanDistance
import util, layout
import sys, types, time, random, os

###################################################
# YOUR INTERFACE TO THE PACMAN WORLD: A GameState #
###################################################


class GameState:
    """
    A GameState specifies the full game state, including the food, capsules,
    agent configurations and score changes.

    GameStates are used by the Game object to capture the actual state of the game and
    can be used by agents to reason about the game.

    Much of the information in a GameState is stored in a GameStateData object. We
    strongly suggest that you access that data via the accessor methods below rather
    than referring to the GameStateData object directly.

    Note that in classic Pacman, Pacman is always agent 0.
    """

    ####################################################
    # Accessor methods: use these to access state data #
    ####################################################

    # static variable keeps track of which states have had getLegalActions called
    explored = set()

    @staticmethod
    def getAndResetExplored() -> set:
        """Returns and resets the set of states that have been explored."""
        tmp = GameState.explored.copy()
        GameState.explored = set()
        return tmp

    def getLegalActions(self, agentIndex: int = 0) -> list:
        """
        Returns the legal actions for the agent specified.
        
        Args:
            agentIndex: Index of the agent (0 for Pacman, 1+ for ghosts)
            
        Returns:
            List of legal actions the agent can take
        """
        #        GameState.explored.add(self)
        if self.isWin() or self.isLose():
            return []

        if agentIndex == 0:  # Pacman is moving
            return PacmanRules.getLegalActions(self)
        else:
            return GhostRules.getLegalActions(self, agentIndex)

    def generateSuccessor(self, agentIndex: int, action) -> 'GameState':
        """
        Returns the successor state after the specified agent takes the action.
        
        Args:
            agentIndex: Index of the agent taking the action
            action: The action being taken
            
        Returns:
            The successor GameState after the action
            
        Raises:
            Exception if trying to generate successor of a terminal state
        """
        # Check that successors exist
        if self.isWin() or self.isLose():
            raise Exception("Can't generate a successor of a terminal state.")

        # Copy current state
        state = GameState(self)

        # Let agent's logic deal with its action's effects on the board
        if agentIndex == 0:  # Pacman is moving
            state.data._eaten = [False for i in range(state.getNumAgents())]
            PacmanRules.applyAction(state, action)
        else:  # A ghost is moving
            GhostRules.applyAction(state, action, agentIndex)

        # Time passes
        if agentIndex == 0:
            state.data.scoreChange += -TIME_PENALTY  # Penalty for waiting around
        else:
            GhostRules.decrementTimer(state.data.agentStates[agentIndex])

        # Resolve multi-agent effects
        GhostRules.checkDeath(state, agentIndex)

        # Book keeping
        state.data._agentMoved = agentIndex
        state.data.score += state.data.scoreChange
        GameState.explored.add(self)
        GameState.explored.add(state)
        return state

    def getLegalPacmanActions(self) -> list:
        """Returns list of legal actions for Pacman (agent 0)"""
        return self.getLegalActions(0)

    def generatePacmanSuccessor(self, action) -> 'GameState':
        """
        Generates the successor state after the specified pacman move
        
        Args:
            action: The action being taken by Pacman
            
        Returns:
            The successor GameState after Pacman's action
        """
        return self.generateSuccessor(0, action)

    def getPacmanState(self):
        """
        Returns an AgentState object for pacman (in game.py)

        state.pos gives the current position
        state.direction gives the travel vector
        """
        return self.data.agentStates[0].copy()

    def getPacmanPosition(self) -> tuple:
        """Returns the coordinates of Pacman's position"""
        return self.data.agentStates[0].getPosition()

    def getGhostStates(self) -> list:
        """Returns list of AgentState objects for all ghosts"""
        return self.data.agentStates[1:]

    def getGhostState(self, agentIndex: int):
        """
        Returns the AgentState object for a specific ghost
        
        Args:
            agentIndex: Index of the ghost (must be >= 1)
            
        Raises:
            Exception if invalid ghost index
        """
        if agentIndex == 0 or agentIndex >= self.getNumAgents():
            raise Exception("Invalid index passed to getGhostState")
        return self.data.agentStates[agentIndex]

    def getGhostPosition(self, agentIndex: int) -> tuple:
        """
        Returns the coordinates of a specific ghost's position
        
        Args:
            agentIndex: Index of the ghost (must be >= 1)
            
        Raises:
            Exception if trying to get Pacman's position
        """
        if agentIndex == 0:
            raise Exception("Pacman's index passed to getGhostPosition")
        return self.data.agentStates[agentIndex].getPosition()

    def getGhostPositions(self) -> list:
        """Returns list of coordinates for all ghost positions"""
        return [s.getPosition() for s in self.getGhostStates()]

    def getNumAgents(self) -> int:
        """Returns total number of agents (Pacman + ghosts)"""
        return len(self.data.agentStates)

    def getScore(self) -> float:
        """Returns current game score"""
        return float(self.data.score)

    def getCapsules(self) -> list:
        """
        Returns a list of positions (x,y) of the remaining capsules.
        """
        return self.data.capsules

    def getNumFood(self) -> int:
        """Returns number of food pellets remaining"""
        return self.data.food.count()

    def getFood(self):
        """
        Returns a Grid of boolean food indicator variables.

        Grids can be accessed via list notation, so to check
        if there is food at (x,y), just call

        currentFood = state.getFood()
        if currentFood[x][y] == True: ...
        """
        return self.data.food

    def getWalls(self):
        """
        Returns a Grid of boolean wall indicator variables.

        Grids can be accessed via list notation, so to check
        if there is a wall at (x,y), just call

        walls = state.getWalls()
        if walls[x][y] == True: ...
        """
        return self.data.layout.walls

    def hasFood(self, x: int, y: int) -> bool:
        """Returns whether there is food at coordinates (x,y)"""
        return self.data.food[x][y]

    def hasWall(self, x: int, y: int) -> bool:
        """Returns whether there is a wall at coordinates (x,y)"""
        return self.data.layout.walls[x][y]

    def isLose(self) -> bool:
        """Returns whether this state is a loss state"""
        return self.data._lose

    def isWin(self) -> bool:
        """Returns whether this state is a win state"""
        return self.data._win

    #############################################
    #             Helper methods:               #
    # You shouldn't need to call these directly #
    #############################################

    def __init__(self, prevState = None):
        """
        Generates a new state by copying information from its predecessor.
        
        Args:
            prevState: Previous GameState to copy from, or None for initial state
        """
        if prevState != None:  # Initial state
            self.data = GameStateData(prevState.data)
        else:
            self.data = GameStateData()

    def deepCopy(self) -> 'GameState':
        """Returns a deep copy of this GameState"""
        state = GameState(self)
        state.data = self.data.deepCopy()
        return state

    def __eq__(self, other) -> bool:
        """
        Allows two states to be compared.
        """
        return hasattr(other, "data") and self.data == other.data

    def __hash__(self) -> int:
        """
        Allows states to be keys of dictionaries.
        """
        return hash(self.data)

    def __str__(self) -> str:
        """Returns string representation of the state"""
        return str(self.data)

    def initialize(self, layout, numGhostAgents: int = 1000) -> None:
        """
        Creates an initial game state from a layout array (see layout.py).
        
        Args:
            layout: The layout to initialize the game with
            numGhostAgents: Maximum number of ghost agents to use
        """
        self.data.initialize(layout, numGhostAgents)


############################################################################
#                     THE HIDDEN SECRETS OF PACMAN                         #
#                                                                          #
# You shouldn't need to look through the code in this section of the file. #
############################################################################

SCARED_TIME = 40  # Moves ghosts are scared
COLLISION_TOLERANCE = 0.7  # How close ghosts must be to Pacman to kill
TIME_PENALTY = 1  # Number of points lost each round


class ClassicGameRules:
    """
    These game rules manage the control flow of a game, deciding when
    and how the game starts and ends.
    """

    def __init__(self, timeout: int = 30):
        self.timeout = timeout

    def newGame(
        self,
        layout,
        pacmanAgent,
        ghostAgents,
        display,
        quiet: bool = False,
        catchExceptions: bool = False,
    ) -> Game:
        """
        Creates and returns a new game.
        
        Args:
            layout: The game layout
            pacmanAgent: The Pacman agent
            ghostAgents: List of ghost agents
            display: The game display
            quiet: Whether to suppress output
            catchExceptions: Whether to catch exceptions during game execution
            
        Returns:
            A new Game object
        """
        agents = [pacmanAgent] + ghostAgents[: layout.getNumGhosts()]
        initState = GameState()
        initState.initialize(layout, len(ghostAgents))
        game = Game(agents, display, self, catchExceptions=catchExceptions)
        game.state = initState
        self.initialState = initState.deepCopy()
        self.quiet = quiet
        return game

    def process(self, state: GameState, game: Game) -> None:
        """
        Checks to see whether it is time to end the game.
        
        Args:
            state: Current game state
            game: The game object
        """
        if state.isWin():
            self.win(state, game)
        if state.isLose():
            self.lose(state, game)

    def win(self, state: GameState, game: Game) -> None:
        """Called when the game is won"""
        if not self.quiet:
            print(f"Pacman emerges victorious! Score: {state.data.score}")
        game.gameOver = True

    def lose(self, state: GameState, game: Game) -> None:
        """Called when the game is lost"""
        if not self.quiet:
            print(f"Pacman died! Score: {state.data.score}")
        game.gameOver = True

    def getProgress(self, game: Game) -> float:
        """Returns ratio of food remaining"""
        return float(game.state.getNumFood()) / self.initialState.getNumFood()

    def agentCrash(self, game: Game, agentIndex: int) -> None:
        """Called when an agent crashes"""
        if agentIndex == 0:
            print("Pacman crashed")
        else:
            print("A ghost crashed")

    def getMaxTotalTime(self, agentIndex: int) -> int:
        """Returns maximum time allowed"""
        return self.timeout

    def getMaxStartupTime(self, agentIndex: int) -> int:
        """Returns maximum startup time allowed"""
        return self.timeout

    def getMoveWarningTime(self, agentIndex: int) -> int:
        """Returns time to warn about slow moves"""
        return self.timeout

    def getMoveTimeout(self, agentIndex: int) -> int:
        """Returns timeout for moves"""
        return self.timeout

    def getMaxTimeWarnings(self, agentIndex: int) -> int:
        """Returns maximum number of time warnings allowed"""
        return 0


class PacmanRules:
    """
    These functions govern how pacman interacts with his environment under
    the classic game rules.
    """

    PACMAN_SPEED = 1

    @staticmethod
    def getLegalActions(state: GameState) -> list:
        """
        Returns a list of possible actions.
        
        Args:
            state: Current game state
            
        Returns:
            List of legal actions Pacman can take
        """
        return Actions.getPossibleActions(
            state.getPacmanState().configuration, state.data.layout.walls
        )

    @staticmethod
    def applyAction(state: GameState, action) -> None:
        """
        Edits the state to reflect the results of the action.
        
        Args:
            state: Current game state
            action: Action being taken
            
        Raises:
            Exception if action is illegal
        """
        legal = PacmanRules.getLegalActions(state)
        if action not in legal:
            raise Exception(f"Illegal action {action}")

        pacmanState = state.data.agentStates[0]

        # Update Configuration
        vector = Actions.directionToVector(action, PacmanRules.PACMAN_SPEED)
        pacmanState.configuration = pacmanState.configuration.generateSuccessor(vector)

        # Eat
        next = pacmanState.configuration.getPosition()
        nearest = nearestPoint(next)
        if manhattanDistance(nearest, next) <= 0.5:
            # Remove food
            PacmanRules.consume(nearest, state)

    @staticmethod
    def consume(position: tuple, state: GameState) -> None:
        """
        Handles Pacman consuming food/capsules at a position
        
        Args:
            position: (x,y) coordinates of consumption
            state: Current game state
        """
        x, y = position
        # Eat food
        if state.data.food[x][y]:
            state.data.scoreChange += 10
            state.data.food = state.data.food.copy()
            state.data.food[x][y] = False
            state.data._foodEaten = position
            # TODO: cache numFood?
            numFood = state.getNumFood()
            if numFood == 0 and not state.data._lose:
                state.data.scoreChange += 500
                state.data._win = True
        # Eat capsule
        if position in state.getCapsules():
            state.data.capsules.remove(position)
            state.data._capsuleEaten = position
            # Reset all ghosts' scared timers
            for index in range(1, len(state.data.agentStates)):
                state.data.agentStates[index].scaredTimer = SCARED_TIME


class GhostRules:
    """
    These functions dictate how ghosts interact with their environment.
    """

    GHOST_SPEED = 1.0

    @staticmethod
    def getLegalActions(state: GameState, ghostIndex: int) -> list:
        """
        Ghosts cannot stop, and cannot turn around unless they
        reach a dead end, but can turn 90 degrees at intersections.
        
        Args:
            state: Current game state
            ghostIndex: Index of ghost
            
        Returns:
            List of legal actions for the ghost
        """
        conf = state.getGhostState(ghostIndex).configuration
        possibleActions = Actions.getPossibleActions(conf, state.data.layout.walls)
        reverse = Actions.reverseDirection(conf.direction)
        if Directions.STOP in possibleActions:
            possibleActions.remove(Directions.STOP)
        if reverse in possibleActions and len(possibleActions) > 1:
            possibleActions.remove(reverse)
        return possibleActions

    @staticmethod
    def applyAction(state: GameState, action, ghostIndex: int) -> None:
        """
        Applies ghost action to the game state
        
        Args:
            state: Current game state  
            action: Action being taken
            ghostIndex: Index of ghost taking action
            
        Raises:
            Exception if action is illegal
        """
        legal = GhostRules.getLegalActions(state, ghostIndex)
        if action not in legal:
            raise Exception(f"Illegal ghost action {action}")

        ghostState = state.data.agentStates[ghostIndex]
        speed = GhostRules.GHOST_SPEED
        if ghostState.scaredTimer > 0:
            speed /= 2.0
        vector = Actions.directionToVector(action, speed)
        ghostState.configuration = ghostState.configuration.generateSuccessor(vector)

    @staticmethod
    def decrementTimer(ghostState) -> None:
        """Decrements ghost's scared timer"""
        timer = ghostState.scaredTimer
        if timer == 1:
            ghostState.configuration.pos = nearestPoint(ghostState.configuration.pos)
        ghostState.scaredTimer = max(0, timer - 1)

    @staticmethod
    def checkDeath(state: GameState, agentIndex: int) -> None:
        """
        Checks if Pacman and ghost collide, handles scoring
        
        Args:
            state: Current game state
            agentIndex: Index of agent that just moved
        """
        pacmanPosition = state.getPacmanPosition()
        if agentIndex == 0:  # Pacman just moved; Anyone can kill him
            for index in range(1, len(state.data.agentStates)):
                ghostState = state.data.agentStates[index]
                ghostPosition = ghostState.configuration.getPosition()
                if GhostRules.canKill(pacmanPosition, ghostPosition):
                    GhostRules.collide(state, ghostState, index)
        else:
            ghostState = state.data.agentStates[agentIndex]
            ghostPosition = ghostState.configuration.getPosition()
            if GhostRules.canKill(pacmanPosition, ghostPosition):
                GhostRules.collide(state, ghostState, agentIndex)

    @staticmethod
    def collide(state: GameState, ghostState, agentIndex: int) -> None:
        """
        Handles collision between Pacman and ghost
        
        Args:
            state: Current game state
            ghostState: State of ghost involved in collision
            agentIndex: Index of ghost
        """
        if ghostState.scaredTimer > 0:
            state.data.scoreChange += 200
            GhostRules.placeGhost(state, ghostState)
            ghostState.scaredTimer = 0
            # Added for first-person
            state.data._eaten[agentIndex] = True
        else:
            if not state.data._win:
                state.data.scoreChange -= 500
                state.data._lose = True

    @staticmethod
    def canKill(pacmanPosition: tuple, ghostPosition: tuple) -> bool:
        """Returns True if Pacman and ghost are close enough to collide"""
        return manhattanDistance(ghostPosition, pacmanPosition) <= COLLISION_TOLERANCE

    @staticmethod
    def placeGhost(state: GameState, ghostState) -> None:
        """Places ghost back at its starting position"""
        ghostState.configuration = ghostState.start


#############################
# FRAMEWORK TO START A GAME #
#############################


def default(str: str) -> str:
    """Adds default value to option string"""
    return f"{str} [Default: %default]"


def parseAgentArgs(str: str) -> dict:
    """
    Parses agent arguments from string
    
    Args:
        str: String of comma-separated arguments
        
    Returns:
        Dictionary of argument key-value pairs
    """
    if str == None:
        return {}
    pieces = str.split(",")
    opts = {}
    for p in pieces:
        if "=" in p:
            key, val = p.split("=")
        else:
            key, val = p, 1
        opts[key] = val
    return opts


def readCommand(argv: list) -> dict:
    """
    Processes the command used to run pacman from the command line.
    
    Args:
        argv: List of command line arguments
        
    Returns:
        Dictionary of game settings/components
        
    Raises:
        Exception if command line input not understood
    """
    from optparse import OptionParser

    usageStr = """
    USAGE:      python pacman.py <options>
    EXAMPLES:   (1) python pacman.py
                    - starts an interactive game
                (2) python pacman.py --layout smallClassic --zoom 2
                OR  python pacman.py -l smallClassic -z 2
                    - starts an interactive game on a smaller board, zoomed in
    """
    parser = OptionParser(usageStr)

    parser.add_option(
        "-n",
        "--numGames",
        dest="numGames",
        type="int",
        help=default("the number of GAMES to play"),
        metavar="GAMES",
        default=1,
    )
    parser.add_option(
        "-l",
        "--layout",
        dest="layout",
        help=default("the LAYOUT_FILE from which to load the map layout"),
        metavar="LAYOUT_FILE",
        default="mediumClassic",
    )
    parser.add_option(
        "-p",
        "--pacman",
        dest="pacman",
        help=default("the agent TYPE in the pacmanAgents module to use"),
        metavar="TYPE",
        default="KeyboardAgent",
    )
    parser.add_option(
        "-t",
        "--textGraphics",
        action="store_true",
        dest="textGraphics",
        help="Display output as text only",
        default=False,
    )
    parser.add_option(
        "-q",
        "--quietTextGraphics",
        action="store_true",
        dest="quietGraphics",
        help="Generate minimal output and no graphics",
        default=False,
    )
    parser.add_option(
        "-g",
        "--ghosts",
        dest="ghost",
        help=default("the ghost agent TYPE in the ghostAgents module to use"),
        metavar="TYPE",
        default="RandomGhost",
    )
    parser.add_option(
        "-k",
        "--numghosts",
        type="int",
        dest="numGhosts",
        help=default("The maximum number of ghosts to use"),
        default=4,
    )
    parser.add_option(
        "-z",
        "--zoom",
        type="float",
        dest="zoom",
        help=default("Zoom the size of the graphics window"),
        default=1.0,
    )
    parser.add_option(
        "-f",
        "--fixRandomSeed",
        action="store_true",
        dest="fixRandomSeed",
        help="Fixes the random seed to always play the same game",
        default=False,
    )
    parser.add_option(
        "-r",
        "--recordActions",
        action="store_true",
        dest="record",
        help="Writes game histories to a file (named by the time they were played)",
        default=False,
    )
    parser.add_option(
        "--replay",
        dest="gameToReplay",
        help="A recorded game file (pickle) to replay",
        default=None,
    )
    parser.add_option(
        "-a",
        "--agentArgs",
        dest="agentArgs",
        help='Comma separated values sent to agent. e.g. "opt1=val1,opt2,opt3=val3"',
    )
    parser.add_option(
        "-x",
        "--numTraining",
        dest="numTraining",
        type="int",
        help=default("How many episodes are training (suppresses output)"),
        default=0,
    )
    parser.add_option(
        "--frameTime",
        dest="frameTime",
        type="float",
        help=default("Time to delay between frames; <0 means keyboard"),
        default=0.1,
    )
    parser.add_option(
        "-c",
        "--catchExceptions",
        action="store_true",
        dest="catchExceptions",
        help="Turns on exception handling and timeouts during games",
        default=False,
    )
    parser.add_option(
        "--timeout",
        dest="timeout",
        type="int",
        help=default(
            "Maximum length of time an agent can spend computing in a single game"
        ),
        default=30,
    )

    options, otherjunk = parser.parse_args(argv)
    if len(otherjunk) != 0:
        raise Exception(f"Command line input not understood: {otherjunk}")
    args = dict()

    # Fix the random seed
    if options.fixRandomSeed:
        random.seed("cs188")

    # Choose a layout
    args["layout"] = layout.getLayout(options.layout)
    if args["layout"] == None:
        raise Exception(f"The layout {options.layout} cannot be found")

    # Choose a Pacman agent
    noKeyboard = options.gameToReplay == None and (
        options.textGraphics or options.quietGraphics
    )
    pacmanType = loadAgent(options.pacman, noKeyboard)
    agentOpts = parseAgentArgs(options.agentArgs)
    if options.numTraining > 0:
        args["numTraining"] = options.numTraining
        if "numTraining" not in agentOpts:
            agentOpts["numTraining"] = options.numTraining
    pacman = pacmanType(**agentOpts)  # Instantiate Pacman with agentArgs
    args["pacman"] = pacman

    # Don't display training games
    if "numTrain" in agentOpts:
        options.numQuiet = int(agentOpts["numTrain"])
        options.numIgnore = int(agentOpts["numTrain"])

    # Choose a ghost agent
    ghostType = loadAgent(options.ghost, noKeyboard)
    args["ghosts"] = [ghostType(i + 1) for i in range(options.numGhosts)]

    # Choose a display format
    if options.quietGraphics:
        import textDisplay

        args["display"] = textDisplay.NullGraphics()
    elif options.textGraphics:
        import textDisplay

        textDisplay.SLEEP_TIME = options.frameTime
        args["display"] = textDisplay.PacmanGraphics()
    else:
        import graphicsDisplay

        args["display"] = graphicsDisplay.PacmanGraphics(
            options.zoom, frameTime=options.frameTime
        )
    args["numGames"] = options.numGames
    args["record"] = options.record
    args["catchExceptions"] = options.catchExceptions
    args["timeout"] = options.timeout

    # Special case: recorded games don't use the runGames method or args structure
    if options.gameToReplay != None:
        print(f"Replaying recorded game {options.gameToReplay}.")
        import pickle

        f = open(options.gameToReplay)
        try:
            recorded = pickle.load(f)
        finally:
            f.close()
        recorded["display"] = args["display"]
        replayGame(**recorded)
        sys.exit(0)

    return args


def loadAgent(pacman: str, nographics: bool):
    """
    Looks through all pythonPath Directories for the right module
    
    Args:
        pacman: Name of agent to load
        nographics: Whether graphics are disabled
        
    Returns:
        The agent class
        
    Raises:
        Exception if agent cannot be found or loaded
    """
    # Looks through all pythonPath Directories for the right module,
    pythonPathStr = os.path.expandvars("$PYTHONPATH")
    if pythonPathStr.find(";") == -1:
        pythonPathDirs = pythonPathStr.split(":")
    else:
        pythonPathDirs = pythonPathStr.split(";")
    pythonPathDirs.append(".")

    for moduleDir in pythonPathDirs:
        if not os.path.isdir(moduleDir):
            continue
        moduleNames = [f for f in os.listdir(moduleDir) if f.endswith("gents.py")]
        for modulename in moduleNames:
            try:
                module = __import__(modulename[:-3])
            except ImportError:
                continue
            if pacman in dir(module):
                if nographics and modulename == "keyboardAgents.py":
                    raise Exception(
                        "Using the keyboard requires graphics (not text display)"
                    )
                return getattr(module, pacman)
    raise Exception("The agent " + pacman + " is not specified in any *Agents.py.")


def replayGame(layout, actions, display):
    """Replay a recorded game from a sequence of actions.
    
    Args:
        layout: The game layout to use
        actions: List of actions taken in the recorded game
        display: The display class to use for visualization
        
    Side effects:
        Replays the game visually using the provided display
    """
    import pacmanAgents, ghostAgents

    rules = ClassicGameRules()
    agents = [pacmanAgents.GreedyAgent()] + [
        ghostAgents.RandomGhost(i + 1) for i in range(layout.getNumGhosts())
    ]
    game = rules.newGame(layout, agents[0], agents[1:], display)
    state = game.state
    display.initialize(state.data)

    for action in actions:
        # Execute the action
        state = state.generateSuccessor(*action)
        # Change the display
        display.update(state.data)
        # Allow for game specific conditions (winning, losing, etc.)
        rules.process(state, game)

    display.finish()


def runGames(
    layout,
    pacman,
    ghosts,
    display,
    numGames,
    record,
    numTraining=0,
    catchExceptions=False,
    timeout=30,
):
    """Run multiple games with the given configuration.
    
    Args:
        layout: The game layout to use
        pacman: The Pacman agent to use
        ghosts: List of ghost agents to use
        display: The display class for visualization
        numGames: Number of games to run
        record: Whether to record the games
        numTraining: Number of training games (no output)
        catchExceptions: Whether to catch exceptions during gameplay
        timeout: Time limit for each move in seconds
        
    Returns:
        List of completed game instances
        
    Side effects:
        - Prints game statistics after completion
        - Records games to files if record=True
    """
    import __main__

    __main__.__dict__["_display"] = display

    rules = ClassicGameRules(timeout)
    games = []

    for i in range(numGames):
        beQuiet = i < numTraining
        if beQuiet:
            # Suppress output and graphics
            import textDisplay

            gameDisplay = textDisplay.NullGraphics()
            rules.quiet = True
        else:
            gameDisplay = display
            rules.quiet = False
        game = rules.newGame(
            layout, pacman, ghosts, gameDisplay, beQuiet, catchExceptions
        )
        game.run()
        if not beQuiet:
            games.append(game)

        if record:
            import time, pickle

            fname = ("recorded-game-%d" % (i + 1)) + "-".join(
                [str(t) for t in time.localtime()[1:6]]
            )
            f = open(fname, "w")
            components = {"layout": layout, "actions": game.moveHistory}
            pickle.dump(components, f)
            f.close()

    if (numGames - numTraining) > 0:
        scores = [game.state.getScore() for game in games]
        wins = [game.state.isWin() for game in games]
        winRate = wins.count(True) / float(len(wins))
        print("Average Score:", sum(scores) / float(len(scores)))
        print("Scores:       ", ", ".join([str(score) for score in scores]))
        print("Win Rate:      %d/%d (%.2f)" % (wins.count(True), len(wins), winRate))
        print("Record:       ", ", ".join([["Loss", "Win"][int(w)] for w in wins]))

    return games


if __name__ == "__main__":
    """
    The main function called when pacman.py is run
    from the command line:

    > python pacman.py

    See the usage string for more details.

    > python pacman.py --help
    """
    args = readCommand(sys.argv[1:])  # Get game components based on input
    runGames(**args)

    # import cProfile
    # cProfile.run("runGames( **args )")
    pass
