"""
# inference.py
# ------------
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

Inference module for the Pacman game.

This module provides probabilistic inference capabilities for tracking
ghost positions in the Pacman game. Key components include:

1. DiscreteDistribution - Models belief distributions over discrete states
2. Inference algorithms for ghost position tracking
3. Particle filtering implementation
4. Exact inference using forward algorithm
5. Joint particle filtering for multiple ghosts

The module works with game.py and ghostAgents.py to enable probabilistic
reasoning about ghost locations based on noisy sensor readings.

Changes by George Rudolph 30 Nov 2024:
- Verified compatibility with Python 3.13
- Enhanced module documentation
- Added type hints throughout
- Improved class and method documentation
- Modernized DiscreteDistribution implementation
- Added input validation
"""

import itertools
import collections
import random
import busters
import game
from typing import Dict, List, Tuple, Optional, Any

from util import manhattanDistance, raiseNotDefined


class DiscreteDistribution(dict):
    """
    A DiscreteDistribution models belief distributions and weight distributions
    over a finite set of discrete keys.

    This class extends dict to represent probability distributions and weights
    over discrete outcomes. It provides methods for normalization, sampling,
    and finding maximum values.
    """

    def __getitem__(self, key: Any) -> float:
        """
        Return the value for the given key, defaulting to 0 if not present.
        
        Args:
            key: The key to look up
            
        Returns:
            The value associated with the key, or 0 if not found
        """
        self.setdefault(key, 0)
        return dict.__getitem__(self, key)

    def copy(self) -> 'DiscreteDistribution':
        """
        Return a deep copy of the distribution.
        
        Returns:
            A new DiscreteDistribution with the same key-value pairs
        """
        return DiscreteDistribution(dict.copy(self))

    def argMax(self) -> Optional[Any]:
        """
        Return the key with the highest value.
        
        Returns:
            The key with maximum value, or None if distribution is empty
        """
        if len(self.keys()) == 0:
            return None
        all = list(self.items())
        values = [x[1] for x in all]
        maxIndex = values.index(max(values))
        return all[maxIndex][0]

    def total(self) -> float:
        """
        Return the sum of values for all keys.
        
        Returns:
            The total sum of all values in the distribution
        """
        return float(sum(self.values()))

    def normalize(self) -> None:
        """
        Normalize the distribution such that the total value of all keys sums
        to 1. The ratio of values for all keys will remain the same. In the case
        where the total value of the distribution is 0, do nothing.

        Examples:
            >>> dist = DiscreteDistribution()
            >>> dist['a'] = 1
            >>> dist['b'] = 2
            >>> dist['c'] = 2
            >>> dist['d'] = 0
            >>> dist.normalize()
            >>> list(sorted(dist.items()))
            [('a', 0.2), ('b', 0.4), ('c', 0.4), ('d', 0.0)]
            >>> dist['e'] = 4
            >>> list(sorted(dist.items()))
            [('a', 0.2), ('b', 0.4), ('c', 0.4), ('d', 0.0), ('e', 4)]
            >>> empty = DiscreteDistribution()
            >>> empty.normalize()
            >>> empty
            {}
        """
        "*** YOUR CODE HERE ***"
        
        first_total = self.total()
 
        if first_total == 0:
            return
        for d in self:
            prop = self[d]/first_total

            self[d] = prop


    def sample(self) -> Any:
        """
        Draw a random sample from the distribution and return the key, weighted
        by the value associated with each key.

        Returns:
            A randomly selected key based on the distribution weights

        Examples:
            >>> dist = DiscreteDistribution()
            >>> dist['a'] = 1
            >>> dist['b'] = 2
            >>> dist['c'] = 2
            >>> dist['d'] = 0
            >>> N = 100000.0
            >>> samples = [dist.sample() for _ in range(int(N))]
            >>> round(samples.count('a') * 1.0/N, 1)  # proportion of 'a'
            0.2
            >>> round(samples.count('b') * 1.0/N, 1)
            0.4
            >>> round(samples.count('c') * 1.0/N, 1)
            0.4
            >>> round(samples.count('d') * 1.0/N, 1)
            0.0
        """
        "*** YOUR CODE HERE ***"
        total = self.total()
        r = random.random() * total

        cumalat = 0.0
        for key, weight in self.items():
            cumalat += weight
            if r < cumalat:
                return key


