"""
Release thread:
http://www.buildandshoot.com/viewtopic.php?t=2586

How to install and configure:

1) Save babel_script.py to 'scripts' folder: http://aloha.pk/files/aos/pyspades/feature_server/scripts/babel_script.py
2) Save babel.py to 'scripts' folder: http://aloha.pk/files/aos/pyspades/feature_server/scripts/babel.py
3) Set game_mode to "babel" in config.txt
4) Add "babel_script" to scripts list in config.txt
5) Set cap_limit to "10" in config.txt

Mapname.txt support:
Optionally you can set the extension 'babel' : True so ALWAYS_ENABLED can be false (see below).
Use 'heavens_color' : (250, 130, 40, 255) for custom  heavens color with format R,G,B,255 (each range 0 to 255)
Use  fog = (190, 120, 60) (not an extension) to set map fog color.  RGB 0 to 255
Use the get_spawn_location and get_entity_location methods for team and tent spawns. Intel spawns will be ignored.

Example:
----------------------------------------------------------------------------------
name = 'Ellipsis'
version = '1.3'
author = 'ei8htx'
description = ('Now with more scripting!')
extensions = { 
	'water_damage' : 8,
	'babel' : True, 
	'heavens_color' : (250, 130, 40, 255)
}

fog = (150, 255, 255)

AREA = (98, 236, 374, 276,) #blue x1, both y1, green x1, both y2
WIDTH = 40
BLUE_RECT =  (AREA[0], AREA[1], AREA[0]+WIDTH, AREA[3]) #x1, y1, x2, y2
GREEN_RECT = (AREA[2], AREA[1], AREA[2]+WIDTH, AREA[3])

from pyspades.constants import *
from pyspades.server import ServerConnection

def get_spawn_location(connection):
	if connection.team is connection.protocol.blue_team:
		return connection.protocol.get_random_location(True, BLUE_RECT)
	elif connection.team is connection.protocol.green_team:
		return connection.protocol.get_random_location(True, GREEN_RECT)
 
def get_entity_location(team, entity_id):
	if entity_id == GREEN_BASE:
		return (256+138, 256, team.protocol.map.get_z(256+138, 256))
	if entity_id == BLUE_BASE:
		return (256-138, 256, team.protocol.map.get_z(256-138, 256))		

----------------------------------------------------------------------------------

Changelog:
Original script by Yourself
Anti grief by izzy
Return intel dropped from platform bug fix by a_girl

23 July 2014 - ei8htx
Fixed new map starting with custom fog (finally!)
Added in support for mapname.txt team and tent spawns
Re-added BR's lost green team heavens block proximity thing
Extension added for custom heavens color.


"""

from pyspades.constants import *
from random import randint
from twisted.internet import reactor
import commands

# If ALWAYS_ENABLED is False, then babel can be enabled by setting 'babel': True
# in the map metadat extensions dictionary.
ALWAYS_ENABLED = True

PLATFORM_WIDTH = 100
PLATFORM_HEIGHT = 32
PLATFORM_COLOR = (0, 255, 255, 255)
BLUE_BASE_COORDS = (256-138, 256)
GREEN_BASE_COORDS = (256+138, 256)
SPAWN_SIZE = 40

# Don't touch this stuff <- I touch ur mom.
PLATFORM_WIDTH /= 2
PLATFORM_HEIGHT /= 2
SPAWN_SIZE /= 2

def get_entity_location(self, entity_id):
	if entity_id == BLUE_FLAG:
		return (256 - PLATFORM_WIDTH + 1, 256, 0)
	elif entity_id == GREEN_FLAG:
		return (256 + PLATFORM_WIDTH - 1, 256, 0)
	elif entity_id == BLUE_BASE:
		return BLUE_BASE_COORDS + (self.protocol.map.get_z(*BLUE_BASE_COORDS),)
	elif entity_id == GREEN_BASE:
		return GREEN_BASE_COORDS + (self.protocol.map.get_z(*GREEN_BASE_COORDS),)

		
