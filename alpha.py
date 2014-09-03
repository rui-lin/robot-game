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
            next_loc = rg.toward(self.location, rg.CENTER_POINT)
            if self.is_empty_loc(game, next_loc):  # try move to other dir
                if self.is_safe_from_attacks(game, next_loc):
                        return ['move', next_loc]

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

            return ['guard'] # prob won't happen

            # predict suicide and dodge. remember for next time.

