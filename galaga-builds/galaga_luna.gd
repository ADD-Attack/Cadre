extends Node3D
## A tiny, asset-free arcade shooter. Gameplay is on the XY plane; the camera looks
## straight down -Z so the controls feel like a classic fixed-screen cabinet.

const PLAY_W := 15.2
const PLAY_H := 8.55
const PLAYER_Y := -3.25
const PLAYER_SPEED := 7.4
const SHOT_SPEED := 12.5
const ENEMY_SPEED := 1.05
const PLAYER_HIT_GRACE := 1.35
const DIVE_INTERVAL := 2.7

var _camera: Camera3D
var _player: Node3D
var _shots: Array[Node3D] = []
var _enemies: Array[Dictionary] = []
var _effects: Array[Dictionary] = []
var _stars: Array[Node3D] = []
var _score := 0
var _lives := 3
var _fire_clock := 0.0
var _formation_clock := 0.0
var _wave := 1
var _hud: Label3D
var _banner: Label3D
var _banner_time := 0.0
var _game_over := false
var _player_grace := 0.0
var _player_blink := 0.0
var _dive_clock := 1.8
var _game_clock := 0.0
var _exhaust: MeshInstance3D

func _ready() -> void:
	# This scene is intentionally runnable by itself, without project settings.
	get_window().size = Vector2i(1152, 648)
	get_window().mode = Window.MODE_FULLSCREEN
	_build_world()
	_spawn_formation()
	_show_banner("STARFIGHTER  /  MOVE  ← →  /  FIRE  SPACE", 2.6)

func _build_world() -> void:
	var env := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color("050816")
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("8bb8ff")
	environment.ambient_light_energy = 0.25
	env.environment = environment
	add_child(env)
	_camera = Camera3D.new()
	_camera.position = Vector3(0, 0, 20)
	_camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	_camera.size = PLAY_H
	_camera.current = true
	_camera.fov = 45.0
	add_child(_camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-10, 0, 0)
	light.light_energy = 1.1
	add_child(light)
	_add_box("Arena", Vector3(0, 0, -1.5), Vector3(15.25, 8.6, 0.08), Color("08142b"), 0.15)
	_build_arena_lines()
	_add_box("Lower rail", Vector3(0, -3.85, -0.7), Vector3(15.1, 0.025, 0.03), Color("23d9ff"), 1.4)
	_add_box("Upper rail", Vector3(0, 3.85, -0.7), Vector3(15.1, 0.025, 0.03), Color("572fbd"), 0.8)
	for i in range(82):
		var star := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		var s := randf_range(0.012, 0.036)
		sphere.radius = s
		sphere.height = s * 2.0
		star.mesh = sphere
		star.position = Vector3(randf_range(-7.35, 7.35), randf_range(-3.75, 3.75), -0.8)
		star.material_override = _mat(Color(0.45, 0.72, 1.0, randf_range(0.22, 0.8)), 0.4)
		add_child(star)
		_stars.append(star)
	_player = _make_ship()
	_player.position = Vector3(0, PLAYER_Y, 0.2)
	_exhaust = _make_exhaust()
	_player.add_child(_exhaust)
	add_child(_player)
	_hud = _make_label("SCORE 000000     ♥ ♥ ♥     WAVE 01", Vector3(-7.15, 4.0, 1.5), 30, Color("c7f7ff"), HORIZONTAL_ALIGNMENT_LEFT)
	_banner = _make_label("", Vector3(0, 0.1, 2.0), 48, Color("ffffff"), HORIZONTAL_ALIGNMENT_CENTER)

func _process(delta: float) -> void:
	var dt := minf(delta, 0.05)
	_game_clock += dt
	for star in _stars:
		star.position.y -= dt * 0.12
		if star.position.y < -3.8:
			star.position.y = 3.8
	if _banner_time > 0.0:
		_banner_time -= dt
		_banner.modulate.a = clampf(_banner_time * 1.5, 0.0, 1.0)
	elif _banner_time < 0.0:
		_banner.modulate.a = 1.0
	if _player_grace > 0.0:
		_player_grace = maxf(_player_grace - dt, 0.0)
		if not _game_over:
			_player_blink += dt * 18.0
			_player.visible = fmod(_player_blink, 2.0) < 1.0
			if _player_grace == 0.0:
				_player.visible = true
	if _exhaust != null:
		_exhaust.scale.y = 0.82 + 0.24 * sin(_game_clock * 22.0)
	_update_effects(dt)
	if _game_over:
		if Input.is_key_pressed(KEY_SPACE):
			_restart()
		return
	_read_controls(dt)
	_update_shots(dt)
	_update_enemies(dt)
	_formation_clock += dt
	_dive_clock -= dt
	if _dive_clock <= 0.0 and not _enemies.is_empty():
		_start_enemy_dive()
		_dive_clock = maxf(DIVE_INTERVAL - minf(_wave * 0.12, 0.9), 1.35)
	if _enemies.is_empty() and _formation_clock > 1.1:
		_wave += 1
		_formation_clock = 0.0
		_spawn_formation()
		_show_banner("WAVE %02d" % _wave, 1.25)
	_update_hud()

