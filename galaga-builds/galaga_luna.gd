extends Node3D
## A compact, self-contained 3D Galaga demo.

const PLAYER_SPEED := 9.0
const PLAYER_MIN_X := -9.2
const PLAYER_MAX_X := 9.2
const PLAYER_MIN_Y := -5.5
const PLAYER_MAX_Y := -2.7
const SHOT_INTERVAL := 0.22
const SHOT_SPEED := 18.0

const CYAN := Color(0.24, 0.92, 1.0)
const GOLD := Color(1.0, 0.72, 0.25)
const ORANGE := Color(1.0, 0.36, 0.22)
const WHITE := Color(0.88, 0.96, 1.0)

var _player: Node3D
var _score_label: Label
var _bullets: Array[Dictionary] = []
var _enemies: Array[Dictionary] = []
var _effects: Array[Dictionary] = []
var _shot_mesh: BoxMesh
var _spark_mesh: SphereMesh
var _shot_material: StandardMaterial3D
var _spark_material: StandardMaterial3D
var _elapsed := 0.0
var _shot_timer := 0.0
var _score := 0

func _ready() -> void:
	_build_world()
	_build_camera()
	_build_backdrop()
	_build_player()
	_build_hud()
	_build_enemies()
	_refresh_hud()

func _process(delta: float) -> void:
	_elapsed += delta
	_shot_timer = maxf(0.0, _shot_timer - delta)
	_move_player(delta)
	_animate_enemies()
	_move_bullets(delta)
	_update_effects(delta)
	if Input.is_key_pressed(KEY_SPACE) and _shot_timer <= 0.0:
		_fire_shot()

func _build_world() -> void:
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.018, 0.028, 0.075)
	world.environment = environment
	add_child(world)

	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-18.0, -12.0, 0.0)
	light.light_energy = 0.65
	add_child(light)

	_shot_mesh = BoxMesh.new()
	_shot_mesh.size = Vector3(0.075, 0.5, 0.09)
	_spark_mesh = SphereMesh.new()
	_spark_mesh.radius = 0.075
	_spark_mesh.height = 0.15
	_shot_material = _make_material(CYAN, 2.4)
	_spark_material = _make_material(GOLD, 2.0)

func _build_camera() -> void:
	var camera := Camera3D.new()
	camera.name = "GalagaCamera"
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 13.0
	camera.position = Vector3(0.0, 0.0, 24.0)
	camera.current = true
	add_child(camera)

func _build_backdrop() -> void:
	var star_mesh := BoxMesh.new()
	star_mesh.size = Vector3(0.035, 0.035, 0.025)
	star_mesh.material = _make_material(Color(0.28, 0.46, 0.82), 0.7)
	for i in 42:
		var star := MeshInstance3D.new()
		star.mesh = star_mesh
		star.position = Vector3(
			fposmod(float(i) * 7.13, 20.4) - 10.2,
			fposmod(float(i) * 3.77, 12.2) - 6.1,
			-2.5 - fposmod(float(i) * 0.17, 1.4))
		add_child(star)

func _build_player() -> void:
	_player = Node3D.new()
	_player.name = "PlayerShip"
	_player.position = Vector3(0.0, -4.65, 0.0)
	add_child(_player)

	var hull := CylinderMesh.new()
	hull.radial_segments = 4
	hull.rings = 1
	hull.top_radius = 0.0
	hull.bottom_radius = 0.48
	hull.height = 1.0
	hull.material = _make_material(CYAN, 1.2)
	var hull_node := MeshInstance3D.new()
	hull_node.mesh = hull
	hull_node.position = Vector3(0.0, 0.0, 0.04)
	_player.add_child(hull_node)

	var wing_mesh := BoxMesh.new()
	wing_mesh.size = Vector3(0.32, 0.62, 0.22)
	wing_mesh.material = _make_material(Color(0.12, 0.44, 0.78), 0.8)
	for side in [-1.0, 1.0]:
		var wing := MeshInstance3D.new()
		wing.mesh = wing_mesh
		wing.position = Vector3(side * 0.48, -0.12, 0.0)
		wing.rotation.z = side * -0.22
		_player.add_child(wing)

	var engine := MeshInstance3D.new()
	var engine_mesh := SphereMesh.new()
	engine_mesh.radius = 0.16
	engine_mesh.height = 0.3
	engine_mesh.material = _make_material(ORANGE, 2.0)
	engine.mesh = engine_mesh
	engine.position = Vector3(0.0, -0.48, 0.0)
	_player.add_child(engine)

func _build_hud() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 5
	add_child(layer)

	_score_label = Label.new()
	_score_label.position = Vector2(20.0, 16.0)
	_score_label.add_theme_font_size_override("font_size", 20)
	_score_label.add_theme_color_override("font_color", WHITE)
	layer.add_child(_score_label)

	var hint := Label.new()
	hint.text = "ARROWS  MOVE     SPACE  FIRE"
	hint.set_anchors_preset(Control.PRESET_CENTER_BOTTOM)
	hint.position = Vector2(-170.0, -42.0)
	hint.size = Vector2(340.0, 28.0)
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.add_theme_font_size_override("font_size", 15)
	hint.add_theme_color_override("font_color", Color(0.54, 0.72, 0.92))
	layer.add_child(hint)

