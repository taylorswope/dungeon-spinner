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

class GraphError(Exception):
	pass

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
			s += "\n\t%s (Region %s)" % (n, n.region)
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
		node_count=30,
		max_links_per_node=3,
		key_count=10,
		loopback_chance_from_none=0.1, # chance that a link will go to an existing node instead of a new one when coming from a region-less node
		loopback_chance_from_region=0.2, # chance that a link will go to an existing node instead of a new one when coming from an existing region
		regions_can_connect=False, # whether or not a region can connect to another region
		region_chance_from_none=0.4, # chance that a new node will introduce a new region when stemming from a region-less node
		region_chance_from_region=0.0, # chance that a new node will introuce a new region instead of continuing an existing region
		region_key_chance=0.7, # for each lock, chance that it will be region-specific rather than global
		extra_locks_for_global_keys=10, # number of extra locks to be places for non-region keys (i.e. the same key will open multiple locks)
		priority_for_low_link_nodes=1, # when selecting which node to expand from, this multiplier will be used as a weight when randomly selecting nodes with fewer links (i.e. when this is higher, nodes with fewer links will be prioritized)
		avoid_redundant_links=True # try to avoid linking two nodes that are already linked
	):
		## TODO:
		## option to prioritize/force more even distribution of links (i.e. avoid dead ends)
		## option to prioritize linking off of regions or non-regions
		
		logging.info(
			f"""Generating a random graph with the following settings:
	node_count={node_count},
	max_links_per_node={max_links_per_node},
	key_count={key_count},
	loopback_chance_from_none={loopback_chance_from_none}, 
	loopback_chance_from_region={loopback_chance_from_region},
	regions_can_connect={regions_can_connect},
	region_chance_from_none={region_chance_from_none},
	region_chance_from_region={region_chance_from_region},
	region_key_chance={region_key_chance},
	extra_locks_for_global_keys={extra_locks_for_global_keys},
	priority_for_low_link_nodes={priority_for_low_link_nodes},
	avoid_redundant_links={avoid_redundant_links}"""
		)
		attempts = 0
		max_attempts = 5
		while attempts < max_attempts:
			graph_success = True
			attempts += 1
			logging.info("Starting attempt #%s..." % attempts)
			graph = cls()
			next_node_id = 1
			start_node = graph.add_node(node_id=str(next_node_id))
			graph.set_start_node(start_node)
			next_node_id += 1
			current_region = 1
			while len(graph.nodes) <= node_count:
				# pick which node to expand from
				node_options = [n for n in graph.nodes if len(n.links) < max_links_per_node]
				if len(node_options) == 0:
					logging.error("Could not find any valid nodes to continue graph; aborting this attempt.")
					graph_success = False
					break
				if priority_for_low_link_nodes == 1:
					current_node = random.choice(node_options)
				else:
					current_node = random.choices(node_options, weights = [priority_for_low_link_nodes**(max_links_per_node-len(n.links)-1) for n in node_options])[0]
				# see if we should loop back to an existing node instead of creating a new one
				roll = random.random()
				if len(node_options) > 1 and ((current_node.region and roll < loopback_chance_from_region) or roll < loopback_chance_from_none):
					linked_node_choices = [n for n in node_options if n is not current_node]
					if current_node.region and not regions_can_connect:
						linked_node_choices = [n for n in linked_node_choices if (n.region == None or n.region == current_node.region)]
					if avoid_redundant_links:
						linked_node_choices = [n for n in linked_node_choices if current_node not in n.get_linked_nodes()]
					if len(linked_node_choices) > 0:
						linked_node = random.choice(linked_node_choices)
						graph.link_nodes(current_node, linked_node)
						continue
				# create a new node
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
			if not graph_success: continue
			# add keys and locks
			key_names = list(KEY_NAMES)
			while len(graph.keys) < key_count:
				roll = random.random()
				if current_region > 1 and roll < region_key_chance:
					region = random.randrange(1, current_region)
				else:
					region = None
				if len([l for l in graph.links if l.region == region and len(l.required_keys)==0]) == 0:
					region = None # failsafe for if the region we picked doesn't have any lockable links
				key_item = KeyItem(key_names.pop(), region=region)
				success = graph.place_key_item(key_item)
				if not success:
					logging.error("Could not find any valid nodes to place a key item; aborting this attempt.")
					graph_success = False
					break
			if not graph_success: continue
			while len([l for l in graph.links if len(l.required_keys)>0]) < key_count+extra_locks_for_global_keys:
				global_keys = [k for k in graph.keys if k.region == None]
				if len(global_keys) == 0: break
				key = random.choice(global_keys)
				success = graph.place_lock_for_key(key, try_again_on_failure=True)
				if not success:
					logging.error("Could not find any valid links to place a lock; aborting this attempt.")
					graph_success = False
					break
			if not graph_success: continue
			return graph
		raise GraphError("Failed to create a valid graph after %s attempts; aborting graph generation." % max_attempts)
		
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
		"""Returns a list of available nodes that are reachable from the start node, using only key items found in available nodes"""
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
			if key_item.region:
				node_options = [n for n in node_options if n.region == key_item.region]
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
		logging.info("Failed to place key item %s" % (key_item))
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
	
	def draw(self, max_tries=3, max_iterations=1000, max_force=30000):
		"""Creates a force-directed graph representation"""
		spring_strength=0.4 #0.4
		antigravity_strength=40000 #400000
		
		size = (len(self.nodes) + len(self.links))*75
		convergence_threshold = 10
		
		blobs = dict.fromkeys(self.nodes + self.links)
		for b in blobs:
			blobs[b] = [size*random.random(), size*random.random()]
		blobs[self.start_node] = [size/2, size/2]
		
		success = False
		try_count = 0
		while not success:
			try_count += 1
			logging.info("Starting attempt #%s at drawing graph %s..." % (try_count, self))
			success = True
			converged = False
			max_iterations = 1000
			iteration = 0
			while not converged:
				iteration += 1
				if iteration > max_iterations:
					logging.warning("Exceeded maximum iterations of %s; aborting" % max_iterations)
					success = False
					break
				converged = True
				for b in blobs:
					if b == self.start_node: continue # keep the start node rooted in place
					try:
						f = [0, 0]
						# antigravity pushing away from other blobs
						for other in blobs:
							if other is b: continue
							v = [blobs[b][0] - blobs[other][0], blobs[b][1] - blobs[other][1]]
							r = math.sqrt(v[0]**2 + v[1]**2)
							r = max(r, 1)
							d = [v[0]/r, v[1]/r]
							strength = antigravity_strength/(r**2)
							f = [f[0] + strength*d[0], f[1] + strength*d[1]]
						# spring pulling links together
						if type(b) == Node:
							for other in b.links:
								v = [blobs[other][0] - blobs[b][0], blobs[other][1] - blobs[b][1]]
								r = math.sqrt(v[0]**2 + v[1]**2)
								r = max(r, 1)
								d = [v[0]/r, v[1]/r]
								strength = spring_strength * r
								f = [f[0] + strength*d[0], f[1] + strength*d[1]]
						elif type(b) == Link:
							for other in b.connected_nodes:
								v = [blobs[other][0] - blobs[b][0], blobs[other][1] - blobs[b][1]]
								r = math.sqrt(v[0]**2 + v[1]**2)
								r = max(r, 1)
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
						# constrain blob positions
						blobs[b][0] = max(min(blobs[b][0], size), 0)
						blobs[b][1] = max(min(blobs[b][1], size), 0)
						if math.sqrt(f[0]**2 + f[1]**2) > convergence_threshold:
							converged = False
					except OverflowError:
						logging.warning("OverflowError; aborting")
						success = False
						break
			if try_count > max_tries:
				logging.error("Could not draw a graph after %s attempts of %s iterations." % (max_tries, max_iterations))
				break
		
		from PIL import Image, ImageDraw
		blob_size = 20
		margin = blob_size + 10
		min_x = min([b[0] for b in blobs.values()])
		max_x = max([b[0] for b in blobs.values()])
		min_y = min([b[1] for b in blobs.values()])
		max_y = max([b[1] for b in blobs.values()])
		x_size = int(max_x - min_x) + 2*margin
		y_size = int(max_y - min_y) + 2*margin
		x_offset = margin - min_x
		y_offset = margin - min_y
		im = Image.new("RGB", (x_size, y_size), (255, 255, 255))
		draw = ImageDraw.Draw(im)
		
		key_color_map = {}
		for b, position in blobs.items():
			if type(b) == Node:
				for link in b.links:
					draw.line([position[0]+x_offset, position[1]+y_offset, blobs[link][0]+x_offset, blobs[link][1]+y_offset], fill=(0, 0, 0), width=2)
				if b is self.start_node:
					draw.rectangle([position[0]-blob_size-2+x_offset, position[1]-blob_size-2+y_offset, position[0]+blob_size+2+x_offset, position[1]+blob_size+2+y_offset], outline=(255, 0, 0), fill=None, width=2)
				draw.rectangle([position[0]-blob_size+x_offset, position[1]-blob_size+y_offset, position[0]+blob_size+x_offset, position[1]+blob_size+y_offset], outline=(0, 0, 0), fill=(255, 255, 255), width=2)
				if len(b.key_items) > 0:
					for k in b.key_items:
						if k in key_color_map:
							key_color = key_color_map[k]
						else:
							key_color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
							key_color_map[k] = key_color
						draw.rectangle([position[0]-blob_size/4+x_offset, position[1]-blob_size/4+y_offset, position[0]+blob_size/4+x_offset, position[1]+blob_size/4+y_offset], fill=key_color)
						draw.text([position[0]-2+x_offset, position[1]-4+y_offset], str(k), fill=(0, 0, 0))
				draw.text([position[0]-blob_size+4+x_offset, position[1]-blob_size+4+y_offset], str(b), fill=(0, 0, 0))
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
				draw.ellipse([position[0]-size+x_offset, position[1]-size+y_offset, position[0]+size+x_offset, position[1]+size+y_offset], outline=(0, 0, 0), fill=color, width=2)
				if len(b.required_keys) > 0:
					draw.text([position[0]-2+x_offset, position[1]-4+y_offset], str(k), fill=(0, 0, 0))
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
		"the only thing I know",
		"one good thing to say"
	]
	
	# Make graph
	graph = Graph.random_graph(node_count=20, key_count=8, max_links_per_node=4, loopback_chance_from_none=0.2, loopback_chance_from_region=0.4, region_chance_from_region=0, regions_can_connect=False, avoid_redundant_links=True)
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
	wanderer_node = graph.start_node
	wanderer_inventory = []
	wanderer_cooldown = 3
	wanderer_actions = [
		"gives you an unsettling look",
		"nods silently",
		"whispers a secret",
		"mumbles foreboding omens",
		"listens to your story",
		"gives you a cryptic signal",
		"looks at you worriedly",
		"gives you a blessing",
		"smiles warmly at you"
	]
	random.shuffle(wanderer_actions)
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
			# wanderer
			if len(wanderer_actions) > 0:
				if wanderer_cooldown <= 0:
					if current_node == wanderer_node:
						print("> You cross paths with a %swanderer%s, who %s before continuing on." % (Colors.WANDERER, Colors.END, wanderer_actions.pop()))
						if len(wanderer_actions) == 0:
							print("> It is the last time you will see each other.")
						wanderer_cooldown = 3
				else:
					wanderer_cooldown -= 1
				if len(wanderer_node.key_items) > 0 and wanderer_node.key_items[0] not in wanderer_inventory:
					wanderer_inventory.append(wanderer_node.key_items[0])
				selected_link = random.choice([l for l in wanderer_node.links if len(l.required_keys)==0 or l.required_keys[0] in wanderer_inventory])
				wanderer_node = selected_link.get_destination_node(wanderer_node)

