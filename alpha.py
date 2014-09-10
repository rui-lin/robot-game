import rg
import math
import random
from collections import namedtuple, defaultdict

TurnState = namedtuple("TurnState", "players enemies attack_locs move_locs " +
                                    "explode_locs guard_locs")
class ReconstructedInfo:
    def __init__(self):
        self.actions = []

class PredictedInfo:
    def __init__(self):
        self.will_explode = False


# Assumes max 4 units 'beside' a robot (north south east west)
class IntelUnit:
    # reconstructed_actions list
    default = 0
    died_by_player = 1
    died_by_spawn = 2
    exploded = 3
    moved = 4
    guarded = 5

    def __init__(self):
        self.turns = {}
        self.enemy_explode_hp_given_nrobots = [0] + [8]*4
        self.player_id = None

        # Per turn variables
        self.current_turn = -1
        self.reconstructed_info = {}
        self.predicted_info = defaultdict(PredictedInfo)

    def _high_player_damage_at_loc(self, loc, turn):
        return (self.turns[turn].attack_locs[loc]*10 +
                sum (15 for l in rg.locs_around(loc)
                     if l in self.turns[turn].explode_locs))

    def _low_player_damage_at_loc(self, loc, turn):
        return (self.turns[turn].attack_locs[loc]*8 +
                sum (15 for l in rg.locs_around(loc)
                     if l in self.turns[turn].explode_locs))

    def _add_reconstructed_action(self, enemy, action):
        if enemy.location not in self.reconstructed_info:
            self.reconstructed_info[enemy.location] = ReconstructedInfo()
        #print "Adding action {0} to {1}, now has {2}".format(
        #    action, enemy.location, self.reconstructed_info[enemy.location].actions)
        self.reconstructed_info[enemy.location].actions += [action]

    # analyze move of enemy in prev turn
    # possibilities are
    # attack, guard, move, explode
    # Tested, cannot move into a location of exploding/dying robot
    # So find locations where enemy robots disappeared.
    def _analyze_enemy_move(self, enemy):
        if enemy.location in self.reconstructed_info:  # already analyzed
            return
        self._add_reconstructed_action(enemy, self.default)

        turn = self.current_turn
        enemyl = enemy.location
        old_enemiesl = {x.location: x for x in self.enemies(turn-1)}
        new_enemiesl = {x.location: x for x in self.enemies(turn)}
        if enemyl not in old_enemiesl:
            print "WARNING: this method is only for enemies of previous turn"
            return

        # move, died by player, died by spawn, exploded
        if enemyl not in new_enemiesl:
            # Find places enemy could have moved to (and is now dead or alive)
            # Leniency towards moving, since its less risky.
            moved_locs = rg.locs_around(enemyl)
            moved_locs = [loc for loc in moved_locs if
                ((loc in new_enemiesl and new_enemiesl[loc].hp <= enemy.hp -
                  self._low_player_damage_at_loc(loc, turn-1)) or
                 (loc not in new_enemiesl and
                  enemy.hp <= self._high_player_damage_at_loc(loc, turn-1)))]
            # Check moved to a place without an enemy there.
            # Lenient.
            # Not 100% sure since another enemy could have moved here as well
            if any(loc for loc in moved_locs if
                   loc not in old_enemiesl):
                self._add_reconstructed_action(enemy, self.moved)
                if loc not in new_enemiesl:
                    self._add_reconstructed_action(enemy, self.died_by_player)
                return
            # Check moved to a place with an enemy originally there.
            # Lenient.
            # Doesn't check to disallow two robots swapping places
            elif len(moved_locs) > 0:
                for loc in moved_locs:
                    self._analyze_enemy_move(old_enemiesl[loc])
                    if self.moved in self.reconstructed_info[loc].actions:
                        self._add_reconstructed_action(enemy, self.moved)
                        if loc not in new_enemiesl:
                            self._add_reconstructed_action(enemy,
                                                       self.died_by_player)
                        return
            # Else, for sure they did not move for sure.
            # Check x could have been killed. Lenient
            if enemy.hp <= self._high_player_damage_at_loc(enemyl, turn-1):
                self._add_reconstructed_action(enemy, self.died_by_player)
                return
            # Check x could have been killed by spawn reset. Lenient
            if ('spawn' in rg.loc_types(enemyl) and
                    turn % rg.settings.spawn_every == 1):
                self._add_reconstructed_action(enemy, self.died_by_spawn)
                return
            # Exhaused all lenient possibilities
            # Must have exploded then.
            self._add_reconstructed_action(enemy, self.exploded)
        # An enemy still in that location
        else:
            # Either this enemy moved, and another enemy moved here.
            self._add_reconstructed_action(enemy, self.moved)
            # Or this enemy guarded.
            # Can be more strict. check dmg/hp
            self._add_reconstructed_action(enemy, self.guarded)

    def _analyze_enemy_moves(self):
        for x in self.enemies(self.current_turn - 1):
            self._analyze_enemy_move(x)

    def _analyze_explosions(self):
        turn = self.current_turn
        old_enemiesl = {x.location: x for x in self.enemies(turn-1)}

        # Players to examine are non-exploding ones.
        old_players = [y for y in self.players(turn-1) if
                   y.location not in self.turns[turn-1].explode_locs]
        new_players_id = {y.robot_id: y for y in self.players(turn)}

        # Find players hit with abnormal damage, or 7 w/ guarding
        for y in old_players:
            num_nearby_enemies = sum (1 for loc in rg.locs_around(y.location)
                                      if loc in old_enemiesl)
            max_norm_dmg = 10*num_nearby_enemies
            new_hp = (new_players_id[y.robot_id].hp if
                        y.robot_id in new_players_id else 0)
            hp_diff = y.hp - new_hp
            guarded = y.location in self.turns[turn-1].guard_locs
            if ((hp_diff == 7 and guarded) or hp_diff > max_norm_dmg):
                print "{0} hit with {1} damage.".format(y, hp_diff)
                # find culprit(s)
                candidates = [old_enemiesl[loc] for loc in
                              rg.locs_around(y.location)
                              if loc in old_enemiesl]
                if len(candidates) == 1:
                    self._record_explosion_point(candidates[0])
                elif len(candidates) > 1:
                    for e in candidates:
                        l = e.location
                        if self.exploded in self.reconstructed_info[l].actions:
                            self._record_explosion_point(old_enemiesl[l])

    def _verify_explosion_predictions(self):
        t = self.current_turn
        old_enemiesl = {x.location: x for x in self.enemies(t-1)}
        for (loc, info) in self.predicted_info.iteritems():
            if not info.will_explode:  # check explosion predictions
                continue

            neighbours = len(filter_nearby(self.players(t-1), loc, 1))
            if self.exploded in self.reconstructed_info[loc].actions:
                print "Anticipated explosion at ", loc, " correctly! ({0}<={1}hp, {2} neighbour(s))".format(
                    old_enemiesl[loc].hp,
                    self.enemy_explode_hp_given_nrobots[neighbours],
                    neighbours)
            else: # False positive prediction
                print "False positive explosion prediction at ", loc, "({0}<={1}hp, {2} neighbour(s))".format(
                    old_enemiesl[loc].hp,
                    self.enemy_explode_hp_given_nrobots[neighbours],
                    neighbours)
                for i in range(neighbours, 5):
                    self.enemy_explode_hp_given_nrobots[i] -= max(
                        2, self.enemy_explode_hp_given_nrobots[i]*0.2)
                print "Lowering expectation to", self.enemy_explode_hp_given_nrobots[neighbours]

    def _record_explosion_point(self, enemy):
        # x exploded. record exploding hp given num neighbours
        turn = self.current_turn
        nplayers = sum(1 for _ in
                       filter_nearby(self.players(turn), enemy.location, 1))
        for i in range(nplayers, 5):
            self.enemy_explode_hp_given_nrobots[i] = max(
                self.enemy_explode_hp_given_nrobots[i], enemy.hp)
        print "guessed an explosion point ({0}+ neighbours) = {1}".format(
            nplayers, self.enemy_explode_hp_given_nrobots[nplayers])

    def _mark_enemies(self):
        # mark enemies predicted to explode
        for x in self.enemies():
            self.predicted_info[x.location].will_explode=self._will_explode(x)

        predicts = [x.location for x in self.enemies() if self.predicted_info[x.location].will_explode]
        if len(predicts) > 0:
            print "explosion predictions", predicts
    def _will_explode(self, enemy):
        nnearby = sum(1 for _ in filter_nearby(self.players(),
                                               enemy.location, 1))
        return enemy.hp <= self.enemy_explode_hp_given_nrobots[nnearby]

    # Inspect once per turn
    def inspect(self, game):
        if self.player_id is None:
            self.player_id = next(x.player_id for x in game.robots.values()
                                  if 'robot_id' in x)

        if game.turn not in self.turns:
            # print "inspecting turn", game.turn
            # Reset per turn variables
            self.current_turn = game.turn
            self.reconstructed_info = {}

            players = [x for x in game.robots.values() if
                       x.player_id == self.player_id]
            enemies = [x for x in game.robots.values() if
                       x.player_id != self.player_id]
            self.turns[game.turn] = TurnState(players=players,
                                                   enemies=enemies,
                                                   attack_locs=defaultdict(int),
                                                   move_locs=defaultdict(int),
                                                   explode_locs=defaultdict(int),
                                                   guard_locs=defaultdict(int)
                                                   )
            if game.turn > 1:
                # Analyze enemy's last moves
                self._analyze_enemy_moves()
                self._analyze_explosions()

                # Verify if our predictions were correct
                self._verify_explosion_predictions()

                # Make new predictions
                self.predicted_info = defaultdict(PredictedInfo)
                self._mark_enemies()

    def enemies(self, turn=None):
        if turn is None:
            turn = self.current_turn
        return self.turns[turn].enemies

    def players(self, turn=None):
        if turn is None:
            turn = self.current_turn
        return self.turns[turn].players

    def will_explode(self, enemy):
        return self.predicted_info[enemy.location].will_explode

    def record_attack(self, loc):
        self.turns[self.current_turn].attack_locs[loc] += 1

    def record_move(self, loc):
        self.turns[self.current_turn].move_locs[loc] += 1

    def record_explode(self, loc):
        self.turns[self.current_turn].explode_locs[loc] += 1

    def record_guard(self, loc):
        self.turns[self.current_turn].guard_locs[loc] += 1

    # not an absolute check, only is accurate for robots already processed
    def will_have_player(self, loc):
        return loc in self.turns[self.current_turn].move_locs