func _read_controls(dt: float) -> void:
	var direction := 0.0
	if Input.is_key_pressed(KEY_LEFT): direction -= 1.0
	if Input.is_key_pressed(KEY_RIGHT): direction += 1.0
	_player.position.x = clampf(_player.position.x + direction * PLAYER_SPEED * dt, -6.85, 6.85)
	_player.rotation.z = -direction * 0.09
	_fire_clock -= dt
	if Input.is_key_pressed(KEY_SPACE) and _fire_clock <= 0.0:
		_fire_clock = 0.23
		_fire()

func _fire() -> void:
	var shot := Node3D.new()
	shot.position = _player.position + Vector3(0, 0.63, 0.12)
	var bolt := _add_box("Bolt", Vector3.ZERO, Vector3(0.075, 0.48, 0.045), Color("49f6ff"), 2.8, shot)
	bolt.rotation.z = 0.0
	add_child(shot)
	_shots.append(shot)
	_emit_spark(shot.position, Color("61fbff"), 2)

func _update_shots(dt: float) -> void:
	for i in range(_shots.size() - 1, -1, -1):
		var shot := _shots[i]
		shot.position.y += SHOT_SPEED * dt
		var hit_index := -1
		for j in range(_enemies.size()):
			var enemy: Node3D = _enemies[j].node
			if absf(shot.position.x - enemy.position.x) < 0.38 and absf(shot.position.y - enemy.position.y) < 0.34:
				hit_index = j
				break
		if hit_index >= 0:
			var victim: Node3D = _enemies[hit_index].node
			_emit_burst(victim.position, Color("ff68cf") if _enemies[hit_index].kind == 1 else Color("ffc35c"))
			victim.queue_free()
			_enemies.remove_at(hit_index)
			_score += 100
			shot.queue_free()
			_shots.remove_at(i)
		elif shot.position.y > 4.5:
			shot.queue_free()
			_shots.remove_at(i)

func _spawn_formation() -> void:
	var cols := 7
	for row in range(3):
		for col in range(cols):
			var kind := 1 if row == 0 else 0
			var enemy := _make_enemy(kind)
			enemy.position = Vector3((col - (cols - 1) * 0.5) * 1.65, 2.55 - row * 0.82, 0.1)
			add_child(enemy)
			_enemies.append({"node": enemy, "kind": kind, "phase": randf() * TAU, "base_x": enemy.position.x, "base_y": enemy.position.y, "diving": false, "dive_time": 0.0, "dive_duration": 2.2, "dive_start_x": enemy.position.x, "dive_start_y": enemy.position.y, "dive_target_x": enemy.position.x})

func _update_enemies(dt: float) -> void:
	var now := _game_clock
	for i in range(_enemies.size() - 1, -1, -1):
		var data: Dictionary = _enemies[i]
		var enemy: Node3D = data.node
		data.phase += dt
		if data.diving:
			data.dive_time += dt
			var progress: float = minf(data.dive_time / data.dive_duration, 1.0)
			var target_x: float = clampf(data.dive_target_x + sin(data.dive_time * 3.0) * 0.46, -6.7, 6.7)
			enemy.position.x = lerpf(data.dive_start_x, target_x, progress)
			enemy.position.y = data.dive_start_y - data.dive_time * (3.1 + _wave * 0.08)
			enemy.rotation.z = sin(data.dive_time * 4.0) * 0.18
		else:
			enemy.position.x = data.base_x + sin(data.phase * 0.9 + now * 0.3) * 0.34
			enemy.position.y = data.base_y + sin(data.phase * 0.7 + now * 0.4) * 0.13
			enemy.rotation.z = sin(data.phase * 2.0) * 0.08
		_enemies[i] = data
		if enemy.position.distance_to(_player.position) < 0.72:
			_emit_burst(enemy.position, Color("ff496c"))
			enemy.queue_free()
			_enemies.remove_at(i)
			if _player_grace <= 0.0:
				_lose_life()
		elif enemy.position.y < -4.35:
			if data.diving:
				_emit_burst(enemy.position, Color("ff496c"))
				enemy.queue_free()
				_enemies.remove_at(i)
				if _player_grace <= 0.0:
					_lose_life()

