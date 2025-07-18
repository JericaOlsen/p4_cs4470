"""
game.py
-------
This module provides core game mechanics and infrastructure for the Pacman AI projects.
It defines base classes and utilities for implementing game agents, states, rules
and other fundamental components used across different Pacman game variants.

Key components:
- Agent: Base class for all game agents (Pacman, ghosts)
- Directions: Constants and utilities for movement directions
- Game: Core game loop and controller
- GameState: Abstract representation of game state
- GameStateData: Concrete game state implementation

Licensing Information:  You are free to use or extend these projects for
educational purposes provided that (1) you do not distribute or publish
solutions, (2) you retain this notice, and (3) you provide clear
attribution to UC Berkeley, including a link to http://ai.berkeley.edu.

Attribution Information: The Pacman AI projects were developed at UC Berkeley.
The core projects and autograders were primarily created by John DeNero
(denero@cs.berkeley.edu) and Dan Klein (klein@cs.berkeley.edu).
Student side autograding was added by Brad Miller, Nick Hay, and
Pieter Abbeel (pabbeel@cs.berkeley.edu).

Modified 19 Dec 2024 by George Rudolph:
- Verified compatibility with Python 3.13
- Added comprehensive module docstring
- Improved code organization and documentation
- Enhanced type hints and error handling
"""

from util import *
import time, os
import traceback
import sys
from typing import List, Tuple, Dict, Optional, Any, Union, IO

#######################
# Parts worth reading #
#######################


class Agent:
    """
    An agent must define a getAction method, but may also define the
    following methods which will be called if they exist:

    def registerInitialState(self, state): # inspects the starting state
    """

    def __init__(self, index: int = 0) -> None:
        self.index = index

    def getAction(self, state: Any) -> str:
        """
        The Agent will receive a GameState (from either {pacman, capture, sonar}.py) and
        must return an action from Directions.{North, South, East, West, Stop}
        
        Args:
            state: The current game state
            
        Returns:
            str: The action to take
        """
        raiseNotDefined()


class Directions:
    NORTH = "North"
    SOUTH = "South" 
    EAST = "East"
    WEST = "West"
    STOP = "Stop"

    LEFT = {NORTH: WEST, SOUTH: EAST, EAST: NORTH, WEST: SOUTH, STOP: STOP}

    RIGHT = dict([(y, x) for x, y in LEFT.items()])

    REVERSE = {NORTH: SOUTH, SOUTH: NORTH, EAST: WEST, WEST: EAST, STOP: STOP}


class Configuration:
    """
    A Configuration holds the (x,y) coordinate of a character, along with its
    traveling direction.

    The convention for positions, like a graph, is that (0,0) is the lower left corner, x increases
    horizontally and y increases vertically. Therefore, north is the direction of increasing y, or (0,1).
    """

    def __init__(self, pos: Tuple[float, float], direction: str) -> None:
        self.pos = pos
        self.direction = direction

    def getPosition(self) -> Tuple[float, float]:
        return self.pos

    def getDirection(self) -> str:
        return self.direction

    def isInteger(self) -> bool:
        x, y = self.pos
        return x == int(x) and y == int(y)

    def __eq__(self, other: Optional['Configuration']) -> bool:
        if other == None:
            return False
        return self.pos == other.pos and self.direction == other.direction

    def __hash__(self) -> int:
        x = hash(self.pos)
        y = hash(self.direction)
        return hash(x + 13 * y)

    def __str__(self) -> str:
        return f"(x,y)={str(self.pos)}, {str(self.direction)}"

    def generateSuccessor(self, vector: Tuple[float, float]) -> 'Configuration':
        """
        Generates a new configuration reached by translating the current
        configuration by the action vector. This is a low-level call and does
        not attempt to respect the legality of the movement.

        Args:
            vector: The movement vector (dx, dy)
            
        Returns:
            Configuration: The new configuration after moving
        """
        x, y = self.pos
        dx, dy = vector
        direction = Actions.vectorToDirection(vector)
        if direction == Directions.STOP:
            direction = self.direction  # There is no stop direction
        return Configuration((x + dx, y + dy), direction)


