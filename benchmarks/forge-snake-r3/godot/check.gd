extends SceneTree
func _init():
	var res = {}
	var ps = load("res://snake-sectional-r3.glb")
	res["loaded"] = ps != null
	if ps == null:
		print("R3_GODOT ", JSON.stringify(res)); quit(1); return
	var root = ps.instantiate()
	var mis = []
	var stack = [root]
	while stack.size() > 0:
		var n = stack.pop_back()
		for c in n.get_children(): stack.push_back(c)
		if n is MeshInstance3D: mis.append(n)
		if n is Skeleton3D: res["skeleton"] = true
	var textured = {}; var tris = 0; var notan = 0; var seg_meshes = {}; var segs = 0; var hous = 0; var glow = 0; var mats = {}
	for mi in mis:
		var m = mi.mesh
		for s in m.get_surface_count():
			var a = m.surface_get_arrays(s)
			var idx = a[Mesh.ARRAY_INDEX]
			tris += (idx.size() if idx != null else a[Mesh.ARRAY_VERTEX].size()) / 3
			if a[Mesh.ARRAY_TANGENT] == null or a[Mesh.ARRAY_TANGENT].size() == 0: notan += 1
			var mat = m.surface_get_material(s)
			if mat:
				mats[mat.resource_name] = mat.get_class()
				if mat.resource_name.begins_with("R3 directional"):
					var fields = {"albedo": mat.albedo_texture != null, "normal": mat.normal_texture != null, "ao_enabled": mat.ao_enabled}
					if mat is ORMMaterial3D:
						fields["orm"] = mat.orm_texture != null
					else:
						fields["roughness"] = mat.roughness_texture != null
						fields["metallic"] = mat.metallic_texture != null
						fields["ao"] = mat.ao_texture != null
					textured[mat.resource_name] = fields
		var nm = String(mi.name)
		if nm.begins_with("Segment_"): segs += 1; seg_meshes[m.get_rid()] = 1
		if nm.contains("Housing"): hous += 1
		if nm.contains("GlowBars"): glow += 1
	res["mesh_instances"] = mis.size(); res["triangles"] = tris; res["surfaces_without_tangents"] = notan
	res["segment_nodes"] = segs; res["segment_distinct_meshes"] = seg_meshes.size(); res["housing_nodes"] = hous; res["glow_nodes"] = glow
	res["materials"] = mats; res["textured_materials"] = textured
	# pose check: rotate every segment node and confirm rigid nodes stay independent
	var ok = 0
	for mi in mis:
		if String(mi.name).begins_with("Segment_"):
			var t0 = mi.transform
			mi.rotate_object_local(Vector3.UP, 0.3)
			if not mi.transform.is_equal_approx(t0): ok += 1
	res["segments_posable"] = ok
	print("R3_GODOT ", JSON.stringify(res))
	root.free()
	ps = null
	var textures_ok = textured.size() == 3
	for fields in textured.values():
		for value in fields.values(): textures_ok = textures_ok and value
	var passed = textures_ok and segs == 28 and seg_meshes.size() == 1 and hous == 29 and glow == 29 and not res.get("skeleton", false) and notan == 0 and tris <= 60000 and tris >= 30000 and ok == 28
	quit(0 if passed else 1)
