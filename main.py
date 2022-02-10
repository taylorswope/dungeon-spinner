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

logging.basicConfig(
	level=logging.INFO,
	format="%(levelname)s %(asctime)-15s %(filename)s:%(lineno)d:%(message)s",
	filename="output.log",
	filemode="w"
)

class Graph():
	def __init__(self):
		self.nodes = []
		self.links = []
		self.start_node = None
		
	def add_node(self, node_id="null"):
		new_node = Node(self, node_id)
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
	
	def place_key_item(self, key_item, try_again_on_failure=False):
		link_options = [l for l in self.links if len(l.required_keys) < l.max_required_keys]
		while len(link_options) > 0:
			selected_link = random.choice(link_options)
			selected_link.add_required_key(key_item)
			node_options = [n for n in self.get_available_nodes() if len(n.key_items) < n.max_key_items]
			if len(node_options) > 0:
				selected_node = random.choice(node_options)
				selected_node.add_key_item(key_item)
				logging.info("Placed %s in %s for a lock on %s" % (key_item, selected_node, selected_link))
				return True
			else:
				selected_link.remove_required_key(key_item)
				if not try_again_on_failure: return False
		return False
	
	def validate(self):
		return len(self.get_available_nodes()) == len(self.nodes)

class GraphElement():
	pass

class Node(GraphElement):
	def __init__(self, parent, id, max_key_items=1):
		self.parent = parent
		self.id = id
		self.links = []
		self.max_key_items = max_key_items
		self.key_items = []
	
	def __str__(self):
		return "Node %s" % self.id
	
	def get_linked_nodes(self):
		linked_nodes = []
		for l in self.links:
			for n in l.connected_nodes:
				if n is not self: linked_nodes.append(n)
		return linked_nodes
	
	def add_key_item(self, key_item):
		self.key_items.append(key_item)
		assert len(self.key_items) <= self.max_key_items

class Link(GraphElement):
	def __init__(self, parent, node1, node2, required_keys=None, max_required_keys=1):
		self.parent = parent
		self.id = "%s/%s" % tuple(sorted((str(node1), str(node2))))
		self.connected_nodes = (node1, node2)
		self.max_required_keys = max_required_keys
		if required_keys: self.required_keys = required_keys
		else: self.required_keys = []
		assert len(self.required_keys) <= self.max_required_keys
	
	def __str__(self):
		return "Link %s" % self.id
	
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
	def __init__(self, id, reusable = False):
		self.id = id
		self.reusable = reusable
		self.used = False
	
	def __str__(self):
		return "Key Item %s" % self.id
	
	def can_use(self):
		return self.reusable or not self.used

#############################################################################################

def test():
	random.seed()
	
	graph = Graph()
	node1 = graph.add_node("1")
	node2 = graph.add_node("2")
	node3 = graph.add_node("3")
	node4 = graph.add_node("4")
	node5 = graph.add_node("5")
	node6 = graph.add_node("6")
	node7 = graph.add_node("7")
	node8 = graph.add_node("8")
	node9 = graph.add_node("9")
	node10 = graph.add_node("10")
	node11 = graph.add_node("11")
	
	graph.set_start_node(node1)
	
	key_items = [
		KeyItem("Red"),
		KeyItem("Orange"),
		KeyItem("Yellow"),
		KeyItem("Green"),
		KeyItem("Cyan")
	]
	
	graph.link_nodes(node1, node2)
	graph.link_nodes(node2, node3)
	graph.link_nodes(node3, node4)
	graph.link_nodes(node2, node5)
	graph.link_nodes(node3, node7)
	graph.link_nodes(node5, node6)
	graph.link_nodes(node6, node8)
	graph.link_nodes(node5, node9)
	graph.link_nodes(node7, node10)
	graph.link_nodes(node10, node11)
	
	#node4.add_key_item(red_key)
	#node9.add_key_item(orange_key)
	
	for k in key_items:
		graph.place_key_item(k)
	
	print(graph.validate())

#############################################################################################

if __name__ == "__main__":
	test()