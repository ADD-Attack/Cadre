extends Node3D
## Self-contained 3D arcade demo. No input actions or external resources.

var ship: Node3D
var muzzle: MeshInstance3D
var engines: Array[MeshInstance3D] = []
var enemies: Array[Dictionary] = []
var shots: Array[Dictionary] = []
var sparks: Array[Dictionary] = []
var score_label: Label
var score := 0
var elapsed := 0.0
var fire_timer := 0.0
var respawn_timer := 0.0
var rng := RandomNumberGenerator.new()

func _ready() -> void:
	# Configure the host window at runtime; no project settings are required.
	var window := get_window()
	window.size = Vector2i(1152, 648)
	window.content_scale_size = Vector2i(1152, 648)
	window.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	window.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_KEEP
	window.mode = Window.MODE_FULLSCREEN
	rng.seed = 61016
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 18.0
	camera.position = Vector3(0, 0, 25)
	camera.current = true
	add_child(camera)
	var environment := WorldEnvironment.new()
	var sky := Environment.new()
	sky.background_mode = Environment.BG_COLOR
	sky.background_color = Color("070b20")
	sky.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	sky.ambient_light_color = Color("6883bc")
	sky.ambient_light_energy = 0.65
	environment.environment = sky
	add_child(environment)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-28, -30, -25)
	light.light_color = Color("b6dbff")
	light.light_energy = 1.5
	add_child(light)
	for i in range(100):
		var star := _sphere(self, Vector3(rng.randf_range(-17, 17), rng.randf_range(-10, 10), rng.randf_range(-8, -4)), rng.randf_range(0.018, 0.055), Color("8eaede"), true)
		star.name = "Star%d" % i
	_build_ship()
	_build_hud()
	_spawn_formation()

