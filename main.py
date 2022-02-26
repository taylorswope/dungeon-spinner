"""
- Pick a random Link and place a Lock there
- Find valid rooms for the Key:
	- Start with the starting room and follow any unlocked links
	- When coming across a room with a Key, re-evaluate links from visited rooms
	- Continue until there are no more unlocked links
- Pick a random room from the set of valid rooms and place the Key there
"""

import random
import logging
import math
import os
os.system("color")

logging.basicConfig(
	level=logging.INFO,
	format="%(levelname)s %(asctime)-15s %(filename)s:%(lineno)d:%(message)s",
	filename="output.log",
	filemode="w"
)

KEY_NAMES = tuple("ZYXWVUTSRQPONMLKJIHGFEDCBA")

class Graph():
	def __init__(self):
		self.nodes = []
		self.links = []
		self.keys = []
		self.start_node = None
	
	def __str__(self):
		return "Graph (%s Nodes/%s Links)" % (len(self.nodes), len(self.links))
	
	def details(self):
		s = "Graph:"
		for n in self.nodes:
			s += "\n\t%s" % n
			if len(n.key_items) > 0:
				s += "\n\t\tKeys:"
				for k in n.key_items:
					s += "\n\t\t\t%s" % k
			s += "\n\t\tLinks:"
			for l in n.links:
				s += "\n\t\t\t%s" % l
		return s
	
	@classmethod
	def random_graph(cls,
		min_nodes=6,
		max_nodes=10,
		max_links_per_node=4,
		loopback_chance_from_none=0.1, # chance that a link will go to an existing node instead of a new one when coming from a region-less node
		loopback_chance_from_region=0.1, # chance that a link will go to an existing node instead of a new one when coming from an existing region
		lock_count=4,
		region_chance_from_none=0.4, # chance that a new node will introduce a new region when stemming from a region-less node
		region_chance_from_region=0.1 # chance that a new node will introuce a new region instead of continuing an existing region
	):
		graph = cls()
		next_node_id = 1
		start_node = graph.add_node(node_id=str(next_node_id))
		graph.set_start_node(start_node)
		next_node_id += 1
		node_count = random.randint(min_nodes, max_nodes)
		current_region = 1
		while len(graph.nodes) <= node_count:
			node_options = [n for n in graph.nodes if len(n.links) < max_links_per_node]
			current_node = random.choice(node_options)
			roll = random.random()
			if len(node_options) > 1 and ((current_node.region and roll < loopback_chance_from_region) or roll < loopback_chance_from_none):
				# link back to an existing node instead of making a new one
				linked_node = random.choice([n for n in node_options if n is not current_node])
				graph.link_nodes(current_node, linked_node)
			else:
				roll = random.random()
				if current_node.region:
					needed_roll = region_chance_from_region
				else:
					needed_roll = region_chance_from_none
				if roll < needed_roll:
					region = current_region
					current_region += 1
				else:
					region = current_node.region
				new_node = graph.add_node(node_id=str(next_node_id), region=region)
				next_node_id += 1
				graph.link_nodes(current_node, new_node)
		key_names = list(KEY_NAMES)
		## TODO -- assign keys to regions (maybe use number of nodes per region to make a probability distribution)
		for i in range(lock_count):
			key_item = KeyItem(key_names.pop())
			graph.place_key_item(key_item)
		return graph
		
	def add_node(self, node_id="null", region=None):
		new_node = Node(self, node_id, region=region)
		self.nodes.append(new_node)
		return new_node
	
	def set_start_node(self, node):
		assert node in self.nodes
		self.start_node = node
	
	def link_nodes(self, node1, node2, required_keys=None):
		assert node1 in self.nodes
		assert node2 in self.nodes
		new_link = Link(self, node1, node2, required_keys)
		self.links.append(new_link)
		node1.links.append(new_link)
		node2.links.append(new_link)
		if node1.region and node1.region == node2.region:
			new_link.region = node1.region
	
	def evaluate_link(self, link, available_keys):
		assert link in self.links
		for key in link.required_keys:
			if key not in available_keys: return False
		return True
	
	def get_available_nodes(self):
		assert self.start_node != None
		available_keys = []
		available_nodes = [self.start_node]
		finished = False
		while not finished:
			finished = True
			for node in available_nodes:
				# add any new keys to our key ring
				for key in node.key_items:
					if key not in available_keys:
						available_keys.append(key)
						finished = False
				# see if we can traverse any links
				for link in node.links:
					# if a link passes, check if its connected node is new
					if self.evaluate_link(link, available_keys):
						other_node = link.get_destination_node(node)
						if other_node not in available_nodes:
							# add the new node to our list and start over
							available_nodes.append(other_node)
							finished = False
				if not finished: break
		return available_nodes
	
	def place_key_item(self, key_item, try_again_on_failure=True):
		"""Places a lock on a valid link, then places the key for the lock in an accessible node."""
		link_options = [l for l in self.links if len(l.required_keys) < l.max_required_keys]
		if key_item.region:
			link_options = [l for l in link_options if l.region == key_item.region]
		while len(link_options) > 0:
			selected_link = random.choice(link_options)
			selected_link.add_required_key(key_item)
			node_options = [n for n in self.get_available_nodes() if len(n.key_items) < n.max_key_items]
			if len(node_options) > 0:
				selected_node = random.choice(node_options)
				selected_node.add_key_item(key_item)
				logging.info("Placed %s in %s for a lock on %s" % (key_item, selected_node, selected_link))
				self.keys.append(key_item)
				return True
			else:
				selected_link.remove_required_key(key_item)
				link_options.remove(selected_link)
				logging.info("Failed to place %s on %s" % (key_item, selected_link))
				if not try_again_on_failure: return False
		logging.info("Failed to place %s" % (key_item))
		return False
	
	def place_lock_for_key(self, key_item, try_again_on_failure=True):
		"""Places a lock for an already-placed key item. Meant for reusable keys."""
		link_options = [l for l in self.links if len(l.required_keys) < l.max_required_keys]
		if key_item.region:
			link_options = [l for l in link_options if l.region == key_item.region]
		while len(link_options) > 0:
			selected_link = random.choice(link_options)
			selected_link.add_required_key(key_item)
			available_nodes = self.get_available_nodes()
			if key_item.location in available_nodes:
				logging.info("Placed a lock on %s for %s" % (selected_link, key_item))
				return True
			else:
				link_options.remove(selected_link)
				selected_link.remove_required_key(key_item)
				if not try_again_on_failure: return False
		return False
	
	def validate(self):
		return len(self.get_available_nodes()) == len(self.nodes)
	
	def draw(self, spring_strength=0.4, antigravity_strength=400000, max_force=-1):
		size = (len(self.nodes) + len(self.links))*75
		convergence_threshold = 10
		
		blobs = dict.fromkeys(self.nodes + self.links)
		for b in blobs:
			blobs[b] = [size*random.random(), size*random.random()]
		blobs[self.start_node] = [size/2, size/2]
		
		converged = False
		max_iter = 1000
		iter = 0
		while not converged:
			iter += 1
			if iter > max_iter:
				print("Exceeded maximum iterations of %s; aborting" % max_iter)
				break
			converged = True
			for b in blobs:
				if b == self.start_node: continue
				try:
					f = [0, 0]
					# antigravity pushing away from other blobs
					for other in blobs:
						if other is b: continue
						v = [blobs[b][0] - blobs[other][0], blobs[b][1] - blobs[other][1]]
						r = math.sqrt(v[0]**2 + v[1]**2)
						if r < 1: r = 1
						d = [v[0]/r, v[1]/r]
						strength = antigravity_strength/(r**2)
						f = [f[0] + strength*d[0], f[1] + strength*d[1]]
					# spring pulling links together
					if type(b) == Node:
						for other in b.links:
							v = [blobs[other][0] - blobs[b][0], blobs[other][1] - blobs[b][1]]
							r = math.sqrt(v[0]**2 + v[1]**2)
							d = [v[0]/r, v[1]/r]
							strength = spring_strength * r
							f = [f[0] + strength*d[0], f[1] + strength*d[1]]
					elif type(b) == Link:
						for other in b.connected_nodes:
							v = [blobs[other][0] - blobs[b][0], blobs[other][1] - blobs[b][1]]
							r = math.sqrt(v[0]**2 + v[1]**2)
							d = [v[0]/r, v[1]/r]
							strength = spring_strength * r
							f = [f[0] + strength*d[0], f[1] + strength*d[1]]
					if max_force > 0:
						# limit force
						force_magnitude = math.sqrt(f[0]**2 + f[1]**2)
						if force_magnitude > max_force:
							f = [f[0]/force_magnitude*max_force, f[1]/force_magnitude*max_force]
					# apply force
					blobs[b] = [blobs[b][0] + f[0], blobs[b][1] + f[1]]
					# constrain
					blobs[b][0] = max(min(blobs[b][0], size), 0)
					blobs[b][1] = max(min(blobs[b][1], size), 0)
					if math.sqrt(f[0]**2 + f[1]**2) > convergence_threshold: converged = False
				except OverflowError:
					print("OverflowError; aborting")
					break
		
		from PIL import Image, ImageDraw
		im = Image.new("RGB", (size, size), (255, 255, 255))
		draw = ImageDraw.Draw(im)
		blob_size = 50
		key_color_map = {}
		for b, position in blobs.items():
			if type(b) == Node:
				for link in b.links:
					draw.line([position[0], position[1], blobs[link][0], blobs[link][1]], fill=(0, 0, 0), width=2)
				if b is self.start_node:
					draw.rectangle([position[0]-blob_size-2, position[1]-blob_size-2, position[0]+blob_size+2, position[1]+blob_size+2], outline=(255, 0, 0), fill=None, width=2)
				draw.rectangle([position[0]-blob_size, position[1]-blob_size, position[0]+blob_size, position[1]+blob_size], outline=(0, 0, 0), fill=(255, 255, 255), width=2)
				if len(b.key_items) > 0:
					for k in b.key_items:
						if k in key_color_map:
							key_color = key_color_map[k]
						else:
							key_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
							key_color_map[k] = key_color
						draw.rectangle([position[0]-blob_size/5, position[1]-blob_size/5, position[0]+blob_size/5, position[1]+blob_size/5], fill=key_color)
						draw.text([position[0], position[1]], str(k), fill=(0, 0, 0))
				draw.text([position[0]-blob_size+4, position[1]-blob_size+4], str(b), fill=(0, 0, 0))
			else: # Link
				if len(b.required_keys) > 0:
					k = b.required_keys[0]
					size = blob_size/2
					if k in key_color_map:
						color = key_color_map[k]
					else:
						color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
						key_color_map[k] = color
				else:
					continue
					color = (0, 0, 0)
					size = blob_size/10
				draw.ellipse([position[0]-size, position[1]-size, position[0]+size, position[1]+size], outline=(0, 0, 0), fill=color, width=2)
				if len(b.required_keys) > 0:
					draw.text([position[0], position[1]], str(k), fill=(0, 0, 0))
		# crop to fit
		"""
		center_x = int(im.size[0]/2)
		center_y = int(im.size[1]/2)
		xmin, ymin = im.size
		xmax, ymax = 0, 0
		for x in range(im.size[0]):
			for y in range(im.size[1]):
				if im.getpixel((x, y)) != (255, 255, 255):
					if x > xmax: xmax = x
					if x < xmin: xmin = x
					if y > ymax: ymax = y
					if y < ymin: ymin = y
		x_from_center = max([abs(center_x - x) for x in (xmin, xmax)])
		y_from_center = max([abs(center_y - y) for y in (ymin, ymax)])
		return im.crop((
			center_x - x_from_center - 1,
			center_y - y_from_center - 1,
			center_x + x_from_center + 1,
			center_y + y_from_center + 1
		))
		"""
		im.show()

