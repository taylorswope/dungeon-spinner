# dungeon-spinner

This is a generator of dungeon-like node graphs where links are "locked" until finding "keys" found in nodes. Locks and keys are placed such that every node on the graph is eventually traversable from the starting node.

## Quick Start

To run the generator from the command line, use  ```dungeonspinner.py --generate```. This will generate a random dungeon using the default settings and print details of nodes, links, locks, and keys. Including the ```--draw``` flag will show a rough visual representation of the graph.

Running ```dungeonspinner.py --adventure``` will start a simple turn-based sequence where users can explore an example dungeon, collecting keys and unlocking new paths.

## Details

### Description

The basic algorithm for the generator is to place a starting node, and then:

* pick a node at random from the existing nodes that don't already have the maximum number of links;
* randomly determine if the graph should spawn a new node off of the selected node and link them, or create a new link back to a pre-existing node;
* repeat until the desired number of nodes have been created.

Once all nodes and links have been created, the algorithm will start placing locks and keys. When placing locks and keys, it will:

* select a link at random and place a lock on it;
* find all nodes that are reachable from the start node without having to traverse the selected link (or traversing any link that is locked by a key that cannot be found without traversing the selected link);
* place the key corresponding to the new lock in one of the valid nodes;
* repeat until the desired number of locks and keys have been created;
* optionally, place additional locks for existing keys onto valid links so that individual keys can unlock multiple locks.

Additionally, the algorithm can flag certain nodes as being part of "regions". Nodes within regions can use separate probability settings for how nodes connect, and some keys and locks will be placed such that both are within the same region. This way, the topography of the graph can change as nodes get further from the starting node, and key distribution can have a variety of distances to their respective locks.

### Command Line Usage
* ```--generate``` - Generate a dungeon graph and print its details.
* ```--draw``` - When using the --generate flag, show a rough graphical representation of the dungeon.
* ```--adventure``` - Play through an adventure with an example dungeon.
* ```--seed``` - When using the --generate flag, specifies the seed used for random number generation.
* ```--node_count``` - When using the --generate flag, specifies the number of nodes in the final graph. (Default is 30)
* ```--max_links_per_node``` - When using the --generate flag, specifies the maximum number of links a single node can have. (Default is 3)
* ```--key_count``` - When using the --generate flag, specifies the number of key items to be placed in the graph. (Default is 10)
* ```--loopback_chance_from_none``` - When using the --generate flag, specifies the chance that a region-less node will connect back to a pre-existing node instead of spawning a new one. (Default is 0.1)
* ```--loopback_chance_from_region``` - When using the --generate flag, specifies the chance that a regioned node will connect back to a pre-existing node instead of spawning a new one. (Default is 0.2)
* ```--regions_can_connect``` - When using the --generate flag, specifies if a regioned node is able to connect to a regioned node with a different region. Does not limit connections to region-less nodes. (Default is False)
* ```--region_chance_from_none``` - When using the --generate flag, specifies the chance that a new node will start a new region when spawned off of a region-less node. (Default is 0.4)
* ```--region_chance_from_region``` - When using the --generate flag, specifies the chance that a new node will start a new region when spawned off of a regioned node. (Default is 0.0)
* ```--region_key_chance``` - When using the --generate flag, specifies the chance that a new key item will be region-specific (i.e. the lock and key will both be placed within the same region). (Default is 0.7)
* ```--extra_locks_for_global_keys``` - When using the --generate flag, specifies the number of additional locks to place for non-regioned keys (i.e. when this value is greater than 0, at least one key will open multiple locks). (Default is 10)
* ```--priority_for_low_link_nodes``` - When using the --generate flag, specifies the weight given to nodes with fewer links when selecting which node to branch from (i.e. when this value is higher, nodes with fewer links will be prioritized when adding new links). (Default is 1.0)
* ```--avoid_redundant_links``` - When using the --generate flag, specifies if the generator should attempt to avoid linking two nodes that are already linked. (Default is False)

### Python Usage
If importing dungeonspinner in Python, the ```Graph``` class holds the main functionality, with the ```Graph.random_graph()``` class method replicating the basic command line usage:

```
	def random_graph(cls,
		node_count=30,
		max_links_per_node=3,
		key_count=10,
		loopback_chance_from_none=0.1,
		loopback_chance_from_region=0.2,
		regions_can_connect=False,
		region_chance_from_none=0.4,
		region_chance_from_region=0.0,
		region_key_chance=0.7,
		extra_locks_for_global_keys=10,
		priority_for_low_link_nodes=1,
		avoid_redundant_links=True
	)
```

The ```Graph.detail()``` method will return a string containing information about the graph's nodes and links.

The ```Graph.draw()``` method will show a visual representation of the graph.