def get_intel_location(self, entity_id):
	if entity_id == BLUE_FLAG:
		return (256 - PLATFORM_WIDTH + 1, 256, 0)
	elif entity_id == GREEN_FLAG:
		return (256 + PLATFORM_WIDTH - 1, 256, 0)
	else: #passing the tent stuff to the mapname.txt file
		return self.protocol.map_info.info.get_entity_location(self, entity_id)

def get_spawn_location(connection):
	xb = connection.team.base.x
	yb = connection.team.base.y
	xb += randint(-SPAWN_SIZE, SPAWN_SIZE)
	yb += randint(-SPAWN_SIZE, SPAWN_SIZE)
	return (xb, yb, connection.protocol.map.get_z(xb, yb))

def coord_on_platform(x, y, z):
	if z <= 2:
		if x >= (256 - PLATFORM_WIDTH) and x <= (256 + PLATFORM_WIDTH - 1) and y >= (256 - PLATFORM_HEIGHT) and y <= (256 + PLATFORM_HEIGHT - 1):
			return True
	if z == 1:
		if x >= (256 - PLATFORM_WIDTH - 1) and x <= (256 + PLATFORM_WIDTH) and y >= (256 - PLATFORM_HEIGHT - 1) and y <= (256 + PLATFORM_HEIGHT):
			return True
	return False