class GraphElement():
	pass

class Node(GraphElement):
	def __init__(self, parent, id, max_key_items=1, region=None):
		self.parent = parent
		self.id = id
		self.links = []
		self.max_key_items = max_key_items
		self.key_items = []
		self.region = region
	
	def __repr__(self):
		s = "Node %s" % self.id
		if self.region: s += " (%s)" % self.region
		return s
	
	def __str__(self):
		return self.id
	
	def get_linked_nodes(self):
		linked_nodes = []
		for l in self.links:
			for n in l.connected_nodes:
				if n is not self: linked_nodes.append(n)
		return linked_nodes
	
	def add_key_item(self, key_item):
		self.key_items.append(key_item)
		key_item.location = self
		assert len(self.key_items) <= self.max_key_items

class Link(GraphElement):
	def __init__(self, parent, node1, node2, required_keys=None, max_required_keys=1, region=None):
		self.parent = parent
		self.id = "%s/%s" % tuple(sorted((str(node1), str(node2))))
		self.connected_nodes = (node1, node2)
		self.max_required_keys = max_required_keys
		if required_keys: self.required_keys = required_keys
		else: self.required_keys = []
		assert len(self.required_keys) <= self.max_required_keys
		self.region = region
	
	def __repr__(self):
		s = "Link %s" % self.id
		if len(self.required_keys) > 0:
			s += " (Requires " + ", ".join([str(k) for k in self.required_keys]) + ")"
		return s
	
	def __str__(self):
		return self.id
	
	def get_destination_node(self, start_node):
		assert start_node in self.connected_nodes
		if start_node == self.connected_nodes[0]: return self.connected_nodes[1]
		else: return self.connected_nodes[0]
	
	def add_required_key(self, key_item):
		self.required_keys.append(key_item)
		assert len(self.required_keys) <= self.max_required_keys
	
	def remove_required_key(self, key_item):
		assert key_item in self.required_keys
		self.required_keys.remove(key_item)

