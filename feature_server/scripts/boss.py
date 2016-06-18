"""
Boss game mode

Maintainer: Triplefox
"""

from pyspades.constants import *
from pyspades.server import orientation_data, weapon_reload
import random
import math
import commands

BOSS_TEAM = 1
PLEBS_TEAM = 0
PLAYERS_NEEDED = 1

def apply_script(protocol, connection, config):
    class BossConnection(connection):
        isBoss = False
        bossHP = 0
        firstJoin = True

        def makeBoss(self):
            playerCount = self.protocol.playerCount
            bossTeam = self.protocol.bossTeam
            self.isBoss = True
            self.bossHP = playerCount * 1000
            self.set_team(bossTeam)
            self.protocol.bossModeRunning = True

        def on_team_join(self, team):
            if self.firstJoin:
                self.protocol.playerCount += 1
                playerCount = self.protocol.playerCount
                self.protocol.connections[playerCount] = self
                self.firstJoin = False
            bossTeam = self.protocol.bossTeam
            if team is bossTeam:
                self.send_chat('Can`t join boss team, boss is choosen automatically')
                return False
            connection.on_team_join(self, team)

        def on_spawn(self, position):
            if self.isBoss:
                self.clear_ammo()
            connection.on_spawn(self, position)

        def on_reset(self):
            playerCount = self.protocol.playerCount
            playerCount = playerCount - 1
            connection.on_reset(self)
        
        def on_kill(self, killer, type, grenade):
            if self.isBoss and self.protocol.bossModeRunning:
                self.protocol.send_chat('BOSS IS KILLED. CHOOSING NEW BOSS.')
                self.protocol.bossModeRunning = False
            return  connection.on_kill(self, killer, type, grenade)

        def on_hit(self, hit_amount, hit_player, type):
            if hit_player.isBoss and hit_player.bossHP:
                hit.player.bossHP -= hit_amount
                return False
            connection.on_hit(self, hit_amount, hit_player, type)

        def on_refill(self):
            if self.isBoss:
                weapon_reload.player_id = self.player_id
                weapon_reload.clip_ammo = self.weapon_object.current_ammo
                weapon_reload.reserve_ammo = self.weapon_object.current_stock
                self.send_contained(weapon_reload)
                self.weapon_object.reload()
            return connection.on_refill(self)

        # clear_ammo() method by infogulch
        def clear_ammo(self):
            if self.isBoss:
                weapon_reload.player_id = self.player_id
                weapon_reload.clip_ammo = 0
                weapon_reload.reserve_ammo = 0
                self.grenades = 0
                self.blocks = 0
                self.weapon_object.clip_ammo = 0
                self.weapon_object.reserve_ammo = 0
                self.send_contained(weapon_reload)

    class BossProtocol(protocol):
        game_mode = CTF_MODE
        playerCount = 0
        connections = {}
        bossModeRunning = False
        bossTeam = None
        plebsTeam = None
        bossPlayerNumber = None
        timer = 0
        seconds = 0

        def on_world_update(self):
            self.timer += 1
            if self.timer is 60:
                self.seconds += 1
                self.timer = 0
                if (not (self.bossModeRunning)):
                    self.checkStartConditions()
                if self.seconds % 5 == 0:
                    if self.bossModeRunning:
                        self.send_chat('Boss HP is %s' % self.connections[self.bossPlayerNumber].bossHP)
            protocol.on_world_update(self)

        def on_map_change(self, map):
           self.bossTeam = self.green_team
           self.plebsTeam = self.blue_team
           protocol.on_map_change(self, map)

        def initializeBossMode(self):
            self.send_chat('Choosing new boss');
            self.bossPlayerNumber = int(math.floor(random.random() * (self.playerCount) + 1))
            self.connections[self.bossPlayerNumber].makeBoss()

        def checkStartConditions(self):
            if self.playerCount >= PLAYERS_NEEDED:
                if self.bossPlayerNumber:
                    self.connections[self.bossPlayerNumber].set_team(self.plebsTeam)
                    self.bossPlayerNumber = None
                self.initializeBossMode()

    return BossProtocol, BossConnection
