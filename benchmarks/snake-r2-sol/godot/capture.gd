extends SceneTree
var model: Node3D
var camera: Camera3D
func _initialize():
	call_deferred("capture")
func capture():
	root.content_scale_size = Vector2i(1280,720)
	root.content_scale_mode = Window.CONTENT_SCALE_MODE_VIEWPORT
	var stage = Node3D.new()
	root.add_child(stage)
	model = load("res://snake-sectional-r2.glb").instantiate()
	stage.add_child(model)
	var env = Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color("c1c1bf")
	env.ambient_light_source = Environment.AMBIENT_SOURCE_SKY
	env.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	var sky = Sky.new()
	var sm = ProceduralSkyMaterial.new()
	sm.sky_top_color = Color(.35,.36,.38)
	sm.sky_horizon_color = Color(.55,.55,.55)
	sm.ground_bottom_color = Color(.13,.13,.13)
	sm.ground_horizon_color = Color(.55,.55,.55)
	sky.sky_material = sm
	env.sky = sky
	env.ambient_light_energy = .7
	var world = WorldEnvironment.new()
	world.environment = env
	stage.add_child(world)
	for spec in [[Vector3(-4,9,6),1.7],[Vector3(1,8,-5),1.2],[Vector3(5,6,2),.4]]:
		var light = DirectionalLight3D.new()
		stage.add_child(light)
		light.position = spec[0]
		light.look_at(Vector3(0,1.5,0))
		light.light_energy = spec[1]
		light.shadow_enabled = true
	camera = Camera3D.new()
	stage.add_child(camera)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.position = Vector3(-7,7,12)
	camera.look_at(Vector3(.5,1.9,0))
	var verts = []
	var todo = [model]
	while todo.size():
		var n = todo.pop_back()
		for child in n.get_children():todo.append(child)
		if n is MeshInstance3D:
			for s in n.mesh.get_surface_count():
				for v in n.mesh.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]:verts.append(camera.global_transform.affine_inverse() * (n.global_transform * v))
	var lo = Vector2(INF,INF)
	var hi = Vector2(-INF,-INF)
	for v in verts:
		lo = lo.min(Vector2(v.x,v.y));hi=hi.max(Vector2(v.x,v.y))
	var center = (lo+hi)/2
	camera.position += camera.global_basis.x*center.x+camera.global_basis.y*center.y
	camera.size = max(hi.y-lo.y,(hi.x-lo.x)/(1280.0/720.0))*1.12
	for i in 12:await process_frame
	await RenderingServer.frame_post_draw
	var img = root.get_texture().get_image()
	assert(img.get_size()==Vector2i(1280,720))
	var err = img.save_png("res://godot-import-pose.png")
	print("R2_NATIVE_CAPTURE ",JSON.stringify({"viewport":[img.get_width(),img.get_height()],"save_error":err,"renderer":"gl_compatibility","role":"import and rest-pose evidence, not judged capture","camera_position":str(camera.position),"camera_size":camera.size}))
	quit(err)