class KeyItem():
	def __init__(self, id, location=None, reusable=False, region=None):
		self.id = id
		self.reusable = reusable
		self.used = False
		self.location = location
		self.region = region
	
	def __repr__(self):
		return "Key Item %s" % self.id
	
	def __str__(self):
		return self.id
	
	def can_use(self):
		return self.reusable or not self.used

#############################################################################################

def example_graph():
	# Return an example graph with uniquely named rooms, passages, and keys
	node_descriptor_1 = [
		"big",
		"cavernous",
		"desecrated",
		"fractured",
		"gargantuan",
		"loud",
		"marred",
		"noisy",
		"painted",
		"quiet",
		"silent",
		"tiny",
		"vast"
	]
	node_descriptor_2 = [
		"aromatic",
		"blazing",
		"cluttered",
		"damp",
		"echoing",
		"frigid",
		"grey",
		"infested",
		"murky",
		"orange",
		"pale",
		"red",
		"shining",
		"unknowable",
		"warm",
		"yellow"
	]
	link_descriptor_1 = [
		"cramped",
		"destroyed",
		"familiar",
		"long",
		"mysterious",
		"narrow",
		"steep",
		"twisting",
		"wide",
	]
	link_descriptor_2 = [
		"barren",
		"deserted",
		"flooded",
		"haunted",
		"lovely",
		"overgrown",
		"rundown",
		"sunlit",
		"windy"
	]
	key_names = [
		"a day when you feel better",
		"all manner of deviltry",
		"whispers from the storefronts",
		"real suspicious cargo",
		"a mouth full of surprises",
		"brighter things than diamonds",
		"a head full of memories",
		"a whole lot of money",
		"a thing of beauty",
		"something hateful",
		"the damage we've done",
		"all your weapons",
		"silent curses",
		"standards of any kind",
		"what you brought me out here for",
		"the secret name",
		"the spirit of a brighter time",
		"the new dark light",
		"my breaking point",
		"all the things we'd held in secret",
		"all the rainbow's heavy tones",
		"whatever's left of me",
		"the blessing I've got coming",
		"the only thing I know"
	]
	
	# Make graph
	graph = Graph.random_graph(min_nodes=15, max_nodes=20, lock_count=5, max_links_per_node=4, loopback_chance_from_none=0.2, loopback_chance_from_region=0.4, region_chance_from_region=0)
	assert len(node_descriptor_1)*len(node_descriptor_2) >= len(graph.nodes)
	assert len(link_descriptor_1)*len(link_descriptor_2) >= len(graph.links)
	assert len(key_names) >= len(graph.keys)
	
	# Name graph elements
	random.shuffle(key_names)
	for key in graph.keys:
		key.id = Colors.KEY + key_names.pop() + Colors.END
	used_node_names = []
	for node in graph.nodes:
		while True:
			name = "a %s, %s room" % (random.choice(node_descriptor_1), random.choice(node_descriptor_2))
			if name not in used_node_names:
				used_node_names.append(name)
				node.id = Colors.ROOM + name + Colors.END
				break
	used_link_names = []
	for link in graph.links:
		while True:
			name = "the %s, %s path" % (random.choice(link_descriptor_1), random.choice(link_descriptor_2))
			if name not in used_link_names:
				used_link_names.append(name)
				link.id = Colors.PATH + name + Colors.END
				break
	return graph

