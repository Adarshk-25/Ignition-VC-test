# shared.nav

def findNode(node, targetPath):
	"""node is a single tree node (dict with 'items')"""
	if node.get('data', {}).get('path') == targetPath:
		return node
	for child in node.get('items', []):
		result = findNode(child, targetPath)
		if result:
			return result
	return None

def findNodeInForest(tree, targetPath):
	"""tree is the top-level list, e.g. the full JSON array"""
	for root in tree:
		result = findNode(root, targetPath)
		if result:
			return result
	return None

def getChildren(tree, currentPath):
    node = findNodeInForest(tree, currentPath)
    if node:
        return [
            {
                "label": c.get('label'),
                "path": c.get('data', {}).get('path'),
                "currentPath": node.get('data', {}).get('path')
            }
            for c in node.get('items', [])
            if c.get('data', {}).get('path')
        ]
    return []

def getAncestors(tree, targetPath, root=None, trail=None):
    trail = trail or []
    roots = tree if root is None else [root]
    for node in roots:
        newTrail = trail + [{
            "label": node.get('label'),
            "path": node.get('data', {}).get('path'),
            "forwardDisplay": True
        }]
        if node.get('data', {}).get('path') == targetPath:
            return newTrail
        for child in node.get('items', []):
            result = getAncestors(tree, targetPath, child, newTrail)
            if result:
                return result
    return None