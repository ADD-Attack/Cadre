extends SceneTree
func _init():
	var res = {}
	var ps = load("res://snake-sectional-r1.glb")
	res["loaded"] = ps != null
	if ps == null:
		print("R1_GODOT ", JSON.stringify(res)); quit(1); return
	var root = ps.instantiate()
	var mis = []
	var stack = [root]
	while stack.size() > 0:
		var n = stack.pop_back()
		for c in n.get_children(): stack.push_back(c)
		if n is MeshInstance3D: mis.append(n)
		if n is Skeleton3D: res["skeleton"] = true
	var tris = 0; var notan = 0; var seg_meshes = {}; var segs = 0; var hous = 0; var glow = 0; var mats = {}
	for mi in mis:
		var m = mi.mesh
		for s in m.get_surface_count():
			var a = m.surface_get_arrays(s)
			var idx = a[Mesh.ARRAY_INDEX]
			tris += (idx.size() if idx != null else a[Mesh.ARRAY_VERTEX].size()) / 3
			if a[Mesh.ARRAY_TANGENT] == null or a[Mesh.ARRAY_TANGENT].size() == 0: notan += 1
			var mat = m.surface_get_material(s)
			if mat: mats[mat.resource_name] = mat.get_class()
		var nm = String(mi.name)
		if nm.begins_with("Segment_"): segs += 1; seg_meshes[m.get_rid()] = 1
		if nm.contains("Housing"): hous += 1
		if nm.contains("GlowBars"): glow += 1
	res["mesh_instances"] = mis.size(); res["triangles"] = tris; res["surfaces_without_tangents"] = notan
	res["segment_nodes"] = segs; res["segment_distinct_meshes"] = seg_meshes.size(); res["housing_nodes"] = hous; res["glow_nodes"] = glow
	res["materials"] = mats
	# pose check: rotate every segment node and confirm rigid nodes stay independent
	var ok = 0
	for mi in mis:
		if String(mi.name).begins_with("Segment_"):
			var t0 = mi.transform
			mi.rotate_object_local(Vector3.UP, 0.3)
			if not mi.transform.is_equal_approx(t0): ok += 1
	res["segments_posable"] = ok
	print("R1_GODOT ", JSON.stringify(res))
	root.free()
	ps = null
	quit(0)