def adventure(graph):
	# Do a text-adventure-style crawl through the specified graph
	
	current_node = graph.start_node
	visited_nodes = []
	visited_links = []
	attempted_links = []
	inventory = []
	line = "-------------------------------------------------------------------------------"
	while True:
		print(line)
		print("> You find yourself in %s" % (current_node.id))
		if current_node not in visited_nodes: visited_nodes.append(current_node)
		if len(current_node.key_items) > 0 and current_node.key_items[0] not in inventory:
			print("> In this room, you find %s" % (current_node.key_items[0]))
			inventory.append(current_node.key_items[0])
		if len(visited_nodes) >= len(graph.nodes):
			print("> You have seen all that there is to see.")
			response = get_user_options(["Yes", "No"], "> Continue exploring?")
			if response == "No": break
		link_options = []
		for link in current_node.links:
			link_options.append(str(link))
			if link in visited_links:
				link_options[-1] += " to %s" % link.get_destination_node(current_node)
			elif link in attempted_links:
				link_options[-1] += ", which requires %s" % link.required_keys[0]
		selected_link = current_node.links[get_user_options(link_options, "Which path would you like to take?", return_index = True)]
		print(line)
		if len(selected_link.required_keys) > 0 and selected_link.required_keys[0] not in inventory:
			print("> You cannot travel this path until you have found %s" % (selected_link.required_keys[0]))
			if selected_link not in attempted_links: attempted_links.append(selected_link)
		else:
			if len(selected_link.required_keys) > 0:
				print("> Travelling this path requires %s, which you have found" % (selected_link.required_keys[0]))
			print("> You travel down %s and reach %s" % (selected_link, selected_link.get_destination_node(current_node)))
			current_node = selected_link.get_destination_node(current_node)
			if selected_link not in visited_links: visited_links.append(selected_link)
		