func _material(color: Color, emissive: bool = false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = 0.35
	material.roughness = 0.4
	if emissive:
		material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return material

func _mesh(parent: Node3D, mesh: Mesh, position: Vector3, color: Color, emissive: bool = false) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.mesh = mesh
	node.position = position
	node.material_override = _material(color, emissive)
	parent.add_child(node)
	return node

func _box(parent: Node3D, position: Vector3, size: Vector3, color: Color, emissive: bool = false) -> MeshInstance3D:
	var mesh := BoxMesh.new()
	mesh.size = size
	return _mesh(parent, mesh, position, color, emissive)

func _sphere(parent: Node3D, position: Vector3, radius: float, color: Color, emissive: bool = false) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	mesh.radial_segments = 12
	mesh.rings = 6
	return _mesh(parent, mesh, position, color, emissive)

func _build_ship() -> void:
	ship = Node3D.new()
	ship.name = "PlayerShip"
	ship.position = Vector3(0, -6.4, 0)
	add_child(ship)
	_box(ship, Vector3.ZERO, Vector3(0.5, 1.6, 0.5), Color("dfebff"))
	var nose := CylinderMesh.new()
	nose.top_radius = 0.0
	nose.bottom_radius = 0.25
	nose.height = 0.7
	nose.radial_segments = 8
	_mesh(ship, nose, Vector3(0, 1.0, 0), Color("f4f8ff"))
	var canopy := _sphere(ship, Vector3(0, 0.25, 0.33), 0.29, Color("38d9ed"))
	canopy.scale = Vector3(0.75, 1.45, 0.7)
	for side in [-1.0, 1.0]:
		var wing := _box(ship, Vector3(side * 0.7, -0.35, 0), Vector3(1.1, 0.55, 0.16), Color("247ad0"))
		wing.rotation.z = side * 0.35
		_box(ship, Vector3(side * 1.12, -0.13, 0.05), Vector3(0.15, 0.7, 0.24), Color("eef7ff"))
		var engine := _sphere(ship, Vector3(side * 0.27, -1.0, 0), 0.17, Color("54dcff"), true)
		engines.append(engine)
	muzzle = _sphere(ship, Vector3(0, 1.4, 0), 0.23, Color("fff0a0"), true)
	muzzle.visible = false

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	add_child(layer)
	var root := Control.new()
	root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(root)
	var title := Label.new()
	title.text = "GALAGA  /  3D DEMO"
	title.position = Vector2(24, 18)
	title.add_theme_font_size_override("font_size", 22)
	title.modulate = Color("8edaff")
	root.add_child(title)
	score_label = Label.new()
	score_label.position = Vector2(24, 48)
	score_label.add_theme_font_size_override("font_size", 18)
	root.add_child(score_label)
	_update_score()
	var controls := Label.new()
	controls.text = "ARROW KEYS  move     SPACE  shoot"
	controls.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	controls.position = Vector2(24, -36)
	controls.add_theme_font_size_override("font_size", 16)
	controls.modulate = Color("b0c4df")
	root.add_child(controls)

func _spawn_formation() -> void:
	for row in range(2):
		for col in range(4):
			var enemy := Node3D.new()
			enemy.name = "Enemy"
			add_child(enemy)
			var color := Color("ed548d") if row == 0 else Color("b888ff")
			var body := _sphere(enemy, Vector3.ZERO, 0.48, color)
			body.scale = Vector3(1.0, 0.85, 0.7)
			for side in [-1.0, 1.0]:
				var wing := _box(enemy, Vector3(side * 0.52, 0.06, -0.07), Vector3(0.6, 0.65, 0.23), color.darkened(0.2))
				wing.rotation.z = side * -0.45
				_sphere(enemy, Vector3(side * 0.17, -0.18, 0.33), 0.10, Color("ffe87d"), true)
			var origin := Vector3((col - 1.5) * 3.0, 3.0 + row * 2.0, 0)
			enemy.position = origin
			enemies.append({"node": enemy, "origin": origin, "phase": col * 0.7 + row * 1.3})

func _process(delta: float) -> void:
	elapsed += delta
	var direction := Vector2(float(Input.is_key_pressed(KEY_RIGHT)) - float(Input.is_key_pressed(KEY_LEFT)), float(Input.is_key_pressed(KEY_UP)) - float(Input.is_key_pressed(KEY_DOWN)))
	direction = direction.limit_length(1.0)
	ship.position.x = clampf(ship.position.x + direction.x * 9.0 * delta, -11.8, 11.8)
	ship.position.y = clampf(ship.position.y + direction.y * 9.0 * delta, -7.2, -2.2)
	ship.rotation.y = lerpf(ship.rotation.y, direction.x * 0.3, minf(delta * 10.0, 1.0))
	ship.rotation.z = lerpf(ship.rotation.z, -direction.x * 0.12, minf(delta * 10.0, 1.0))
	for engine in engines:
		engine.scale = Vector3(1, 1.5 + sin(elapsed * 40.0) * 0.4, 1)
	fire_timer -= delta
	muzzle.visible = fire_timer > 0.10
	if Input.is_key_pressed(KEY_SPACE) and fire_timer <= 0.0:
		_fire()
	for enemy in enemies:
		var node: Node3D = enemy["node"]
		var phase: float = enemy["phase"]
		node.position = enemy["origin"] + Vector3(sin(elapsed * 1.25 + phase) * 1.1, cos(elapsed * 1.7 + phase) * 0.25, sin(elapsed + phase) * 0.25)
		node.rotation.y = sin(elapsed * 2.0 + phase) * 0.3
	_update_shots(delta)
	_update_sparks(delta)
	if enemies.is_empty():
		respawn_timer += delta
		if respawn_timer > 1.3:
			respawn_timer = 0.0
			_spawn_formation()

func _fire() -> void:
	fire_timer = 0.16
	muzzle.visible = true
	var shot := _box(self, ship.position + Vector3(0, 1.3, 0.05), Vector3(0.10, 0.85, 0.10), Color("9df8ff"), true)
	_box(shot, Vector3(0, -0.3, 0), Vector3(0.23, 0.5, 0.08), Color("258bd7"), true)
	shots.append({"node": shot})

func _update_shots(delta: float) -> void:
	for i in range(shots.size() - 1, -1, -1):
		var shot: Node3D = shots[i]["node"]
		shot.position.y += 22.0 * delta
		var hit := false
		for j in range(enemies.size() - 1, -1, -1):
			var enemy: Node3D = enemies[j]["node"]
			# Swept vertical segment prevents fast shots skipping a target.
			var previous_y := shot.position.y - 22.0 * delta
			if absf(shot.position.x - enemy.position.x) < 0.8 and previous_y < enemy.position.y + 0.65 and shot.position.y > enemy.position.y - 0.65:
				_explode(enemy.position)
				enemy.queue_free()
				enemies.remove_at(j)
				score += 100
				_update_score()
				hit = true
				break
		if hit or shot.position.y > 10.0:
			shot.queue_free()
			shots.remove_at(i)

func _explode(position_at_hit: Vector3) -> void:
	for i in range(12):
		var particle := _box(self, position_at_hit, Vector3.ONE * rng.randf_range(0.08, 0.22), Color("fff2a6") if i % 2 == 0 else Color("ff7769"), true)
		var velocity := Vector3(rng.randf_range(-4, 4), rng.randf_range(-4, 4), rng.randf_range(-1, 2))
		sparks.append({"node": particle, "velocity": velocity, "life": rng.randf_range(0.25, 0.65)})

func _update_sparks(delta: float) -> void:
	for i in range(sparks.size() - 1, -1, -1):
		var spark: Dictionary = sparks[i]
		spark["life"] -= delta
		var node: Node3D = spark["node"]
		if spark["life"] <= 0.0:
			node.queue_free()
			sparks.remove_at(i)
		else:
			node.position += spark["velocity"] * delta
			node.rotate_z(delta * 4.0)
			node.scale = Vector3.ONE * minf(1.0, float(spark["life"]) * 4.0)

func _update_score() -> void:
	score_label.text = "SCORE  %04d" % score
