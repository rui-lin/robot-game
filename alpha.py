import rg
import math

# started 11am
class Robot:
    GATHER = 0
    ATTACK = 1
    DEFEND = 2
    SUICIDE_DMG = 15

    def __init__(self):
        self.allstate = {}

    def set_state(self, value):
        self.allstate[self.robot_id] = value

    def state(self):
        if self.robot_id not in self.allstate:
                self.set_state(self.GATHER)
        return self.allstate[self.robot_id]

    def enemy_robots(self, game):
        return [x for x in game.robots.values() if x.player_id != self.player_id]

    def player_robots(self, game):
        return [x for x in game.robots.values() if x.player_id == self.player_id]

    def is_empty_loc(self, game, loc):
        return loc not in game.robots and 'obstacle' not in rg.loc_types(loc)

    def confident_dmg(self):
        (low,high) = rg.settings.attack_range
        return math.ceil(low + (high-low)*0.9) # range 8-10, so prob returns 10.

    def is_safe_from_attacks(self, game, loc):
        enemy_locs = [x.location for x in self.enemy_robots(game)]
        for p in rg.locs_around(loc):
            if p in enemy_locs:
		print "not safe", self.location, "to", loc, "cuz of",p
                return False
        return True

    def is_in_danger(self,game):
	enemy_locs = [x.location for x in self.enemy_robots(game)]
        return any([loc in enemy_locs for loc in rg.locs_around(self.location)])

    def is_near(self, loc, dist):
        return rg.wdist(self.location, loc) <= dist

    # Returns list of possible next dirs to reach dest location
    def towards(self, dest):
        (x,y) = self.location
        locs = []
        if dest[0] < x:
          locs += [(x-1,y)]
        if dest[0] > x:
          locs += [(x+1,y)]
        if dest[1] < y:
          locs += [(x, y-1)]
        if dest[1] > y:
          locs += [(x, y+1)]
        # short hack to control which dir to try first
        if abs(dest[0] - x) < abs(dest[1] - y):
          return reversed(locs)
        else:
          return locs

    def act(self, game):
        # Switches
        if self.state() == self.GATHER:
            if self.is_in_danger(game):
                self.set_state(self.ATTACK)
            if self.is_near(rg.CENTER_POINT,3): # bad switch, change
                self.set_state(self.DEFEND)
        if self.state() == self.ATTACK:
            if not self.is_in_danger(game):
                self.set_state(self.GATHER)
        if self.state() == self.DEFEND:
            pass #hey

        # not sure why bump collisions aren't always detected
        # fix two same robots trying to move to center
        if self.state() == self.GATHER:
            next_locs = self.towards(rg.CENTER_POINT)
            for loc in next_locs:
                if self.is_empty_loc(game, loc):
                    if self.is_safe_from_attacks(game, loc):
                        return ['move', loc]

            self.set_state(self.ATTACK) # crucial, was why kept trying to walk

        if self.state() == self.ATTACK or self.state() == self.DEFEND:
            # team up attacks
            # normal attack
            targets = self.enemy_robots(game)
            targets = [x for x in targets if rg.wdist(self.location, x.location) == 1]
            targets.sort(lambda x,y: cmp(x.hp,y.hp))
            # for later, if want to coordinate attacks from afar
            #targets.sort(lambda x,y: cmp(rg.wdist(self.location,x.location),rg.wdist(self.location,y.location)))

            if len(targets) > 0: # shouldn't happen with current switches. may change later.
                if len(targets) == 1 and self.hp <= rg.settings.attack_range[1] and targets[0].hp > rg.settings.attack_range[0]:
                    return ['suicide']
                # rough, so hard for opponent to guess. need to count diag robots too
                if len(targets) > 1 and self.hp < len(targets)*(self.SUICIDE_DMG*0.9):
                    return ['suicide']

                return ['attack', targets[0].location]

            # 2 block away targets
            targets = self.enemy_robots(game)
            targets = [x for x in targets if rg.wdist(self.location, x.location) == 1]
            targets.sort(lambda x,y: cmp(x.hp,y.hp))
            for x in targets:
               predicted_loc = rg.toward(x.location,rg.CENTER_POINT)
               if rg.wdist(self.location, predicted_loc) == 1: # can hit it
                  return ['attack', predicted_loc]

            return ['guard']

            # predict suicide and dodge. remember for next time.