class AgentState:
    """
    AgentStates hold the state of an agent (configuration, speed, scared, etc).
    """

    def __init__(self, startConfiguration: Configuration, isPacman: bool) -> None:
        self.start = startConfiguration
        self.configuration = startConfiguration
        self.isPacman = isPacman
        self.scaredTimer = 0
        self.numCarrying = 0
        self.numReturned = 0

    def __str__(self) -> str:
        if self.isPacman:
            return f"Pacman: {str(self.configuration)}"
        else:
            return f"Ghost: {str(self.configuration)}"

    def __eq__(self, other: Optional['AgentState']) -> bool:
        if other == None:
            return False
        return (
            self.configuration == other.configuration
            and self.scaredTimer == other.scaredTimer
        )

    def __hash__(self) -> int:
        return hash(hash(self.configuration) + 13 * hash(self.scaredTimer))

    def copy(self) -> 'AgentState':
        state = AgentState(self.start, self.isPacman)
        state.configuration = self.configuration
        state.scaredTimer = self.scaredTimer
        state.numCarrying = self.numCarrying
        state.numReturned = self.numReturned
        return state

    def getPosition(self) -> Optional[Tuple[float, float]]:
        if self.configuration == None:
            return None
        return self.configuration.getPosition()

    def getDirection(self) -> str:
        return self.configuration.getDirection()


class Grid:
    """
    A 2-dimensional array of objects backed by a list of lists. Data is accessed
    via grid[x][y] where (x,y) are positions on a Pacman map with x horizontal,
    y vertical and the origin (0,0) in the bottom left corner.

    The __str__ method constructs an output that is oriented like a pacman board.
    """

    def __init__(self, width: int, height: int, initialValue: bool = False, bitRepresentation: Optional[Tuple[int, ...]] = None) -> None:
        if initialValue not in [False, True]:
            raise Exception("Grids can only contain booleans")
        self.CELLS_PER_INT = 30

        self.width = width
        self.height = height
        self.data = [[initialValue for y in range(height)] for x in range(width)]
        if bitRepresentation:
            self._unpackBits(bitRepresentation)

    def __getitem__(self, i: int) -> List[bool]:
        return self.data[i]

    def __setitem__(self, key: int, item: List[bool]) -> None:
        self.data[key] = item

    def __str__(self) -> str:
        out = [
            [str(self.data[x][y])[0] for x in range(self.width)]
            for y in range(self.height)
        ]
        out.reverse()
        return "\n".join(["".join(x) for x in out])

    def __eq__(self, other: Optional['Grid']) -> bool:
        if other == None:
            return False
        return self.data == other.data

    def __hash__(self) -> int:
        # return hash(str(self))
        base = 1
        h = 0
        for l in self.data:
            for i in l:
                if i:
                    h += base
                base *= 2
        return hash(h)

    def copy(self) -> 'Grid':
        g = Grid(self.width, self.height)
        g.data = [x[:] for x in self.data]
        return g

    def deepCopy(self) -> 'Grid':
        return self.copy()

    def shallowCopy(self) -> 'Grid':
        g = Grid(self.width, self.height)
        g.data = self.data
        return g

    def count(self, item: bool = True) -> int:
        return sum([x.count(item) for x in self.data])

    def asList(self, key: bool = True) -> List[Tuple[int, int]]:
        list = []
        for x in range(self.width):
            for y in range(self.height):
                if self[x][y] == key:
                    list.append((x, y))
        return list

    def packBits(self) -> Tuple[int, ...]:
        """
        Returns an efficient int list representation

        Returns:
            Tuple[int, ...]: (width, height, bitPackedInts...)
        """
        bits = [self.width, self.height]
        currentInt = 0
        for i in range(self.height * self.width):
            bit = self.CELLS_PER_INT - (i % self.CELLS_PER_INT) - 1
            x, y = self._cellIndexToPosition(i)
            if self[x][y]:
                currentInt += 2 ** bit
            if (i + 1) % self.CELLS_PER_INT == 0:
                bits.append(currentInt)
                currentInt = 0
        bits.append(currentInt)
        return tuple(bits)

    def _cellIndexToPosition(self, index: int) -> Tuple[int, int]:
        x = index / self.height
        y = index % self.height
        return x, y

    def _unpackBits(self, bits: Tuple[int, ...]) -> None:
        """
        Fills in data from a bit-level representation
        
        Args:
            bits: Tuple of integers representing the bit-packed grid
        """
        cell = 0
        for packed in bits:
            for bit in self._unpackInt(packed, self.CELLS_PER_INT):
                if cell == self.width * self.height:
                    break
                x, y = self._cellIndexToPosition(cell)
                self[x][y] = bit
                cell += 1

    def _unpackInt(self, packed: int, size: int) -> List[bool]:
        bools = []
        if packed < 0:
            raise ValueError("must be a positive integer")
        for i in range(size):
            n = 2 ** (self.CELLS_PER_INT - i - 1)
            if packed >= n:
                bools.append(True)
                packed -= n
            else:
                bools.append(False)
        return bools