class InferenceModule:
    """
    An inference module tracks a belief distribution over a ghost's location.
    This class handles the mechanics of combining observations and maintaining
    belief distributions over time.
    """

    ############################################
    # Useful methods for all inference modules #
    ############################################

    def __init__(self, ghostAgent: Any) -> None:
        """
        Set the ghost agent for later access.
        
        Args:
            ghostAgent: The agent representing the ghost being tracked
        """
        self.ghostAgent = ghostAgent
        self.index = ghostAgent.index
        self.obs = []  # most recent observation position

    def getJailPosition(self) -> Tuple[int, int]:
        """
        Return the jail position for the ghost.
        
        Returns:
            A tuple of (x,y) coordinates for the jail position
        """
        return (2 * self.ghostAgent.index - 1, 1)

    def getPositionDistributionHelper(self, gameState: Any, pos: Tuple[int, int], index: int, agent: Any) -> DiscreteDistribution:
        """
        Helper method for getPositionDistribution.
        
        Args:
            gameState: The current game state
            pos: The position to get distribution for
            index: The ghost index
            agent: The ghost agent
            
        Returns:
            A DiscreteDistribution over possible successor positions
        """
        try:
            jail = self.getJailPosition()
            gameState = self.setGhostPosition(gameState, pos, index + 1)
        except TypeError:
            jail = self.getJailPosition(index)
            gameState = self.setGhostPositions(gameState, pos)
        pacmanPosition = gameState.getPacmanPosition()
        ghostPosition = gameState.getGhostPosition(index + 1)  # The position you set
        dist = DiscreteDistribution()
        if pacmanPosition == ghostPosition:  # The ghost has been caught!
            dist[jail] = 1.0
            return dist
        pacmanSuccessorStates = game.Actions.getLegalNeighbors(
            pacmanPosition, gameState.getWalls()
        )  # Positions Pacman can move to
        if ghostPosition in pacmanSuccessorStates:  # Ghost could get caught
            mult = 1.0 / float(len(pacmanSuccessorStates))
            dist[jail] = mult
        else:
            mult = 0.0
        actionDist = agent.getDistribution(gameState)
        for action, prob in actionDist.items():
            successorPosition = game.Actions.getSuccessor(ghostPosition, action)
            if successorPosition in pacmanSuccessorStates:  # Ghost could get caught
                denom = float(len(actionDist))
                dist[jail] += prob * (1.0 / denom) * (1.0 - mult)
                dist[successorPosition] = prob * ((denom - 1.0) / denom) * (1.0 - mult)
            else:
                dist[successorPosition] = prob * (1.0 - mult)
        return dist

    def getPositionDistribution(self, gameState: Any, pos: Tuple[int, int], index: Optional[int] = None, agent: Optional[Any] = None) -> DiscreteDistribution:
        """
        Return a distribution over successor positions of the ghost from the
        given gameState. You must first place the ghost in the gameState, using
        setGhostPosition below.
        
        Args:
            gameState: The current game state
            pos: The position to get distribution for
            index: Optional ghost index (defaults to self.index - 1)
            agent: Optional ghost agent (defaults to self.ghostAgent)
            
        Returns:
            A DiscreteDistribution over possible successor positions
        """
        if index == None:
            index = self.index - 1
        if agent == None:
            agent = self.ghostAgent
        return self.getPositionDistributionHelper(gameState, pos, index, agent)

    def getObservationProb(
        self, noisy_distance: Optional[float], pacman_position: Tuple[int, int], 
        ghost_position: Tuple[int, int], jail_position: Tuple[int, int]
    ) -> float:
        """
        Return the probability P(noisy_distance | pacman_position, ghost_position).
        
        Args:
            noisy_distance: The noisy distance observation, or None
            pacman_position: Pacman's position
            ghost_position: The ghost's position
            jail_position: The jail position
            
        Returns:
            The probability of observing the noisy distance given the positions
        """
        "*** YOUR CODE HERE ***"
        if ghost_position == jail_position:
            if noisy_distance is not None:
                return 0
            else:
                return 1
            
        if noisy_distance is not None:
            distance_from_ghost = manhattanDistance(pacman_position, ghost_position)
            probability = busters.getObservationProbability(noisy_distance, distance_from_ghost)
            return probability

        return 0

    def setGhostPosition(self, gameState: Any, ghostPosition: Tuple[int, int], index: int) -> Any:
        """
        Set the position of the ghost for this inference module to the specified
        position in the supplied gameState.

        Note that calling setGhostPosition does not change the position of the
        ghost in the GameState object used for tracking the true progression of
        the game. The code in inference.py only ever receives a deep copy of
        the GameState object which is responsible for maintaining game state,
        not a reference to the original object.  Note also that the ghost
        distance observations are stored at the time the GameState object is
        created, so changing the position of the ghost will not affect the
        functioning of observe.
        
        Args:
            gameState: The game state to modify
            ghostPosition: The new ghost position
            index: The index of the ghost to modify
            
        Returns:
            The modified game state
        """
        conf = game.Configuration(ghostPosition, game.Directions.STOP)
        gameState.data.agentStates[index] = game.AgentState(conf, False)
        return gameState

    def setGhostPositions(self, gameState: Any, ghostPositions: List[Tuple[int, int]]) -> Any:
        """
        Sets the position of all ghosts to the values in ghostPositions.
        
        Args:
            gameState: The game state to modify
            ghostPositions: List of new ghost positions
            
        Returns:
            The modified game state
        """
        for index, pos in enumerate(ghostPositions):
            conf = game.Configuration(pos, game.Directions.STOP)
            gameState.data.agentStates[index + 1] = game.AgentState(conf, False)
        return gameState

    def observe(self, gameState: Any) -> None:
        """
        Collect the relevant noisy distance observation and pass it along.
        
        Args:
            gameState: The current game state
        """
        distances = gameState.getNoisyGhostDistances()
        if len(distances) >= self.index:  # Check for missing observations
            obs = distances[self.index - 1]
            self.obs = obs
            self.observeUpdate(obs, gameState)

    def initialize(self, gameState: Any) -> None:
        """
        Initialize beliefs to a uniform distribution over all legal positions.
        
        Args:
            gameState: The initial game state
        """
        self.legalPositions = [
            p for p in gameState.getWalls().asList(False) if p[1] > 1
        ]
        self.allPositions = self.legalPositions + [self.getJailPosition()]
        self.initializeUniformly(gameState)

    ######################################
    # Methods that need to be overridden #
    ######################################

    def initializeUniformly(self, gameState: Any) -> None:
        """
        Set the belief state to a uniform prior belief over all positions.
        
        Args:
            gameState: The initial game state
        """
        raise NotImplementedError


    def observeUpdate(self, observation: Optional[float], gameState: Any) -> None:
        """
        Update beliefs based on the given distance observation and gameState.
        
        Args:
            observation: The noisy distance observation
            gameState: The current game state
        """
        raise NotImplementedError


    def elapseTime(self, gameState: Any) -> None:
        """
        Predict beliefs for the next time step from a gameState.
        
        Args:
            gameState: The current game state
        """
        raise NotImplementedError

    def getBeliefDistribution(self) -> DiscreteDistribution:
        """
        Return the agent's current belief state, a distribution over ghost
        locations conditioned on all evidence so far.
        
        Returns:
            The current belief distribution
        """
        raise NotImplementedError