def apply_script(protocol, connection, config):
	allowed_intel_hold_time = config.get('allowed_intel_hold_time', 150)
	class TowerOfBabelConnection(connection):
		def invalid_build_position(self, x, y, z):
			if not self.god and self.protocol.babel:
				if coord_on_platform(x, y, z):
					connection.on_block_build_attempt(self, x, y, z)
					return True
			# prevent enemies from building in protected areas
			if self.team is self.protocol.blue_team:
				if self.world_object.position.x >= 301 and self.world_object.position.x <= 384 and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
					self.send_chat('You can\'t build near the enemy\'s tower!')
					return True
			if self.team is self.protocol.green_team:
				if self.world_object.position.x >= 128 and self.world_object.position.x <= 211 and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
					self.send_chat('You can\'t build near the enemy\'s tower!')
					return True
			return False

		def on_block_build_attempt(self, x, y, z):
			if self.invalid_build_position(x, y, z):
				return False
			return connection.on_block_build_attempt(self, x, y, z)

		def on_line_build_attempt(self, points):
			for point in points:
				if self.invalid_build_position(*point):
					return False
			return connection.on_line_build_attempt(self, points)

		# anti team destruction
		def on_block_destroy(self, x, y, z, mode):
			if self.team is self.protocol.blue_team:
				if not (self.admin or self.user_types.moderator or self.user_types.guard or self.user_types.trusted) and self.tool is SPADE_TOOL and self.world_object.position.x >= 128 and self.world_object.position.x <= 211 and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
					self.send_chat('You can\'t destroy your team\'s blocks in this area. Attack the enemy\'s tower!')
					return False
				if self.world_object.position.x <= 288:
					if self.tool is WEAPON_TOOL:
						self.send_chat('You must be closer to the enemy\'s base to shoot blocks!')
						return False
					if mode is GRENADE_DESTROY:
						self.send_chat('You must be closer to the enemy\'s base to grenade blocks!')
						return False
			if self.team is self.protocol.green_team:
				if not (self.admin or self.user_types.moderator or self.user_types.guard or self.user_types.trusted) and self.tool is SPADE_TOOL and self.world_object.position.x >= 301 and self.world_object.position.x <= 384 and self.world_object.position.y >= 240 and self.world_object.position.y <= 272:
					self.send_chat('You can\'t destroy your team\'s blocks in this area. Attack the enemy\'s tower!')
					return False
				if self.world_object.position.x >= 224:
					if self.tool is WEAPON_TOOL:
						self.send_chat('You must be closer to the enemy\'s base to shoot blocks!')
						return False
					if mode is GRENADE_DESTROY:
						self.send_chat('You must be closer to the enemy\'s base to grenade blocks!')
						return False
			return connection.on_block_destroy(self, x, y, z, mode)

		auto_kill_intel_hog_call = None

		# kill intel carrier if held too long
		def auto_kill_intel_hog(self):
			self.auto_kill_intel_hog_call = None
			self.kill()
			self.protocol.send_chat('God punished %s for holding the intel too long' % (self.name))

		def restore_default_fog_color(self):
			self.protocol.set_fog_color(getattr(self.protocol.map_info.info, 'fog', (128, 232, 255)))

		def on_flag_take(self):
			if self.auto_kill_intel_hog_call is not None:
				self.auto_kill_intel_hog_call.cancel()
				self.auto_kill_intel_hog_call = None
			self.auto_kill_intel_hog_call = reactor.callLater(allowed_intel_hold_time, self.auto_kill_intel_hog)
			# flash team color in sky
			if self.team is self.protocol.blue_team:
				self.protocol.set_fog_color((0, 0, 255))
			if self.team is self.protocol.green_team:
				self.protocol.set_fog_color((0, 255, 0))
			reactor.callLater(0.25, self.restore_default_fog_color)
			return connection.on_flag_take(self)

		# return intel to platform if dropped
		def on_flag_drop(self):
			x, y, z = self.world_object.position.x, self.world_object.position.y, self.world_object.position.z
			if self.auto_kill_intel_hog_call is not None:
				self.auto_kill_intel_hog_call.cancel()
				self.auto_kill_intel_hog_call = None
			if z >= 0:
				self.reset_flag()
			elif (x >= (256 + PLATFORM_WIDTH)) or (x < (256 - PLATFORM_WIDTH)):
				self.reset_flag()
			elif (y >= (256 + PLATFORM_HEIGHT)) or (y < (256 - PLATFORM_HEIGHT)):
				self.reset_flag()
			self.protocol.set_fog_color((255, 0, 0))
			reactor.callLater(0.25, self.restore_default_fog_color)
			return connection.on_flag_drop(self)
			
		def reset_flag(self):
			self.protocol.onectf_reset_flags()
			self.protocol.send_chat('The intel has returned to the heavens')

		def on_flag_capture(self):
			if self.auto_kill_intel_hog_call is not None:
				self.auto_kill_intel_hog_call.cancel()
				self.auto_kill_intel_hog_call = None
			return connection.on_flag_capture(self)

		def on_reset(self):
			if self.auto_kill_intel_hog_call is not None:
				self.auto_kill_intel_hog_call.cancel()
				self.auto_kill_intel_hog_call = None
			return connection.on_reset(self)

	class TowerOfBabelProtocol(protocol):
		babel = False
		def on_map_change(self, map):
			extensions = self.map_info.extensions
			if ALWAYS_ENABLED:
				self.babel = True
			else:
				if extensions.has_key('babel'):
					self.babel = extensions['babel']
				else:
					self.babel = False
			if self.babel:
				self.map_info.cap_limit = 1
				#prioritizing the mapname.txt spawn and tent locations over inbuilt
				#print "%s ", getattr(self.map_info.info, 'get_entity_location', None)
				if getattr(self.map_info.info, 'get_entity_location', None) == None:
					self.map_info.get_entity_location = get_entity_location
				else:
					self.map_info.get_entity_location = get_intel_location
				if getattr(self.map_info.info, 'get_spawn_location', None) == None:
					self.map_info.get_spawn_location = get_spawn_location
				for x in xrange(256 - PLATFORM_WIDTH, 256 + PLATFORM_WIDTH):
					for y in xrange(256 - PLATFORM_HEIGHT, 256 + PLATFORM_HEIGHT):					
						if extensions.has_key('heavens_color'):
							map.set_point(x, y, 1, extensions['heavens_color'])
						else:
							map.set_point(x, y, 1, PLATFORM_COLOR)
			self.set_fog_color(getattr(self.map_info.info, 'fog', (128, 232, 255)))
			return protocol.on_map_change(self, map)
		
		def is_indestructable(self, x, y, z):
			if self.babel:
				if coord_on_platform(x, y, z):
					protocol.is_indestructable(self, x, y, z)
					return True
			return protocol.is_indestructable(self, x, y, z)

	return TowerOfBabelProtocol, TowerOfBabelConnection