def reconstituteGrid(bitRep: Union[Tuple[int, ...], Any]) -> Union[Grid, Any]:
    if type(bitRep) is not type((1, 2)):
        return bitRep
    width, height = bitRep[:2]
    return Grid(width, height, bitRepresentation=bitRep[2:])


####################################
# Parts you shouldn't have to read #
####################################


class Actions:
    """
    A collection of static methods for manipulating move actions.
    """

    # Directions
    _directions = {
        Directions.NORTH: (0, 1),
        Directions.SOUTH: (0, -1),
        Directions.EAST: (1, 0),
        Directions.WEST: (-1, 0),
        Directions.STOP: (0, 0),
    }

    _directionsAsList = _directions.items()

    TOLERANCE = 0.001

    def reverseDirection(action: str) -> str:
        if action == Directions.NORTH:
            return Directions.SOUTH
        if action == Directions.SOUTH:
            return Directions.NORTH
        if action == Directions.EAST:
            return Directions.WEST
        if action == Directions.WEST:
            return Directions.EAST
        return action

    reverseDirection = staticmethod(reverseDirection)

    def vectorToDirection(vector: Tuple[float, float]) -> str:
        dx, dy = vector
        if dy > 0:
            return Directions.NORTH
        if dy < 0:
            return Directions.SOUTH
        if dx < 0:
            return Directions.WEST
        if dx > 0:
            return Directions.EAST
        return Directions.STOP

    vectorToDirection = staticmethod(vectorToDirection)

    def directionToVector(direction: str, speed: float = 1.0) -> Tuple[float, float]:
        dx, dy = Actions._directions[direction]
        return (dx * speed, dy * speed)

    directionToVector = staticmethod(directionToVector)

    def getPossibleActions(config: Configuration, walls: Grid) -> List[str]:
        possible = []
        x, y = config.pos
        x_int, y_int = int(x + 0.5), int(y + 0.5)

        # In between grid points, all agents must continue straight
        if abs(x - x_int) + abs(y - y_int) > Actions.TOLERANCE:
            return [config.getDirection()]

        for dir, vec in Actions._directionsAsList:
            dx, dy = vec
            next_y = y_int + dy
            next_x = x_int + dx
            if not walls[next_x][next_y]:
                possible.append(dir)

        return possible

    getPossibleActions = staticmethod(getPossibleActions)

    def getLegalNeighbors(position: Tuple[int, int], walls: Grid) -> List[Tuple[int, int]]:
        x, y = position
        x_int, y_int = int(x + 0.5), int(y + 0.5)
        neighbors = []
        for dir, vec in Actions._directionsAsList:
            dx, dy = vec
            next_x = x_int + dx
            if next_x < 0 or next_x == walls.width:
                continue
            next_y = y_int + dy
            if next_y < 0 or next_y == walls.height:
                continue
            if not walls[next_x][next_y]:
                neighbors.append((next_x, next_y))
        return neighbors

    getLegalNeighbors = staticmethod(getLegalNeighbors)

    def getSuccessor(position: Tuple[float, float], action: str) -> Tuple[float, float]:
        dx, dy = Actions.directionToVector(action)
        x, y = position
        return (x + dx, y + dy)

    getSuccessor = staticmethod(getSuccessor)