func _build_enemies() -> void:
	for i in 8:
		var enemy := _make_enemy()
		var row := i / 4
		var column := i % 4
		var home := Vector3(-3.9 + float(column) * 2.6, 3.75 - float(row) * 1.5, 0.0)
		enemy.position = home
		add_child(enemy)
		_enemies.append({"node": enemy, "home": home, "phase": float(i) * 0.73})

func _make_enemy() -> Node3D:
	var enemy := Node3D.new()
	var body_mesh := SphereMesh.new()
	body_mesh.radius = 0.39
	body_mesh.height = 0.55
	body_mesh.material = _make_material(ORANGE, 0.75)
	var body := MeshInstance3D.new()
	body.mesh = body_mesh
	enemy.add_child(body)

	var fin_mesh := BoxMesh.new()
	fin_mesh.size = Vector3(0.45, 0.15, 0.24)
	fin_mesh.material = _make_material(Color(0.72, 0.16, 0.32), 0.8)
	for side in [-1.0, 1.0]:
		var fin := MeshInstance3D.new()
		fin.mesh = fin_mesh
		fin.position = Vector3(side * 0.43, -0.04, 0.0)
		fin.rotation.z = side * 0.18
		enemy.add_child(fin)
	return enemy

func _move_player(delta: float) -> void:
	var direction := Vector2.ZERO
	if Input.is_key_pressed(KEY_LEFT):
		direction.x -= 1.0
	if Input.is_key_pressed(KEY_RIGHT):
		direction.x += 1.0
	if Input.is_key_pressed(KEY_UP):
		direction.y += 1.0
	if Input.is_key_pressed(KEY_DOWN):
		direction.y -= 1.0
	if direction.length_squared() > 1.0:
		direction = direction.normalized()
	_player.position.x = clampf(_player.position.x + direction.x * PLAYER_SPEED * delta, PLAYER_MIN_X, PLAYER_MAX_X)
	_player.position.y = clampf(_player.position.y + direction.y * PLAYER_SPEED * delta, PLAYER_MIN_Y, PLAYER_MAX_Y)
	_player.rotation.z = -direction.x * 0.12

func _animate_enemies() -> void:
	for entry in _enemies:
		var enemy: Node3D = entry["node"]
		var home: Vector3 = entry["home"]
		var phase: float = entry["phase"]
		enemy.position.x = home.x + sin(_elapsed * 0.9 + phase) * 0.3
		enemy.position.y = home.y + sin(_elapsed * 1.4 + phase) * 0.08
		enemy.rotation.z = sin(_elapsed + phase) * 0.05

func _fire_shot() -> void:
	_shot_timer = SHOT_INTERVAL
	var shot := MeshInstance3D.new()
	shot.mesh = _shot_mesh
	shot.material_override = _shot_material
	shot.position = _player.position + Vector3(0.0, 0.65, 0.55)
	add_child(shot)
	_bullets.append({"node": shot, "speed": SHOT_SPEED})
	_spawn_flash(shot.position)

func _move_bullets(delta: float) -> void:
	for i in range(_bullets.size() - 1, -1, -1):
		var bullet: Dictionary = _bullets[i]
		var shot: Node3D = bullet["node"]
		shot.position.y += float(bullet["speed"]) * delta
		var hit_index := _find_hit(shot.position)
		if hit_index >= 0:
			var burst_position: Vector3 = _enemies[hit_index]["node"].position
			_enemies[hit_index]["node"].queue_free()
			_enemies.remove_at(hit_index)
			shot.queue_free()
			_bullets.remove_at(i)
			_score += 100
			_spawn_burst(burst_position)
			_refresh_hud()
			continue
		if shot.position.y > 7.0:
			shot.queue_free()
			_bullets.remove_at(i)
func _find_hit(shot_position: Vector3) -> int:
	for i in _enemies.size():
		var enemy: Node3D = _enemies[i]["node"]
		if absf(shot_position.x - enemy.position.x) < 0.52 and absf(shot_position.y - enemy.position.y) < 0.48:
			return i
	return -1

func _spawn_flash(position: Vector3) -> void:
	var flash := MeshInstance3D.new()
	flash.mesh = _spark_mesh
	flash.material_override = _shot_material
	flash.position = position
	flash.scale = Vector3(0.8, 1.7, 0.8)
	add_child(flash)
	_effects.append({"node": flash, "velocity": Vector3.ZERO, "life": 0.08, "size": 1.0})

func _spawn_burst(position: Vector3) -> void:
	for i in 7:
		var angle := TAU * float(i) / 7.0
		var particle := MeshInstance3D.new()
		particle.mesh = _spark_mesh
		particle.material_override = _spark_material
		particle.position = position + Vector3(0.0, 0.0, 0.45)
		add_child(particle)
		var velocity := Vector3(cos(angle), sin(angle), 0.0) * (2.5 + float(i % 3))
		_effects.append({"node": particle, "velocity": velocity, "life": 0.34, "size": 1.0})

func _update_effects(delta: float) -> void:
	for i in range(_effects.size() - 1, -1, -1):
		var effect: Dictionary = _effects[i]
		var node: Node3D = effect["node"]
		var life := float(effect["life"]) - delta
		if life <= 0.0:
			node.queue_free()
			_effects.remove_at(i)
			continue
		node.position += effect["velocity"] * delta
		node.scale = Vector3.ONE * minf(1.0, life * 5.0)
		effect["life"] = life
		_effects[i] = effect

func _refresh_hud() -> void:
	_score_label.text = "GALAGA  //  LUNA          SCORE  %05d" % _score

func _make_material(color: Color, glow: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = glow
	return material