def get_user_options(options, prompt="Select from the following:", return_index=False):
	while True:
		print(prompt)
		for i in range(0, len(options)):
			print("%s:\t%s" % (i+1, options[i]))
		index = input("Selection: ")
		try:
			index = int(index) - 1
			if return_index: return index
			else: return options[index]
		except:
			print("Input must be one of the integer values offered")

class Colors():
	END = "\x1b[0m"
	KEY = "\x1b[7;37;45m"
	ROOM = "\x1b[7;37;41m"
	PATH = "\x1b[7;37;40m"

#############################################################################################

def test():
	for s in range(1):
		random.seed(s)
		graph = Graph.random_graph(min_nodes=35, max_nodes=40, lock_count=10, max_links_per_node=4, loopback_chance_from_region=0.2, region_chance_from_region=0)
		assert graph.validate()
		#graph.draw(antigravity_strength=500000, spring_strength=0.3)
		#graph.draw(antigravity_strength=400000, spring_strength=0.4)
		#graph.draw(antigravity_strength=400000, spring_strength=0.4, max_force=50000)
		graph.draw(antigravity_strength=400000, spring_strength=0.4, max_force=30000)


#############################################################################################

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("--adventure", help="Play through an adventure with an example dungeon.", action="store_true")
	parser.add_argument("--test", help="Run a test function.", action="store_true")
	args = parser.parse_args()
	
	if args.adventure:
		adventure(example_graph())
	elif args.test:
		test()