class GameStateData:
    """ """

    def __init__(self, prevState: Optional['GameStateData'] = None) -> None:
        """
        Generates a new data packet by copying information from its predecessor.
        """
        if prevState != None:
            self.food = prevState.food.shallowCopy()
            self.capsules = prevState.capsules[:]
            self.agentStates = self.copyAgentStates(prevState.agentStates)
            self.layout = prevState.layout
            self._eaten = prevState._eaten
            self.score = prevState.score

        self._foodEaten = None
        self._foodAdded = None
        self._capsuleEaten = None
        self._agentMoved = None
        self._lose = False
        self._win = False
        self.scoreChange = 0

    def deepCopy(self) -> 'GameStateData':
        state = GameStateData(self)
        state.food = self.food.deepCopy()
        state.layout = self.layout.deepCopy()
        state._agentMoved = self._agentMoved
        state._foodEaten = self._foodEaten
        state._foodAdded = self._foodAdded
        state._capsuleEaten = self._capsuleEaten
        return state

    def copyAgentStates(self, agentStates: List[AgentState]) -> List[AgentState]:
        copiedStates = []
        for agentState in agentStates:
            copiedStates.append(agentState.copy())
        return copiedStates

    def __eq__(self, other: Optional['GameStateData']) -> bool:
        """
        Allows two states to be compared.
        """
        if other == None:
            return False
        # TODO Check for type of other
        if not self.agentStates == other.agentStates:
            return False
        if not self.food == other.food:
            return False
        if not self.capsules == other.capsules:
            return False
        if not self.score == other.score:
            return False
        return True

    def __hash__(self) -> int:
        """
        Allows states to be keys of dictionaries.
        """
        for i, state in enumerate(self.agentStates):
            try:
                int(hash(state))
            except TypeError as e:
                print(e)
                # hash(state)
        return int(
            (
                hash(tuple(self.agentStates))
                + 13 * hash(self.food)
                + 113 * hash(tuple(self.capsules))
                + 7 * hash(self.score)
            )
            % 1048575
        )

    def __str__(self) -> str:
        width, height = self.layout.width, self.layout.height
        map = Grid(width, height)
        if type(self.food) == type((1, 2)):
            self.food = reconstituteGrid(self.food)
        for x in range(width):
            for y in range(height):
                food, walls = self.food, self.layout.walls
                map[x][y] = self._foodWallStr(food[x][y], walls[x][y])

        for agentState in self.agentStates:
            if agentState == None:
                continue
            if agentState.configuration == None:
                continue
            x, y = [int(i) for i in nearestPoint(agentState.configuration.pos)]
            agent_dir = agentState.configuration.direction
            if agentState.isPacman:
                map[x][y] = self._pacStr(agent_dir)
            else:
                map[x][y] = self._ghostStr(agent_dir)

        for x, y in self.capsules:
            map[x][y] = "o"

        return f"{str(map)}\nScore: {self.score}\n"

    def _foodWallStr(self, hasFood: bool, hasWall: bool) -> str:
        if hasFood:
            return "."
        elif hasWall:
            return "%"
        else:
            return " "

    def _pacStr(self, dir: str) -> str:
        if dir == Directions.NORTH:
            return "v"
        if dir == Directions.SOUTH:
            return "^"
        if dir == Directions.WEST:
            return ">"
        return "<"

    def _ghostStr(self, dir: str) -> str:
        return "G"
        if dir == Directions.NORTH:
            return "M"
        if dir == Directions.SOUTH:
            return "W"
        if dir == Directions.WEST:
            return "3"
        return "E"

    def initialize(self, layout: Any, numGhostAgents: int) -> None:
        """
        Creates an initial game state from a layout array (see layout.py).
        
        Args:
            layout: The layout of the game board
            numGhostAgents: Number of ghost agents in the game
        """
        self.food = layout.food.copy()
        # self.capsules = []
        self.capsules = layout.capsules[:]
        self.layout = layout
        self.score = 0
        self.scoreChange = 0

        self.agentStates = []
        numGhosts = 0
        for isPacman, pos in layout.agentPositions:
            if not isPacman:
                if numGhosts == numGhostAgents:
                    continue  # Max ghosts reached already
                else:
                    numGhosts += 1
            self.agentStates.append(
                AgentState(Configuration(pos, Directions.STOP), isPacman)
            )
        self._eaten = [False for a in self.agentStates]