func _start_enemy_dive() -> void:
	var candidates: Array[int] = []
	for i in range(_enemies.size()):
		if not _enemies[i].diving:
			candidates.append(i)
	if candidates.is_empty():
		return
	var index: int = candidates[randi_range(0, candidates.size() - 1)]
	var data: Dictionary = _enemies[index]
	data.diving = true
	data.dive_time = 0.0
	data.dive_duration = 2.2
	data.dive_start_x = (_enemies[index].node as Node3D).position.x
	data.dive_start_y = (_enemies[index].node as Node3D).position.y
	data.dive_target_x = _player.position.x
	_enemies[index] = data

func _lose_life() -> void:
	if _player_grace > 0.0 or _game_over:
		return
	_lives = maxi(_lives - 1, 0)
	_player_grace = PLAYER_HIT_GRACE
	_player_blink = 0.0
	_emit_burst(_player.position, Color("4cf3ff"))
	if _lives <= 0:
		_game_over = true
		_player.visible = false
		_show_banner("GAME OVER\nSPACE TO RESTART", -1.0)

func _update_effects(dt: float) -> void:
	for i in range(_effects.size() - 1, -1, -1):
		var e: Dictionary = _effects[i]
		e.time += dt
		var node: Node3D = e.node
		if e.time >= e.life:
			node.queue_free()
			_effects.remove_at(i)
		else:
			node.scale = Vector3.ONE * (1.0 + e.time * 2.3)
			var material := node.get_child(0).material_override as StandardMaterial3D
			var tint := material.albedo_color
			tint.a = 1.0 - e.time / e.life
			material.albedo_color = tint
			_effects[i] = e

func _emit_burst(pos: Vector3, color: Color) -> void:
	for n in range(9):
		var puff := Node3D.new()
		puff.position = pos + Vector3(randf_range(-0.16, 0.16), randf_range(-0.16, 0.16), 0.3)
		var core := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = randf_range(0.045, 0.09)
		sphere.height = sphere.radius * 2.0
		core.mesh = sphere
		core.material_override = _mat(color, 2.0, true)
		puff.add_child(core)
		add_child(puff)
		_effects.append({"node": puff, "time": 0.0, "life": randf_range(0.18, 0.38)})

func _emit_spark(pos: Vector3, color: Color, count: int) -> void:
	for n in range(count):
		var puff := Node3D.new()
		puff.position = pos + Vector3(randf_range(-0.09, 0.09), randf_range(-0.04, 0.04), 0.25)
		var dot := MeshInstance3D.new()
		var sphere := SphereMesh.new()
		sphere.radius = 0.035
		sphere.height = 0.07
		dot.mesh = sphere
		dot.material_override = _mat(color, 3.0, true)
		puff.add_child(dot)
		add_child(puff)
		_effects.append({"node": puff, "time": 0.0, "life": 0.12})

func _build_arena_lines() -> void:
	for x in range(-6, 7):
		_add_box("Grid vertical", Vector3(x * 1.08, 0, -1.405), Vector3(0.008, 7.55, 0.008), Color("102345"), 0.0)
	for y in range(-3, 4):
		_add_box("Grid horizontal", Vector3(0, y * 1.05, -1.405), Vector3(14.2, 0.008, 0.008), Color("102345"), 0.0)
	for x in [-1.0, 1.0]:
		_add_box("Pilot console", Vector3(x * 5.6, -3.55, -1.38), Vector3(1.35, 0.045, 0.025), Color("23577a"), 0.5)

func _make_exhaust() -> MeshInstance3D:
	var flame := _polygon_mesh("Ion exhaust", [Vector3(-0.15, -0.30, 0), Vector3(0, -0.88, 0), Vector3(0.15, -0.30, 0)], Color("ff9b4a"), 2.2)
	flame.position = Vector3(0, -0.22, -0.03)
	return flame

func _make_ship() -> Node3D:
	var ship := Node3D.new()
	var body := _polygon_mesh("Ship body", [Vector3(0, 0.68, 0), Vector3(-0.21, 0.22, 0), Vector3(-0.60, -0.34, 0), Vector3(-0.56, -0.46, 0), Vector3(-0.11, -0.28, 0), Vector3(0, -0.50, 0), Vector3(0.11, -0.28, 0), Vector3(0.56, -0.46, 0), Vector3(0.60, -0.34, 0), Vector3(0.21, 0.22, 0)], Color("35dcff"), 1.5)
	ship.add_child(body)
	var cockpit := _make_sphere("Cockpit", Vector3(0, 0.12, 0.08), Vector3(0.13, 0.24, 0.11), Color("f3ffff"), 1.8)
	ship.add_child(cockpit)
	var wing_l := _add_box("Wing light L", Vector3(-0.38, -0.28, 0.07), Vector3(0.12, 0.035, 0.035), Color("ff68c9"), 1.8, ship)
	var wing_r := _add_box("Wing light R", Vector3(0.38, -0.28, 0.07), Vector3(0.12, 0.035, 0.035), Color("ff68c9"), 1.8, ship)
	return ship