def get_user_options(options, prompt="Select from the following:", return_index=False):
	while True:
		print(prompt)
		for i in range(0, len(options)):
			print("%s:\t%s" % (i+1, options[i]))
		index = input("Selection: ")
		if not index.isdigit() or int(index)-1 >= len(options):
			print("Input must be one of the integer values offered")
		else:
			index = int(index) - 1
			if return_index: return index
			else: return options[index]

class Colors():
	END = "\x1b[0m"
	KEY = "\x1b[7;37;45m"
	ROOM = "\x1b[7;37;41m"
	PATH = "\x1b[7;37;40m"
	WANDERER = "\x1b[7;37;42m"

#############################################################################################

def test():
	for s in range(10):
		#random.seed(s*100)
		#random.seed(10)
		
		"""
		graph = Graph.random_graph(
			node_count=48,
			max_links_per_node=5,
			key_count=20,
			loopback_chance_from_none=0.39333963307182956, 
			loopback_chance_from_region=0.4399818290196964,
			regions_can_connect=True,
			region_chance_from_none=0.12991372374448845,
			region_chance_from_region=0.3178629348029946,
			region_key_chance=0.9049456946664788,
			extra_locks_for_global_keys=10,
			priority_for_low_link_nodes=5,
			avoid_redundant_links=True
		)
		
		
		graph = Graph.random_graph(
			node_count=random.randint(20, 50),
			max_links_per_node=random.randint(3, 5),
			key_count=random.randint(10, 20),
			loopback_chance_from_none=random.uniform(0, 0.5), # chance that a link will go to an existing node instead of a new one when coming from a region-less node
			loopback_chance_from_region=random.uniform(0, 0.5), # chance that a link will go to an existing node instead of a new one when coming from an existing region
			regions_can_connect=random.choice((True, False)), # whether or not a region can connect to another region
			region_chance_from_none=random.uniform(0, 0.5), # chance that a new node will introduce a new region when stemming from a region-less node
			region_chance_from_region=random.uniform(0, 0.5), # chance that a new node will introuce a new region instead of continuing an existing region
			region_key_chance=random.random(), # for each lock, chance that it will be region-specific rather than global
			extra_locks_for_global_keys=random.randint(5, 15), # number of extra locks to be places for non-region keys (i.e. the same key will open multiple locks)
			priority_for_low_link_nodes=random.randint(1, 5),
			avoid_redundant_links=random.choice((True, False))
		)
		"""
		graph = Graph.random_graph()
		
		#graph = Graph.random_graph(node_count=40, key_count=10, max_links_per_node=3, loopback_chance_from_region=0.2, region_chance_from_region=0, regions_can_connect=False, extra_locks_for_global_keys=10)
		for n in graph.nodes:
			n.id = "%s (%s)" % (n.id, n.region) if n.region else "%s (%s)" % (n.id, 0)
		assert graph.validate()
		#random.seed(10)
		graph.draw(max_tries=3, max_iterations=1000)
		#random.seed(10)
		#graph.draw(max_tries=1, max_iterations=1001)
		
		#random.seed(10)
		#graph.draw(max_tries=1, max_force=20000, max_iterations=1000)
		#random.seed(10)
		#graph.draw(max_tries=1, max_force=20000, max_iterations=1001)
		