class ExactInference(InferenceModule):
    """
    The exact dynamic inference module should use forward algorithm updates to
    compute the exact belief function at each time step.
    """

    def initializeUniformly(self, gameState: Any) -> None:
        """
        Begin with a uniform distribution over legal ghost positions (i.e., not
        including the jail position).
        
        Args:
            gameState: The initial game state
        """
        self.beliefs = DiscreteDistribution()
        for p in self.legalPositions:
            self.beliefs[p] = 1.0
        self.beliefs.normalize()

    def observeUpdate(self, observation: Optional[float], gameState: Any) -> None:
        """
        Update beliefs based on the distance observation and Pacman's position.

        The observation is the noisy Manhattan distance to the ghost you are
        tracking.

        self.allPositions is a list of the possible ghost positions, including
        the jail position. You should only consider positions that are in
        self.allPositions.

        The update model is not entirely stationary: it may depend on Pacman's
        current position. However, this is not a problem, as Pacman's current
        position is known.
        
        Args:
            observation: The noisy distance observation
            gameState: The current game state
        """
        "*** YOUR CODE HERE ***"
        for ghost in self.allPositions:
            observationProb = self.getObservationProb(
                observation,
                gameState.getPacmanPosition(),
                ghost,
                self.getJailPosition()
            )
            self.beliefs[ghost] = self.beliefs[ghost] * observationProb
        self.beliefs.normalize()

    def elapseTime(self, game_state: Any) -> None:
        """
        Predict beliefs in response to a time step passing from the current
        state.

        The transition model is not entirely stationary: it may depend on
        Pacman's current position. However, this is not a problem, as Pacman's
        current position is known.
        
        Args:
            game_state: The current game state
        """
        "*** YOUR CODE HERE ***"
        belief = self.getBeliefDistribution()

        distribution = DiscreteDistribution()

        for oldPos in self.allPositions:
            new_dist = self.getPositionDistribution(game_state, oldPos)
            for pos, prob in new_dist.items():
                distribution[pos] += belief[oldPos] * prob

                
        self.beliefs = distribution

    def getBeliefDistribution(self) -> DiscreteDistribution:
        """
        Return the agent's current belief distribution.
        
        Returns:
            The current belief distribution
        """
        return self.beliefs