func _make_enemy(kind: int) -> Node3D:
	var enemy := Node3D.new()
	var color := Color("ff58c7") if kind == 1 else Color("ffad52")
	var points := [Vector3(0, -0.36, 0), Vector3(-0.12, -0.08, 0), Vector3(-0.5, 0.05, 0), Vector3(-0.58, 0.22, 0), Vector3(-0.3, 0.16, 0), Vector3(-0.18, 0.44, 0), Vector3(0, 0.3, 0), Vector3(0.18, 0.44, 0), Vector3(0.3, 0.16, 0), Vector3(0.58, 0.22, 0), Vector3(0.5, 0.05, 0), Vector3(0.12, -0.08, 0)]
	enemy.add_child(_polygon_mesh("Enemy shell", points, color, 1.1))
	enemy.add_child(_make_sphere("Eye L", Vector3(-0.14, 0.06, 0.08), Vector3(0.07, 0.09, 0.06), Color("ffffff"), 1.0))
	enemy.add_child(_make_sphere("Eye R", Vector3(0.14, 0.06, 0.08), Vector3(0.07, 0.09, 0.06), Color("ffffff"), 1.0))
	return enemy

func _polygon_mesh(label: String, points: Array[Vector3], color: Color, glow: float) -> MeshInstance3D:
	var st := SurfaceTool.new()
	st.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in range(1, points.size() - 1):
		st.set_color(color)
		st.add_vertex(points[0])
		st.set_color(color.lightened(0.18))
		st.add_vertex(points[i])
		st.set_color(color.darkened(0.14))
		st.add_vertex(points[i + 1])
	st.generate_normals()
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = st.commit()
	instance.material_override = _mat(color, glow, true)
	return instance

func _add_box(label: String, pos: Vector3, size: Vector3, color: Color, glow: float, parent: Node = self) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	var box := BoxMesh.new()
	box.size = size
	instance.mesh = box
	instance.position = pos
	instance.material_override = _mat(color, glow, true)
	parent.add_child(instance)
	return instance

func _make_sphere(label: String, pos: Vector3, size: Vector3, color: Color, glow: float) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	var sphere := SphereMesh.new()
	sphere.radius = 0.5
	sphere.height = 1.0
	instance.mesh = sphere
	instance.position = pos
	instance.scale = size
	instance.material_override = _mat(color, glow, true)
	return instance

func _mat(color: Color, glow: float, transparent := false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.emission_enabled = glow > 0.0
	material.emission = color
	material.emission_energy_multiplier = glow
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA if transparent else BaseMaterial3D.TRANSPARENCY_DISABLED
	material.depth_draw_mode = BaseMaterial3D.DEPTH_DRAW_DISABLED if transparent else BaseMaterial3D.DEPTH_DRAW_OPAQUE_ONLY
	return material

func _make_label(text: String, pos: Vector3, size: int, color: Color, align: HorizontalAlignment) -> Label3D:
	var label := Label3D.new()
	label.text = text
	label.position = pos
	label.font_size = size
	label.pixel_size = 0.0045
	label.modulate = color
	label.horizontal_alignment = align
	label.shaded = false
	label.no_depth_test = true
	label.outline_size = 4
	label.outline_modulate = Color("10233d")
	add_child(label)
	return label

func _update_hud() -> void:
	var hearts := "♥ ".repeat(maxi(_lives, 0)).strip_edges()
	_hud.text = "SCORE %06d     %s     WAVE %02d" % [_score, hearts, _wave]

func _show_banner(text: String, duration: float) -> void:
	_banner.text = text
	_banner_time = duration
	_banner.modulate.a = 1.0

func _restart() -> void:
	for e in _enemies: (e.node as Node3D).queue_free()
	for shot in _shots: shot.queue_free()
	for effect in _effects: (effect.node as Node3D).queue_free()
	_enemies.clear()
	_shots.clear()
	_effects.clear()
	_score = 0
	_lives = 3
	_wave = 1
	_game_over = false
	_player_grace = 0.0
	_dive_clock = 1.8
	_fire_clock = 0.0
	_player.visible = true
	_player.position = Vector3(0, PLAYER_Y, 0.2)
	_spawn_formation()
	_show_banner("STARFIGHTER  /  MOVE  ← →  /  FIRE  SPACE", 2.0)