try:
    import boinc
    _BOINC_ENABLED = True
except:
    _BOINC_ENABLED = False


class Game:
    """
    The Game manages the control flow, soliciting actions from agents.
    """

    def __init__(
        self,
        agents: List[Agent],
        display: Any,
        rules: Any,
        startingIndex: int = 0,
        muteAgents: bool = False,
        catchExceptions: bool = False,
    ) -> None:
        self.agentCrashed = False
        self.agents = agents
        self.display = display
        self.rules = rules
        self.startingIndex = startingIndex
        self.gameOver = False
        self.muteAgents = muteAgents
        self.catchExceptions = catchExceptions
        self.moveHistory = []
        self.totalAgentTimes = [0 for agent in agents]
        self.totalAgentTimeWarnings = [0 for agent in agents]
        self.agentTimeout = False
        import io
        self.agentOutput = [io.StringIO() for agent in agents]

    def getProgress(self) -> float:
        if self.gameOver:
            return 1.0
        else:
            return self.rules.getProgress(self)

    def _agentCrash(self, agentIndex: int, quiet: bool = False) -> None:
        "Helper method for handling agent crashes"
        if not quiet:
            traceback.print_exc()
        self.gameOver = True
        self.agentCrashed = True
        self.rules.agentCrash(self, agentIndex)

    OLD_STDOUT = None
    OLD_STDERR = None

    def mute(self, agentIndex: int) -> None:
        if not self.muteAgents:
            return
        global OLD_STDOUT, OLD_STDERR
        import io
        OLD_STDOUT = sys.stdout
        OLD_STDERR = sys.stderr
        sys.stdout = self.agentOutput[agentIndex]
        sys.stderr = self.agentOutput[agentIndex]

    def unmute(self) -> None:
        if not self.muteAgents:
            return
        global OLD_STDOUT, OLD_STDERR
        # Revert stdout/stderr to originals
        sys.stdout = OLD_STDOUT
        sys.stderr = OLD_STDERR

    def run(self) -> None:
        """
        Main control loop for game play.
        """
        self.display.initialize(self.state.data)
        self.numMoves = 0

        ###self.display.initialize(self.state.makeObservation(1).data)
        # inform learning agents of the game start
        for i in range(len(self.agents)):
            agent = self.agents[i]
            if not agent:
                self.mute(i)
                # this is a null agent, meaning it failed to load
                # the other team wins
                print(f"Agent {i} failed to load", file=sys.stderr)
                self.unmute()
                self._agentCrash(i, quiet=True)
                return
            if "registerInitialState" in dir(agent):
                self.mute(i)
                if self.catchExceptions:
                    try:
                        timed_func = TimeoutFunction(
                            agent.registerInitialState,
                            int(self.rules.getMaxStartupTime(i)),
                        )
                        try:
                            start_time = time.time()
                            timed_func(self.state.deepCopy())
                            time_taken = time.time() - start_time
                            self.totalAgentTimes[i] += time_taken
                        except TimeoutFunctionException:
                            print(
                                f"Agent {i} ran out of time on startup!",
                                file=sys.stderr,
                            )
                            self.unmute()
                            self.agentTimeout = True
                            self._agentCrash(i, quiet=True)
                            return
                    except Exception as data:
                        self._agentCrash(i, quiet=False)
                        self.unmute()
                        return
                else:
                    agent.registerInitialState(self.state.deepCopy())
                ## TODO: could this exceed the total time
                self.unmute()

        agentIndex = self.startingIndex
        numAgents = len(self.agents)

        while not self.gameOver:
            # Fetch the next agent
            agent = self.agents[agentIndex]
            move_time = 0
            skip_action = False
            # Generate an observation of the state
            if "observationFunction" in dir(agent):
                self.mute(agentIndex)
                if self.catchExceptions:
                    try:
                        timed_func = TimeoutFunction(
                            agent.observationFunction,
                            int(self.rules.getMoveTimeout(agentIndex)),
                        )
                        try:
                            start_time = time.time()
                            observation = timed_func(self.state.deepCopy())
                        except TimeoutFunctionException:
                            skip_action = True
                        move_time += time.time() - start_time
                        self.unmute()
                    except Exception as data:
                        self._agentCrash(agentIndex, quiet=False)
                        self.unmute()
                        return
                else:
                    observation = agent.observationFunction(self.state.deepCopy())
                self.unmute()
            else:
                observation = self.state.deepCopy()

            # Solicit an action
            action = None
            self.mute(agentIndex)
            if self.catchExceptions:
                try:
                    timed_func = TimeoutFunction(
                        agent.getAction,
                        int(self.rules.getMoveTimeout(agentIndex)) - int(move_time),
                    )
                    try:
                        start_time = time.time()
                        if skip_action:
                            raise TimeoutFunctionException()
                        action = timed_func(observation)
                    except TimeoutFunctionException:
                        print(
                            f"Agent {agentIndex} timed out on a single move!",
                            file=sys.stderr,
                        )
                        self.agentTimeout = True
                        self._agentCrash(agentIndex, quiet=True)
                        self.unmute()
                        return

                    move_time += time.time() - start_time

                    if move_time > self.rules.getMoveWarningTime(agentIndex):
                        self.totalAgentTimeWarnings[agentIndex] += 1
                        print(
                            f"Agent {agentIndex} took too long to make a move! This is warning {self.totalAgentTimeWarnings[agentIndex]}",
                            file=sys.stderr,
                        )
                        if self.totalAgentTimeWarnings[
                            agentIndex
                        ] > self.rules.getMaxTimeWarnings(agentIndex):
                            print(
                                f"Agent {agentIndex} exceeded the maximum number of warnings: {self.totalAgentTimeWarnings[agentIndex]}",
                                file=sys.stderr,
                            )
                            self.agentTimeout = True
                            self._agentCrash(agentIndex, quiet=True)
                            self.unmute()
                            return

                    self.totalAgentTimes[agentIndex] += move_time
                    # print "Agent: %d, time: %f, total: %f" % (agentIndex, move_time, self.totalAgentTimes[agentIndex])
                    if self.totalAgentTimes[agentIndex] > self.rules.getMaxTotalTime(
                        agentIndex
                    ):
                        print(
                            f"Agent {agentIndex} ran out of time! (time: {self.totalAgentTimes[agentIndex]:.2f})",
                            file=sys.stderr,
                        )
                        self.agentTimeout = True
                        self._agentCrash(agentIndex, quiet=True)
                        self.unmute()
                        return
                    self.unmute()
                except Exception as data:
                    self._agentCrash(agentIndex)
                    self.unmute()
                    return
            else:
                action = agent.getAction(observation)
            self.unmute()

            # Execute the action
            self.moveHistory.append((agentIndex, action))
            if self.catchExceptions:
                try:
                    self.state = self.state.getResult(agentIndex, action)
                except Exception as data:
                    self.mute(agentIndex)
                    self._agentCrash(agentIndex)
                    self.unmute()
                    return
            else:
                # Check if the state has a getResult method: for running pacman.py
                # instead of busters.py with the inference module (else clause)
                if hasattr(self.state, 'getResult'):
                    self.state = self.state.getResult(agentIndex, action)
                else:
                    self.state = self.state.generateSuccessor(agentIndex, action)

            # Change the display
            self.display.update(self.state.data)
            ###idx = agentIndex - agentIndex % 2 + 1
            ###self.display.update( self.state.makeObservation(idx).data )

            # Allow for game specific conditions (winning, losing, etc.)
            self.rules.process(self.state, self)
            # Track progress
            if agentIndex == numAgents + 1:
                self.numMoves += 1
            # Next agent
            agentIndex = (agentIndex + 1) % numAgents

            if _BOINC_ENABLED:
                boinc.set_fraction_done(self.getProgress())

        # inform a learning agent of the game result
        for agentIndex, agent in enumerate(self.agents):
            if "final" in dir(agent):
                try:
                    self.mute(agentIndex)
                    agent.final(self.state)
                    self.unmute()
                except Exception as data:
                    if not self.catchExceptions:
                        raise
                    self._agentCrash(agentIndex)
                    self.unmute()
                    return
        self.display.finish()