class ParticleFilter(InferenceModule):
    """
    A particle filter for approximately tracking a single ghost.
    """

    def __init__(self, ghostAgent: Any, numParticles: int = 300) -> None:
        """
        Initialize the particle filter with the given ghost agent and number of particles.
        
        Args:
            ghostAgent: The ghost agent to track
            numParticles: Number of particles to use
        """
        InferenceModule.__init__(self, ghostAgent)
        self.setNumParticles(numParticles)

    def setNumParticles(self, numParticles: int) -> None:
        """
        Set the number of particles.
        
        Args:
            numParticles: The new number of particles
        """
        self.numParticles = numParticles

    def initializeUniformly(self, game_state: Any) -> None:
        """
        Initialize a list of particles. Use self.numParticles for the number of
        particles. Use self.legalPositions for the legal board positions where
        a particle could be located. Particles should be evenly (not randomly)
        distributed across positions in order to ensure a uniform prior. Use
        self.particles for the list of particles.
        
        Args:
            game_state: The initial game state
        """
        self.particles = []
        "*** YOUR CODE HERE ***"
        nums = 0
        while(nums < self.numParticles):
            
            for action in self.legalPositions:
                self.particles.append(action)
                nums +=1

    def observeUpdate(self, observation: Optional[float], gameState: Any) -> None:
        """
        Update beliefs based on the distance observation and Pacman's position.

        The observation is the noisy Manhattan distance to the ghost you are
        tracking.

        There is one special case that a correct implementation must handle.
        When all particles receive zero weight, the list of particles should
        be reinitialized by calling initializeUniformly. The total method of
        the DiscreteDistribution may be useful.
        
        Args:
            observation: The noisy distance observation
            gameState: The current game state
        """
        "*** YOUR CODE HERE ***"

        pacman = gameState.getPacmanPosition()
        jail = self.getJailPosition()

        distProb = DiscreteDistribution()

        for particle in self.particles:
            obsProb = self.getObservationProb(observation, pacman, particle, jail)
            distProb[particle] = distProb.get(particle, 0) + obsProb

        distProb.normalize()

        if distProb.total() == 0:
            self.initializeUniformly(gameState)
            return
        
        newParticles = []
        for i in range(self.numParticles):
            newParticles.append(distProb.sample())
        self.particles = newParticles
        
    def elapseTime(self, gameState: Any) -> None:
        """
        Sample each particle's next state based on its current state and the
        gameState.
        
        Args:
            gameState: The current game state
        """
        "*** YOUR CODE HERE ***"
        belief = self.getBeliefDistribution()

        distribution = DiscreteDistribution()

        for oldPos in self.allPositions:
            new_dist = self.getPositionDistribution(gameState, oldPos)
            for pos, prob in new_dist.items():
                distribution[pos] += belief[oldPos] * prob

                
        self.beliefs = distribution

    def getBeliefDistribution(self) -> DiscreteDistribution:
        """
        Return the agent's current belief state, a distribution over ghost
        locations conditioned on all evidence and time passage. This method
        essentially converts a list of particles into a belief distribution.

        This function should return a normalized distribution.
        
        Returns:
            The current belief distribution
        """
        "*** YOUR CODE HERE ***"
        dist = DiscreteDistribution()

        for p in self.particles:
            dist[p] += 1
        
        dist.normalize() 
        return dist

