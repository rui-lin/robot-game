import rg
import math
import random
from collections import namedtuple, defaultdict

TurnState = namedtuple("TurnState", "players enemies attack_locs move_locs " +
                                    "explode_locs guard_locs")
EnemyInfo = namedtuple("EnemyInfo", "will_explode")


# Assumes max 4 units 'beside' a robot (north south east west)
class IntelUnit:
    def __init__(self):
        self.game_turns = {}
        self.enemy_explode_hp_given_nrobots = [0] * 5
        self.player_id = None

        # Per turn variables
        self.current_turn = -1
        self.enemy_info = defaultdict(EnemyInfo)

    def _analyze_explosions(self):
        # Method 1.
        # Tested, cannot move into a location of exploding robot
        # So find locations where enemy robots disappeared.
        # Now they've either moved, got hit by me, or exploded
        # Check possible move locations to see if candidate robot is there
        # Check if I could've destroyed it already.
        # TODO: check if there was orginally a robot there, if it moved
        # somewhere. bit complicated recursion, can't backtrace 1 but more
        # is ok.
        turn = self.current_turn
        enemies_by_loc = {x.location: x for x in self.enemies(turn)}
        players_by_id = {x.robot_id: x for x in self.players(turn)}
        candidates = [x for x in self.enemies(turn-1) if
                      x.location not in enemies_by_loc]
        for x in candidates:
            # any players nearby that got damaged exactly 7 or 15?
            # (and this enemy was only possibility responsible). exploded
            nearby_players = filter_nearby(self.players(turn-1), x.location)
            for y in nearby_players:
                # player explosion caused the damage
                if y.location in self.game_turns[turn-1].explode_locs:
                    continue
                nearby_enemies = filter_nearby(self.enemies(turn-1), y.location,
                                               1)
                nearby_enemies_after = filter_nearby(self.enemies(turn),
                                                     y.location, 1)
                # exactly one enemy exploded around this player
                if len(nearby_enemies) - len(nearby_enemies_after) != 1:
                    continue

                max_norm_dmg = 10*len(nearby_enemies)
                new_hp = (players_by_id[y.robot_id].hp if
                          y.robot_id in players_by_id else 0)
                hp_diff = y.hp - new_hp
                guarded = y.location in self.game_turns[turn].guard_locs
                if ((hp_diff == 7 and guarded) or hp_diff > max_norm_dmg):
                    print "exact dmg discovery"
                    self._record_explosion_point(x)
                    break

            # x could have moved and is alive
            moved_locs = filter_nearby(self.enemies(turn), x.location,
                                       1)
            moved_locs = [x for x in moved_locs if
                          (x.location in enemies_by_loc and
                           enemies_by_loc[x.location].hp <= x.hp)]
            if len(moved_locs) > 0:
                continue

            # x could have moved and got killed at new loc
            for loc in rg.locs_around(x.location):
                if x.hp <= (self.game_turns[turn-1].attack_locs[loc]*10 +
                            self.game_turns[turn-1].explode_locs[loc]*15):
                    continue

            # x could have been killed, so skip
            # (or it could have moved)
            if x.hp <= (self.game_turns[turn-1].attack_locs[x.location]*10 +
                        self.game_turns[turn-1].explode_locs[x.location]*15):
                continue

            # x could have been killed by spawn reset
            if ('spawn' in rg.loc_types(x.location) and
                    turn % rg.settings.spawn_every == 1):
                continue

            # possibilities exhausted, x must have exploded
            self._record_explosion_point(x)

    def _record_explosion_point(self, enemy):
        # x exploded. record exploding hp given num neighbours
        turn = self.current_turn
        nplayers = sum(1 for _ in
                       filter_nearby(self.players(turn), enemy.location, 1))
        self.enemy_explode_hp_given_nrobots[nplayers] = max(
            self.enemy_explode_hp_given_nrobots[nplayers], enemy.hp)
        print("guessed an explosion point (", nplayers, "neighbours) = ",
              self.enemy_explode_hp_given_nrobots[nplayers])

    def _analyze_enemies(self):
        # predict when they explode.
        turn = self.current_turn
        if turn > 1:
            self._analyze_explosions()

    def _mark_enemies(self):
        # mark enemies predicted to explode
        for x in self.enemies():
            self.enemy_info[x.location] = EnemyInfo(
                will_explode=self._will_explode(x))

    def _will_explode(self, enemy):
        nnearby = sum(1 for _ in filter_nearby(self.players(),
                                               enemy.location, 1))
        return enemy.hp <= self.enemy_explode_hp_given_nrobots[nnearby]

    # Inspect once per turn
    def inspect(self, game):
        if self.player_id is None:
            self.player_id = next(x.player_id for x in game.robots.values()
                                  if 'robot_id' in x)

        if game.turn not in self.game_turns:
            print "inspecting turn", game.turn
            # Reset per turn variables
            self.current_turn = game.turn
            self.enemy_info = defaultdict(EnemyInfo)

            players = [x for x in game.robots.values() if
                       x.player_id == self.player_id]
            enemies = [x for x in game.robots.values() if
                       x.player_id != self.player_id]
            self.game_turns[game.turn] = TurnState(players=players,
                                                   enemies=enemies,
                                                   attack_locs=defaultdict(int),
                                                   move_locs=defaultdict(int),
                                                   explode_locs=defaultdict(int),
                                                   guard_locs=defaultdict(int)
                                                   )
            self._analyze_enemies()
            self._mark_enemies()

    def enemies(self, turn=None):
        if turn is None:
            turn = self.current_turn
        return self.game_turns[turn].enemies

    def players(self, turn=None):
        if turn is None:
            turn = self.current_turn
        return self.game_turns[turn].players

    def will_explode(self, enemy):
        return self.enemy_info[enemy.location].will_explode

    def record_attack(self, loc):
        self.game_turns[self.current_turn].attack_locs[loc] += 1

    def record_move(self, loc):
        self.game_turns[self.current_turn].move_locs[loc] += 1

    def record_explode(self, loc):
        for loc in rg.locs_around(loc) + [loc]:
            self.game_turns[self.current_turn].explode_locs[loc] += 1

    def record_guard(self, loc):
        self.game_turns[self.current_turn].guard_locs[loc] += 1

    # not an absolute check, only is accurate for robots already processed
    def will_have_player(self, loc):
        return loc in self.game_turns[self.current_turn].move_locs


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

        # short hack to control which dir to try first
        if abs(dest[0] - x) < abs(dest[1] - y):
            return list(reversed(locs))
        else:
            return locs

    def neighbours_exploding(self):
        return [x for x in filter_nearby(self.intel.enemies(), self.location, 1)
                if self.intel.will_explode(x)]

    def process_switches(self, game):
        if self.state() == self.GATHER:
            if self.is_in_danger(game):
                self.set_state(self.ATTACK)
            elif self.is_near(rg.CENTER_POINT, 3):  # bad switch, change
                self.set_state(self.DEFEND)
        elif self.state() == self.ATTACK:
            if not self.is_in_danger(game):
                self.set_state(self.GATHER)
        elif self.state() == self.DEFEND:
            pass  # TODO

    def process_gather_state(self, game):
        next_locs = self.towards(rg.CENTER_POINT)
        for loc in next_locs:
            if self.is_empty_loc(game, loc):
                if self.is_safe_from_attacks(game, loc):
                    return ['move', loc]

        self.set_state(self.ATTACK)  # crucial, was why kept trying to walk

    def process_attack_state(self, game):
        # TODO: team up attacks

        # parry if needed
        dangers = {x.location: x for x in self.neighbours_exploding()}
        if len(dangers) > 0:
            safe_locs = [x for x in rg.locs_around(self.location) if
                         (x not in dangers and self.is_empty_loc(game, x) and
                         self.is_safe_from_attacks(game, x))]
            if len(safe_locs) > 0:
                return ['move', random.choice(safe_locs)]
            else:
                return ['guard']

        # normal attack
        targets = self.intel.enemies()
        targets = [x for x in targets if
                   rg.wdist(self.location, x.location) == 1]
        targets.sort(lambda x, y: cmp(x.hp, y.hp))
        # for later, if want to coordinate attacks from afar
        # targets.sort(lambda x, y: cmp(rg.wdist(self.location,x.location),
        # rg.wdist(self.location,y.location)))

        if len(targets) > 0:
            if (len(targets) == 1 and self.hp <= rg.settings.attack_range[1] and
                    targets[0].hp > rg.settings.attack_range[0]):
                return ['suicide']

            # rough, hard for opponent to guess. need to count diag robots too
            if (len(targets) > 1 and
                    self.hp < len(targets)*(rg.settings.suicide_damage*0.9)):
                return ['suicide']

            return ['attack', targets[0].location]

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