#############################################################################################

if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("--generate", help="Generate a dungeon graph and print its details.", action="store_true")
	parser.add_argument("--draw", help="When using the --generate flag, show a rough graphical representation of the dungeon.", action="store_true")
	parser.add_argument("--adventure", help="Play through an adventure with an example dungeon.", action="store_true")
	parser.add_argument("--test", help="Run a test function.", action="store_true")
	
	parser.add_argument("--seed", default=None, help="When using the --generate flag, specifies the seed used for random number generation.")
	parser.add_argument("--node_count", type=int, default=30, help="When using the --generate flag, specifies the number of nodes in the final graph.")
	parser.add_argument("--max_links_per_node", type=int, default=3, help="When using the --generate flag, specifies the maximum number of links a single node can have.")
	parser.add_argument("--key_count", type=int, default=10, help="When using the --generate flag, specifies the number of key items to be placed in the graph.")
	parser.add_argument("--loopback_chance_from_none", type=float, default=0.1, help="When using the --generate flag, specifies the chance that a region-less node will connect back to a pre-existing node instead of spawning a new one.")
	parser.add_argument("--loopback_chance_from_region", type=float, default=0.2, help="When using the --generate flag, specifies the chance that a regioned node will connect back to a pre-existing node instead of spawning a new one.")
	parser.add_argument("--regions_can_connect", action="store_true", help="When using the --generate flag, specifies if a regioned node is able to connect to a regioned node with a different region. Does not limit connections to region-less nodes.")
	parser.add_argument("--region_chance_from_none", type=float, default=0.4, help="When using the --generate flag, specifies the chance that a new node will start a new region when spawned off of a region-less node.")
	parser.add_argument("--region_chance_from_region", type=float, default=0.0, help="When using the --generate flag, specifies the chance that a new node will start a new region when spawned off of a regioned node.")
	parser.add_argument("--region_key_chance", type=float, default=0.7, help="When using the --generate flag, specifies the chance that a new key item will be region-specific (i.e. the lock and key will both be placed within the same region).")
	parser.add_argument("--extra_locks_for_global_keys", type=int, default=10, help="When using the --generate flag, specifies the number of additional locks to place for non-regioned keys (i.e. when this value is greater than 0, at least one key will open multiple locks).")
	parser.add_argument("--priority_for_low_link_nodes", type=float, default=1.0, help="When using the --generate flag, specifies the weight given to nodes with fewer links when selecting which node to branch from (i.e. when this value is higher, nodes with fewer links will be prioritized when adding new links).")
	parser.add_argument("--avoid_redundant_links", action="store_true", help="When using the --generate flag, specifies if the generator should attempt to avoid linking two nodes that are already linked.")
	
	args = parser.parse_args()
	
	if args.generate:
		for arg in (
			args.loopback_chance_from_none,
			args.loopback_chance_from_region,
			args.region_chance_from_none,
			args.region_chance_from_region,
			args.region_key_chance
		):
			if arg < 0 or arg > 1:
				raise ValueError("Chance parameters must be between 0 and 1.")
		random.seed(args.seed)
		graph = Graph.random_graph(
			node_count = args.node_count,
			max_links_per_node = args.max_links_per_node,
			key_count = args.key_count,
			loopback_chance_from_none = args.loopback_chance_from_none,
			loopback_chance_from_region = args.loopback_chance_from_region,
			regions_can_connect = args.regions_can_connect,
			region_chance_from_none = args.region_chance_from_none,
			region_chance_from_region = args.region_chance_from_region,
			region_key_chance = args.region_key_chance,
			extra_locks_for_global_keys = args.extra_locks_for_global_keys,
			priority_for_low_link_nodes = args.priority_for_low_link_nodes,
			avoid_redundant_links = args.avoid_redundant_links
		)
		print(graph.details())
		if args.draw:
			graph.draw()
	elif args.adventure:
		adventure(example_graph())
	elif args.test:
		test()
	else:
		parser.print_help()