class JointParticleFilter(ParticleFilter):
    """
    JointParticleFilter tracks a joint distribution over tuples of all ghost
    positions.
    """

    def __init__(self, numParticles: int = 600) -> None:
        """
        Initialize with the given number of particles.
        
        Args:
            numParticles: Number of particles to use
        """
        self.setNumParticles(numParticles)

    def initialize(self, game_state: Any, legal_positions: List[Tuple[int, int]]) -> None:
        """
        Store information about the game, then initialize particles.
        
        Args:
            game_state: The initial game state
            legal_positions: List of legal ghost positions
        """
        self.numGhosts = game_state.getNumAgents() - 1
        self.ghostAgents = []
        self.legalPositions = legal_positions
        self.initializeUniformly(game_state)

    def initializeUniformly(self, game_state: Any) -> None:
        """
        Initialize particles to be consistent with a uniform prior. Particles
        should be evenly distributed across positions in order to ensure a
        uniform prior.
        
        Args:
            game_state: The initial game state
        """
        self.particles = []
        "*** YOUR CODE HERE ***"
        pos = list(itertools.product(self.legalPositions, repeat = self.numGhosts))
        
        nums = 0
        while(nums < self.numParticles):
            
            for action in pos:
                self.particles.append(action)
                nums +=1



    def addGhostAgent(self, agent: Any) -> None:
        """
        Each ghost agent is registered separately and stored (in case they are
        different).
        
        Args:
            agent: The ghost agent to add
        """
        self.ghostAgents.append(agent)

    def getJailPosition(self, i: int) -> Tuple[int, int]:
        """
        Get the jail position for the given ghost index.
        
        Args:
            i: The ghost index
            
        Returns:
            The jail position coordinates
        """
        return (2 * i + 1, 1)

    def observe(self, gameState: Any) -> None:
        """
        Resample the set of particles using the likelihood of the noisy
        observations.
        
        Args:
            gameState: The current game state
        """
        observation = gameState.getNoisyGhostDistances()
        self.observeUpdate(observation, gameState)

    def observeUpdate(self, observation: List[Optional[float]], gameState: Any) -> None:
        """
        Update beliefs based on the distance observation and Pacman's position.

        The observation is the noisy Manhattan distances to all ghosts you
        are tracking.

        There is one special case that a correct implementation must handle.
        When all particles receive zero weight, the list of particles should
        be reinitialized by calling initializeUniformly. The total method of
        the DiscreteDistribution may be useful.
        
        Args:
            observation: List of noisy distance observations
            gameState: The current game state
        """
        "*** YOUR CODE HERE ***"

        dist = DiscreteDistribution()

        for particle in self.particles:
            prob = 1.0
            for i in range(self.numGhosts):
                ghosts = observation[i]
                jail = self.getJailPosition(i)
                if ghosts is not None:
                    prob *= self.getObservationProb(ghosts, gameState.getPacmanPosition(), particle[i], jail)
                    continue
                particle = list(particle)
                particle[i] = jail
                particle = tuple(particle)
                prob = 0
            dist[particle] += prob
        dist.normalize()

        if dist.total() == 0:
            self.initializeUniformly(gameState)
            dist = self.getBeliefDistribution()
        
        self.particles = []
        for i in range(self.numParticles):
            self.particles.append(dist.sample())

    def elapseTime(self, game_state: Any) -> None:
        """
        Sample each particle's next state based on its current state and the
        gameState.
        
        Args:
            game_state: The current game state
        """
        newParticles = []
        for oldParticle in self.particles:
            newParticle = list(oldParticle)  # A list of ghost positions

            # now loop through and update each entry in newParticle...
            "*** YOUR CODE HERE ***"
            for ghost_i  in range(self.numGhosts):
                dist = self.getPositionDistribution(game_state, oldParticle, ghost_i, self.ghostAgents[ghost_i])
                new_pos = dist.sample()

                newParticle[ghost_i] = tuple(new_pos)

            """*** END YOUR CODE HERE ***"""
            newParticles.append(tuple(newParticle))
        self.particles = newParticles


# One JointInference module is shared globally across instances of MarginalInference
jointInference = JointParticleFilter()


class MarginalInference(InferenceModule):
    """
    A wrapper around the JointInference module that returns marginal beliefs
    about ghosts.
    """

    def initializeUniformly(self, gameState: Any) -> None:
        """
        Set the belief state to an initial, prior value.
        
        Args:
            gameState: The initial game state
        """
        if self.index == 1:
            jointInference.initialize(gameState, self.legalPositions)
        jointInference.addGhostAgent(self.ghostAgent)

    def observe(self, gameState: Any) -> None:
        """
        Update beliefs based on the given distance observation and gameState.
        
        Args:
            gameState: The current game state
        """
        if self.index == 1:
            jointInference.observe(gameState)

    def elapseTime(self, gameState: Any) -> None:
        """
        Predict beliefs for a time step elapsing from a gameState.
        
        Args:
            gameState: The current game state
        """
        if self.index == 1:
            jointInference.elapseTime(gameState)

    def getBeliefDistribution(self) -> DiscreteDistribution:
        """
        Return the marginal belief over a particular ghost by summing out the
        others.
        
        Returns:
            The marginal belief distribution for this ghost
        """
        jointDistribution = jointInference.getBeliefDistribution()
        dist = DiscreteDistribution()
        for t, prob in jointDistribution.items():
            dist[t[self.index - 1]] += prob
        return dist