class Robot:
    GATHER = 0
    ATTACK = 1
    DEFEND = 2

    def __init__(self):
        self.allstate = {}
        self.intel = IntelUnit()

    def set_state(self, value):
        self.allstate[self.robot_id] = value

    def state(self):
        if self.robot_id not in self.allstate:
            self.set_state(self.GATHER)
        return self.allstate[self.robot_id]

    def is_empty_loc(self, game, loc):
        return (loc not in game.robots
                and 'obstacle' not in rg.loc_types(loc)
                and 'invalid' not in rg.loc_types(loc)
                and ('spawn' not in rg.loc_types(loc) or game.turn % 10 != 0)
                and not self.intel.will_have_player(loc))

    def confident_dmg(self):
        (low, high) = rg.settings.attack_range
        return math.ceil(low + (high-low)*0.9)  # range 8-10, so prob returns 10

    def is_safe_from_attacks(self, game, loc):
        enemy_locs = [x.location for x in self.intel.enemies()]
        for p in rg.locs_around(loc):
            if p in enemy_locs:
                return False
        return True

    def is_in_danger(self, game):
        enemy_locs = [x.location for x in self.intel.enemies()]
        return any([loc in enemy_locs for loc in rg.locs_around(self.location)])

    def is_near(self, loc, dist):
        return rg.wdist(self.location, loc) <= dist

    # Returns list of possible next dirs to reach dest location
    def towards(self, dest):
        (x, y) = self.location
        locs = []
        if dest[0] < x:
            locs += [(x-1, y)]
        if dest[0] > x:
            locs += [(x+1, y)]
        if dest[1] < y:
            locs += [(x, y-1)]
        if dest[1] > y:
            locs += [(x, y+1)]

        # filter invalid ones
        locs = [l for l in locs if ('invalid' not in rg.loc_types(l) and
                                    'obstacle' not in rg.loc_types(l))]

        # short hack to control which dir to try first
        if abs(dest[0] - x) < abs(dest[1] - y):
            return list(reversed(locs))
        else:
            return locs

    def neighbours_exploding(self):
        return [x for x in filter_nearby(self.intel.enemies(), self.location, 1)
                if self.intel.will_explode(x)]

    # First hp below which expected value of attack < value of explode
    # (1,9,14)(2,19,29)(3,28,37)(4,37,57)
    def should_explode_over_attack(self):
        targets = self.intel.enemies()
        targets = [x for x in targets if
                   rg.wdist(self.location, x.location) == 1]
        return ((len(targets) == 1 and self.hp <= 9 and targets[0].hp > 8) or
                (len(targets) == 2 and self.hp <= 19) or
                (len(targets) == 3 and self.hp <= 28) or
                (len(targets) == 4 and self.hp <= 37))

    def process_switches(self, game):
        if self.state() == self.GATHER:
            if self.is_in_danger(game):
                self.set_state(self.ATTACK)
            elif self.is_near(rg.CENTER_POINT, 3):  # bad switch, change
                self.set_state(self.DEFEND)
        if self.state() == self.ATTACK:
            if not self.is_in_danger(game):
                self.set_state(self.GATHER)
        if self.state() == self.DEFEND:
            pass  # TODO

    def process_gather_state(self, game):
        next_locs = self.towards(rg.CENTER_POINT)
        for loc in next_locs:
            if self.is_empty_loc(game, loc):
                if self.is_safe_from_attacks(game, loc):
                    return ['move', loc]

        self.set_state(self.ATTACK)  # crucial, was why kept trying to walk

    def try_parry(self, game, spawn_points_ok=False):
        safe_locs = [x for x in rg.locs_around(self.location) if
                     (self.is_empty_loc(game, x) and
                      self.is_safe_from_attacks(game, x) and
                      (spawn_points_ok or 'spawn' not in rg.loc_types(x)))]
        if len(safe_locs) > 0:
            return ['move', random.choice(safe_locs)]
        else:
            return False

    # next turn spawn resets
    def is_spawn_reset(self, game):
        return game.turn % 10 == 0

    def turns_after_last_spawn(self, game):
        return (game.turn-1) % 10

    # todo. some improvement here.. is it better to try to find way around
    # or just run into enemy fire?
    def escape_spawn_trap_move(self, game):
        if 'spawn' in rg.loc_types(self.location):
            locs = [x for x in rg.locs_around(self.location) if
                    self.is_empty_loc(game, x)]
            free_locs = [x for x in locs if 'spawn' not in rg.loc_types(x)]
            safe_locs = [x for x in locs if self.is_safe_from_attacks(game, x)]
            safe_and_free_locs = [x for x in free_locs if x in safe_locs]

            # Try moving away first, even if may get hit.
            if len(safe_and_free_locs) > 0:
                return ['move', random.choice(safe_and_free_locs)]
            elif len(safe_locs) > 0:
                return ['move', random.choice(safe_locs)]
            elif len(free_locs) > 0:
                return ['move', random.choice(free_locs)]
            elif len(locs) > 0:
                return ['move', random.choice(locs)]
            # No where to move.
            else:
                # Todo: for friendlies, can tell them to gtfo out lol.
                # Todo: find a route, instead of just moving back n forth lol

                # Gonna die anyways, explode and cause some damage!
                # Enemies likely to guard. Some may move but hard to tell.
                if self.is_spawn_reset(game):
                    return ['suicide']
                # Else, go to some other behaviour
                return False

    def process_attack_state(self, game):
        # Try parry from predicted explosion
        dangers = {x.location: x for x in self.neighbours_exploding()}
        if len(dangers) > 0:
            res = self.try_parry(game, spawn_points_ok=True)
            return res if res else ['guard']

        # Try escape from spawn reset
        res = self.escape_spawn_trap_move(game)
        if res:
            return res

        # Combat-mode
        targets = self.intel.enemies()
        targets = [x for x in targets if
                   rg.wdist(self.location, x.location) == 1]
        targets.sort(lambda x, y: cmp(x.hp, y.hp))

        # 1 block away targets (in combat)
        if len(targets) > 0:
            # try parry if may die or getting double-team'd and can't kill
            # opponent
            if ((len(targets) == 1 and self.hp <= 10 and targets[0].hp > 9) or
                (len(targets) > 1 and any(x for x in targets if x.hp > 15))):
                    res = self.try_parry(game, spawn_points_ok=False)
                    if res:
                        return res

            # explode or attack decision
            if self.should_explode_over_attack():
                return ['suicide']
            else:
                return ['attack', targets[0].location]

        # TODO: team up attacks

        # 2 block away targets
        targets = self.intel.enemies()
        targets = [x for x in targets if
                   rg.wdist(self.location, x.location) == 2]
        targets.sort(lambda x, y: cmp(x.hp, y.hp))
        for x in targets:
            # Can hit predicted loc 1? (towards center)
            predicted_loc = rg.toward(x.location, rg.CENTER_POINT)
            if rg.wdist(self.location, predicted_loc) == 1:
                return ['attack', predicted_loc]

            # Try predicted loc 2 (towards robot)
            predicted_loc = self.towards(x.location)[0]
            return ['attack', predicted_loc]

        # for later, if want to coordinate attacks from afar
        # targets.sort(lambda x, y: cmp(rg.wdist(self.location,x.location),
        # rg.wdist(self.location,y.location)))

        return ['guard']

    def record_result(self, res):
        if res[0] == 'attack':
            self.intel.record_attack(res[1])
        elif res[0] == 'suicide':
            self.intel.record_explode(self.location)
        elif res[0] == 'move':
            self.intel.record_move(res[1])
        elif res[0] == 'guard':
            self.intel.record_move(self.location)
            self.intel.record_guard(self.location)
        else:
            pass  # no result yet

    def act(self, game):
        self.intel.inspect(game)

        # Switches
        self.process_switches(game)

        if self.state() == self.GATHER:
            res = self.process_gather_state(game)
            if res is not None:
                self.record_result(res)
                return res

        if self.state() == self.ATTACK or self.state() == self.DEFEND:
            res = self.process_attack_state(game)
            if res is not None:
                self.record_result(res)
                return res

        # predict explode and dodge. remember for next time.


# Helper functions
def filter_nearby(robots, loc, dist=1):
    return [x for x in robots if rg.wdist(loc, x.location) == dist]
