extends Node3D

const GRID_SIZE := 17
const TILE := 1.2
const CENTER := 8
const APPLES_TO_LEVEL := 15
const HIGH_SCORE_PATH := "user://highscore.cfg"

const CYAN := Color("#13d9ff")
const GREEN := Color("#7dff76")
const GOLD := Color("#ffc83d")
const BG := Color("#071321")

var rng := RandomNumberGenerator.new()
var snake: Array[Vector2i] = []
var direction := Vector2i.RIGHT
var queued_direction := Vector2i.RIGHT
var obstacles: Array[Vector2i] = []
var apple := Vector2i.ZERO
var score := 0
var high_score := 0
var apples := 0
var level := 1
var elapsed := 0.0
var step_clock := 0.0
var level_clock := 0.0
var combo := 0
var last_apple_time := -INF
var state := "title"
var paused := false
var rng_seed := 0

var arena_root: Node3D
var snake_root: Node3D
var apple_root: Node3D
var camera: Camera3D
var overlay: ColorRect
var title_label: Label
var subtitle_label: Label
var hud_label: Label
var time_level_label: Label
var score_high_label: Label
var apples_label: Label
var combo_label: Label
var combo_bar_fill: ColorRect
var progress_fill: ColorRect
var apple_fruit: MeshInstance3D
var warning_lights: Array[MeshInstance3D] = []
var objective_label: Label
var pause_label: Label
var hud_layer: CanvasLayer


func _ready() -> void:
	rng_seed = int(Time.get_unix_time_from_system()) ^ int(Time.get_ticks_usec())
	rng.seed = rng_seed
	_load_high_score()
	_build_world()
	_build_ui()
	_set_screen("title")


func _process(delta: float) -> void:
	if state == "playing" and not paused:
		elapsed += delta
		if combo > 0 and elapsed - last_apple_time > 4.0:
			combo = 0
		step_clock += delta
		while step_clock >= _step_interval():
			step_clock -= _step_interval()
			_advance_snake()
			if state != "playing":
				break
	elif state == "level_complete":
		level_clock += delta
		if level_clock >= 2.0:
			_begin_level_two()
	if apple_fruit != null and is_instance_valid(apple_fruit):
		var shimmer := 1.0 + sin(Time.get_ticks_msec() * 0.003) * 0.035
		apple_fruit.scale = Vector3(shimmer, 1.0 / shimmer, shimmer)
	for i in range(warning_lights.size()):
		warning_lights[i].scale = Vector3.ONE * (0.8 + 0.35 * (0.5 + 0.5 * sin(elapsed * 2.4 + float(i))))
	_update_hud()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var key := event as InputEventKey
		if state == "title" and (key.keycode == KEY_ENTER or key.keycode == KEY_KP_ENTER):
			_start_game()
			return
		if (state == "game_over" or state == "level_complete") and (key.keycode == KEY_ENTER or key.keycode == KEY_KP_ENTER):
			_start_game()
			return
		if state == "playing":
			if key.keycode == KEY_ESCAPE or key.keycode == KEY_P:
				paused = not paused
				pause_label.visible = paused
				return
			var candidate := Vector2i.ZERO
			match key.keycode:
				KEY_UP, KEY_W: candidate = Vector2i.UP
				KEY_DOWN, KEY_S: candidate = Vector2i.DOWN
				KEY_LEFT, KEY_A: candidate = Vector2i.LEFT
				KEY_RIGHT, KEY_D: candidate = Vector2i.RIGHT
			if candidate != Vector2i.ZERO and candidate != -direction:
				queued_direction = candidate
	elif event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT:
		if state == "title" or state == "game_over" or state == "level_complete":
			_start_game()


func _build_world() -> void:
	var world := WorldEnvironment.new()
	var environment := Environment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = BG
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("#a1c4dc")
	environment.ambient_light_energy = 1.15
	environment.fog_enabled = true
	environment.fog_light_color = Color("#789bad")
	environment.fog_density = 0.0035
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	world.environment = environment
	add_child(world)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-52, -28, 0)
	sun.light_color = Color("#c5e9ff")
	sun.light_energy = 1.8
	sun.shadow_enabled = true
	add_child(sun)

	camera = Camera3D.new()
	camera.position = Vector3(15.5, 20.5, 22.5)
	camera.current = true
	camera.fov = 46
	add_child(camera)
	camera.look_at(Vector3.ZERO, Vector3.UP)

	arena_root = Node3D.new()
	arena_root.name = "Arena"
	add_child(arena_root)
	_build_arena()

	snake_root = Node3D.new()
	snake_root.name = "Snake"
	add_child(snake_root)
	apple_root = Node3D.new()
	apple_root.name = "Apple"
	add_child(apple_root)


func _build_arena() -> void:
	var floor_mesh := BoxMesh.new()
	floor_mesh.size = Vector3(GRID_SIZE * TILE, 0.25, GRID_SIZE * TILE)
	_add_mesh(arena_root, floor_mesh, Vector3(0, -0.2, 0), _material(Color("#30495d"), 0.65, 0.4))
	var under_mesh := BoxMesh.new()
	under_mesh.size = Vector3(GRID_SIZE * TILE + 1.0, 0.45, GRID_SIZE * TILE + 1.0)
	_add_mesh(arena_root, under_mesh, Vector3(0, -0.58, 0), _material(Color("#142638"), 0.55, 0.6))
	# Fine metal grid lines and luminous perimeter inlays.
	for i in range(GRID_SIZE + 1):
		var offset := (float(i) - CENTER) * TILE - TILE * 0.5
		var line_mesh := BoxMesh.new()
		line_mesh.size = Vector3(0.018, 0.014, GRID_SIZE * TILE)
		_add_mesh(arena_root, line_mesh, Vector3(offset, -0.064, 0), _glow_material(Color("#54819a"), 0.48))
		var cross_mesh := BoxMesh.new()
		cross_mesh.size = Vector3(GRID_SIZE * TILE, 0.014, 0.018)
		_add_mesh(arena_root, cross_mesh, Vector3(0, -0.064, offset), _glow_material(Color("#54819a"), 0.48))
	var span := GRID_SIZE * TILE
	for edge in [-1, 1]:
		var wall := BoxMesh.new()
		wall.size = Vector3(span + 0.48, 1.25, 0.42)
		_add_mesh(arena_root, wall, Vector3(0, 0.5, edge * (span * 0.5 + 0.03)), _material(Color("#29485f"), 0.42, 0.38))
		_add_mesh(arena_root, _box(Vector3(span + 0.52, 0.055, 0.48)), Vector3(0, 1.15, edge * (span * 0.5 + 0.03)), _glow_material(CYAN, 4.0))
		var side_wall := BoxMesh.new()
		side_wall.size = Vector3(0.42, 1.25, span + 0.48)
		_add_mesh(arena_root, side_wall, Vector3(edge * (span * 0.5 + 0.03), 0.5, 0), _material(Color("#29485f"), 0.42, 0.38))
		_add_mesh(arena_root, _box(Vector3(0.48, 0.055, span + 0.52)), Vector3(edge * (span * 0.5 + 0.03), 1.15, 0), _glow_material(CYAN, 4.0))
	# Eight fixed crates leave a generous opening around the spawn lane.
	obstacles = [Vector2i(-5, -4), Vector2i(-5, -3), Vector2i(5, -4), Vector2i(5, -3), Vector2i(-5, 4), Vector2i(-5, 5), Vector2i(5, 4), Vector2i(5, 5)]
	for cell in obstacles:
		var crate := BoxMesh.new()
		crate.size = Vector3(TILE * 0.82, 0.82, TILE * 0.82)
		var pos := _cell_to_world(cell)
		_add_mesh(arena_root, crate, pos + Vector3(0, 0.43, 0), _material(Color("#526778"), 0.72, 0.3))
		_add_mesh(arena_root, _box(Vector3(TILE * 0.84, 0.045, TILE * 0.84)), pos + Vector3(0, 0.86, 0), _glow_material(Color("#36a0bd"), 1.8))
		_add_mesh(arena_root, _box(Vector3(TILE * 0.7, 0.04, 0.08)), pos + Vector3(0, 0.88, 0), _material(Color("#536c79"), 0.7, 0.25))

	_build_industrial_details(span)


func _build_industrial_details(span: float) -> void:
	# Alternating hazard bands across the inside face of the four arena walls.
	for edge in [-1.0, 1.0]:
		for i in range(19):
			var stripe_color := Color("#ffd34e") if i % 2 == 0 else Color("#18232d")
			var x := -10.2 + float(i) * 1.14
			_add_mesh(arena_root, _box(Vector3(0.55, 0.09, 0.035)), Vector3(x, 0.96, edge * 10.12), _material(stripe_color, 0.3, 0.45))
			_add_mesh(arena_root, _box(Vector3(0.035, 0.09, 0.55)), Vector3(edge * 10.12, 0.96, x), _material(stripe_color, 0.3, 0.45))
	# Pipe runs and industrial drums sit beyond the playable wall.
	for side in [-1.0, 1.0]:
		var pipe_mesh := CylinderMesh.new()
		pipe_mesh.top_radius = 0.105
		pipe_mesh.bottom_radius = 0.105
		pipe_mesh.height = span - 2.0
		var pipe := _add_mesh(arena_root, pipe_mesh, Vector3(side * 11.2, 0.18, 0), _material(Color("#546c7c"), 0.75, 0.32))
		pipe.rotation.x = PI / 2.0
		for z in [-6.0, 0.0, 6.0]:
			var barrel_mesh := CylinderMesh.new()
			barrel_mesh.top_radius = 0.43
			barrel_mesh.bottom_radius = 0.43
			barrel_mesh.height = 1.05
			var barrel_x: float = side * 11.65
			_add_mesh(arena_root, barrel_mesh, Vector3(barrel_x, 0.52, z), _material(Color("#526879"), 0.72, 0.35))
			var band := TorusMesh.new()
			band.inner_radius = 0.36
			band.outer_radius = 0.42
			var band_node := _add_mesh(arena_root, band, Vector3(barrel_x, 0.52, z), _material(Color("#899ba5"), 0.8, 0.28))
			band_node.rotation.x = PI / 2.0
	# Red beacons identify the four wall corners.
	for x in [-10.35, 10.35]:
		for z in [-10.35, 10.35]:
			var beacon := _sphere(arena_root, Vector3(x, 1.42, z), 0.13, _glow_material(Color("#ff334a"), 2.8))
			warning_lights.append(beacon)
			var point := OmniLight3D.new()
			point.position = Vector3(x, 1.4, z)
			point.light_color = Color("#ff304a")
			point.light_energy = 1.3
			point.omni_range = 2.8
			arena_root.add_child(point)


func _sphere(parent: Node3D, pos: Vector3, radius: float, material: Material) -> MeshInstance3D:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = radius * 2.0
	return _add_mesh(parent, mesh, pos, material)


func _build_ui() -> void:
	hud_layer = CanvasLayer.new()
	add_child(hud_layer)
	var topbar := ColorRect.new()
	topbar.color = Color(0.012, 0.027, 0.045, 0.96)
	topbar.position = Vector2(0, 0)
	topbar.size = Vector2(1280, 94)
	hud_layer.add_child(topbar)
	var left_panel := _panel(Vector2(18, 10), Vector2(326, 74))
	var center_panel := _panel(Vector2(357, 10), Vector2(550, 74))
	var right_panel := _panel(Vector2(921, 10), Vector2(341, 74))
	hud_layer.add_child(left_panel)
	hud_layer.add_child(center_panel)
	hud_layer.add_child(right_panel)
	time_level_label = _label("TIME 00:00     •     LEVEL 1", 20, Color("#e8f7ff"), Vector2(34, 22), Vector2(294, 42), HORIZONTAL_ALIGNMENT_CENTER)
	hud_layer.add_child(time_level_label)
	score_high_label = _label("SCORE 000000    •    HIGH 000000", 20, Color("#fff0bb"), Vector2(372, 20), Vector2(520, 36), HORIZONTAL_ALIGNMENT_CENTER)
	hud_layer.add_child(score_high_label)
	combo_label = _label("COMBO x2  •  4.0s", 17, Color("#7dffb6"), Vector2(372, 53), Vector2(520, 25), HORIZONTAL_ALIGNMENT_CENTER)
	hud_layer.add_child(combo_label)
	hud_label = score_high_label # Preserve the Wave 1 public HUD reference.
	var apple_text := _label("APPLES 00/15   •   0%", 17, Color("#ffe59a"), Vector2(936, 14), Vector2(310, 28), HORIZONTAL_ALIGNMENT_CENTER)
	hud_layer.add_child(apple_text)
	apples_label = apple_text
	var progress_track := ColorRect.new()
	progress_track.color = Color("#233b4c")
	progress_track.position = Vector2(948, 55)
	progress_track.size = Vector2(288, 9)
	hud_layer.add_child(progress_track)
	progress_fill = ColorRect.new()
	progress_fill.color = Color("#5de5b1")
	progress_fill.size = Vector2(0, 9)
	progress_track.add_child(progress_fill)
	var combo_track := ColorRect.new()
	combo_track.color = Color("#183d38")
	combo_track.position = Vector2(500, 80)
	combo_track.size = Vector2(264, 5)
	hud_layer.add_child(combo_track)
	combo_bar_fill = ColorRect.new()
	combo_bar_fill.color = Color("#65ffac")
	combo_bar_fill.size = Vector2(0, 5)
	combo_track.add_child(combo_bar_fill)
	var bottom := ColorRect.new()
	bottom.color = Color(0.012, 0.027, 0.045, 0.96)
	bottom.position = Vector2(0, 656)
	bottom.size = Vector2(1280, 64)
	hud_layer.add_child(bottom)
	objective_label = _label("COLLECT 15 APPLES     •     ARROWS / WASD MOVE     •     ESC / P PAUSE", 17, Color("#a5c6d8"), Vector2(32, 670), Vector2(1216, 34), HORIZONTAL_ALIGNMENT_CENTER)
	hud_layer.add_child(objective_label)
	var dim := ColorRect.new()
	dim.color = Color(0.01, 0.025, 0.045, 0.72)
	dim.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	dim.offset_top = 94
	dim.offset_bottom = -64
	hud_layer.add_child(dim)
	overlay = dim
	title_label = _label("TRIPLE AAA SNAKE", 58, Color("#eaf8ff"), Vector2(0, 238), Vector2(1280, 80), HORIZONTAL_ALIGNMENT_CENTER)
	title_label.add_theme_color_override("font_shadow_color", Color("#0bdbff"))
	title_label.add_theme_constant_override("shadow_offset_x", 0)
	title_label.add_theme_constant_override("shadow_offset_y", 0)
	title_label.add_theme_constant_override("shadow_outline_size", 2)
	hud_layer.add_child(title_label)
	subtitle_label = _label("CLICK OR PRESS ENTER TO START", 23, Color("#82eaff"), Vector2(0, 337), Vector2(1280, 48), HORIZONTAL_ALIGNMENT_CENTER)
	hud_layer.add_child(subtitle_label)
	pause_label = _label("PAUSED", 46, Color("#eaf8ff"), Vector2(0, 306), Vector2(1280, 64), HORIZONTAL_ALIGNMENT_CENTER)
	pause_label.visible = false
	hud_layer.add_child(pause_label)


func _panel(pos: Vector2, size: Vector2) -> ColorRect:
	var panel := ColorRect.new()
	panel.position = pos
	panel.size = size
	panel.color = Color(0.06, 0.11, 0.15, 0.94)
	return panel

func _start_game() -> void:
	score = 0
	apples = 0
	combo = 0
	last_apple_time = -INF
	level = 1
	elapsed = 0.0
	step_clock = 0.0
	paused = false
	state = "playing"
	snake = [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(-2, 0)]
	direction = Vector2i.RIGHT
	queued_direction = direction
	_spawn_apple()
	_render_snake()
	_set_screen("playing")


func _begin_level_two() -> void:
	level = 2
	combo = 0
	last_apple_time = -INF
	apples = 0
	step_clock = 0.0
	snake = [Vector2i(0, 0), Vector2i(-1, 0), Vector2i(-2, 0)]
	direction = Vector2i.RIGHT
	queued_direction = direction
	_spawn_apple()
	_render_snake()
	state = "playing"
	_set_screen("playing")


func _advance_snake() -> void:
	direction = queued_direction
	var next := snake[0] + direction
	if abs(next.x) > CENTER or abs(next.y) > CENTER or obstacles.has(next):
		_end_game()
		return
	var eating := next == apple
	if snake.has(next) and not (next == snake[-1] and not eating):
		_end_game()
		return
	snake.push_front(next)
	if eating:
		if elapsed - last_apple_time <= 4.0:
			combo += 1
		else:
			combo = 1
		last_apple_time = elapsed
		_spawn_eat_sparkles(_cell_to_world(apple) + Vector3(0, 0.32, 0))
		score += 100 * combo
		apples += 1
		if score > high_score:
			high_score = score
			_save_high_score()
		if apples >= APPLES_TO_LEVEL and level == 1:
			state = "level_complete"
			level_clock = 0.0
			_set_screen("level_complete")
		else:
			_spawn_apple()
	else:
		snake.pop_back()
	_render_snake()


func _spawn_apple() -> void:
	var free_cells: Array[Vector2i] = []
	for x in range(-CENTER, CENTER + 1):
		for y in range(-CENTER, CENTER + 1):
			var cell := Vector2i(x, y)
			if not snake.has(cell) and not obstacles.has(cell):
				free_cells.append(cell)
	if free_cells.is_empty():
		return
	apple = free_cells[rng.randi_range(0, free_cells.size() - 1)]
	for child in apple_root.get_children():
		child.queue_free()
	var at := _cell_to_world(apple)
	var pedestal := CylinderMesh.new()
	pedestal.top_radius = 0.31
	pedestal.bottom_radius = 0.4
	pedestal.height = 0.16
	_add_mesh(apple_root, pedestal, at + Vector3(0, 0.08, 0), _material(Color("#596776"), 0.82, 0.27))
	var pedestal_ring := TorusMesh.new()
	pedestal_ring.inner_radius = 0.29
	pedestal_ring.outer_radius = 0.36
	var pedestal_ring_node := _add_mesh(apple_root, pedestal_ring, at + Vector3(0, 0.17, 0), _glow_material(GOLD, 3.8))
	pedestal_ring_node.rotation.x = PI / 2.0
	var fruit := SphereMesh.new()
	fruit.radius = 0.32
	fruit.height = 0.64
	apple_fruit = _add_mesh(apple_root, fruit, at + Vector3(0, 0.48, 0), _glow_material(GOLD, 4.5))
	apple_fruit.name = "AppleFruit"
	var stem := CylinderMesh.new()
	stem.top_radius = 0.035
	stem.bottom_radius = 0.055
	stem.height = 0.2
	_add_mesh(apple_root, stem, at + Vector3(0, 0.82, 0), _material(Color("#55d56a"), 0.35, 0.15))
	var leaf := SphereMesh.new()
	leaf.radius = 0.11
	leaf.height = 0.06
	_add_mesh(apple_root, leaf, at + Vector3(0.1, 0.87, 0), _material(Color("#71ff88"), 0.3, 0.1))
	var glow := OmniLight3D.new()
	glow.position = at + Vector3(0, 0.62, 0)
	glow.light_color = GOLD
	glow.light_energy = 2.4
	glow.omni_range = 3.6
	apple_root.add_child(glow)


func _spawn_eat_sparkles(at: Vector3) -> void:
	var particles := GPUParticles3D.new()
	particles.name = "AppleEatSparkles"
	particles.position = at
	particles.amount = 28
	particles.lifetime = 0.85
	particles.one_shot = true
	particles.explosiveness = 0.9
	particles.emitting = true
	particles.visibility_aabb = AABB(Vector3(-3, -2, -3), Vector3(6, 6, 6))
	var process_material := ParticleProcessMaterial.new()
	process_material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	process_material.emission_sphere_radius = 0.2
	process_material.direction = Vector3(0, 1, 0)
	process_material.spread = 180.0
	process_material.initial_velocity_min = 1.8
	process_material.initial_velocity_max = 4.2
	process_material.gravity = Vector3(0, -1.2, 0)
	process_material.scale_min = 0.035
	process_material.scale_max = 0.085
	process_material.color = GOLD.lightened(0.15)
	particles.process_material = process_material
	var sparkle := SphereMesh.new()
	sparkle.radius = 0.055
	sparkle.height = 0.11
	particles.draw_pass_1 = sparkle
	particles.material_override = _glow_material(GOLD, 3.5)
	add_child(particles)
	particles.finished.connect(particles.queue_free)


func _render_snake() -> void:
	for child in snake_root.get_children():
		child.queue_free()
	for i in range(snake.size()):
		var cell := snake[i]
		var at := _cell_to_world(cell)
		var is_head := i == 0
		if is_head:
			var head_mesh := CapsuleMesh.new()
			head_mesh.radius = 0.43
			head_mesh.height = 1.0
			var head := _add_mesh(snake_root, head_mesh, at + Vector3(0, 0.43, 0), _material(Color("#7bbf79"), 0.88, 0.22))
			var head_axis := Vector3(direction.x, 0, direction.y).normalized()
			if head_axis.length_squared() > 0.5:
				head.basis = Basis(Quaternion(Vector3.UP, head_axis))
			var forward := head_axis
			var side := Vector3(-direction.y, 0, direction.x).normalized()
			for sign in [-1.0, 1.0]:
				var eye_pos: Vector3 = at + Vector3(0, 0.72, 0) + forward * 0.28 + side * 0.2 * sign
				_sphere(snake_root, eye_pos, 0.125, _material(Color("#f3fff0"), 0.25, 0.18))
				_sphere(snake_root, eye_pos + forward * 0.075, 0.064, _glow_material(Color("#0c2420"), 0.35))
		else:
			var prev_cell: Vector2i = snake[maxi(0, i - 1)]
			var next_cell: Vector2i = snake[mini(snake.size() - 1, i + 1)]
			var tangent := Vector3(float(prev_cell.x - next_cell.x), 0, float(prev_cell.y - next_cell.y)).normalized()
			if tangent.length_squared() < 0.5:
				tangent = Vector3(direction.x, 0, direction.y).normalized()
			var cylinder := CylinderMesh.new()
			cylinder.top_radius = 0.37
			cylinder.bottom_radius = 0.37
			cylinder.height = 0.93
			cylinder.radial_segments = 16
			var body := _add_mesh(snake_root, cylinder, at + Vector3(0, 0.4, 0), _material(Color("#43575b"), 0.94, 0.24))
			body.basis = Basis(Quaternion(Vector3.UP, tangent))
			var ring := TorusMesh.new()
			ring.inner_radius = 0.32
			ring.outer_radius = 0.405
			var ring_node := _add_mesh(snake_root, ring, at + Vector3(0, 0.4, 0) + tangent * (TILE * 0.24), _glow_material(GREEN, 3.2))
			ring_node.basis = Basis(Quaternion(Vector3.BACK, tangent))
			var spine := _sphere(snake_root, at + Vector3(0, 0.765, 0), 0.115, _glow_material(Color("#c8ff6b"), 1.0))
			spine.scale = Vector3(1.25, 0.55, 1.0)

func _end_game() -> void:
	state = "game_over"
	paused = false
	_set_screen("game_over")


func _set_screen(screen: String) -> void:
	state = screen
	var showing := screen == "title" or screen == "game_over" or screen == "level_complete"
	overlay.visible = showing
	title_label.visible = showing
	subtitle_label.visible = showing
	pause_label.visible = false
	match screen:
		"title":
			title_label.text = "TRIPLE AAA SNAKE"
			subtitle_label.text = "CLICK OR PRESS ENTER TO START"
		"game_over":
			title_label.text = "GAME OVER"
			subtitle_label.text = "SCORE  %d     •     HIGH SCORE  %d\nCLICK OR PRESS ENTER TO RESTART" % [score, high_score]
		"level_complete":
			title_label.text = "LEVEL COMPLETE"
			subtitle_label.text = "LEVEL 2 INCOMING  •  FASTER.\nCLICK OR PRESS ENTER TO RESTART"


func _update_hud() -> void:
	var total_seconds := int(elapsed)
	var time_text := "%02d:%02d" % [total_seconds / 60, total_seconds % 60]
	time_level_label.text = "TIME   %s     •     LEVEL   %d" % [time_text, level]
	score_high_label.text = "SCORE   %06d       •       HIGH SCORE   %06d" % [score, high_score]
	var percent := int(round(float(apples) * 100.0 / float(APPLES_TO_LEVEL)))
	apples_label.text = "APPLES   %02d/%02d     •     %d%%" % [apples, APPLES_TO_LEVEL, percent]
	progress_fill.size.x = 288.0 * float(apples) / float(APPLES_TO_LEVEL)
	var remaining := maxf(0.0, 4.0 - (elapsed - last_apple_time))
	combo_label.visible = state == "playing" and combo >= 2 and remaining > 0.0
	combo_bar_fill.visible = combo_label.visible
	combo_label.text = "COMBO  x%d     •     %.1fs" % [combo, remaining]
	combo_bar_fill.size.x = 264.0 * remaining / 4.0

func _step_interval() -> float:
	return maxf(0.105, (0.31 - float(apples) * 0.008) / (1.0 if level == 1 else 1.22))


func _cell_to_world(cell: Vector2i) -> Vector3:
	return Vector3(float(cell.x) * TILE, 0, float(cell.y) * TILE)


func _box(size: Vector3) -> BoxMesh:
	var mesh := BoxMesh.new()
	mesh.size = size
	return mesh


func _add_mesh(parent: Node3D, mesh: Mesh, pos: Vector3, material: Material) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.mesh = mesh
	instance.position = pos
	instance.material_override = material
	instance.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_ON
	parent.add_child(instance)
	return instance


func _material(color: Color, metallic: float, roughness: float) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = roughness
	return material


func _glow_material(color: Color, energy: float) -> StandardMaterial3D:
	var material := _material(color, 0.5, 0.22)
	material.emission_enabled = true
	material.emission = color
	material.emission_energy_multiplier = energy
	return material


func _label(text_value: String, font_size: int, color: Color, pos: Vector2, size: Vector2, align: HorizontalAlignment) -> Label:
	var label := Label.new()
	label.text = text_value
	label.position = pos
	label.size = size
	label.horizontal_alignment = align
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", color)
	label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	label.add_theme_constant_override("shadow_offset_x", 1)
	label.add_theme_constant_override("shadow_offset_y", 2)
	return label


func _load_high_score() -> void:
	var config := ConfigFile.new()
	if config.load(HIGH_SCORE_PATH) == OK:
		high_score = int(config.get_value("snake", "high_score", 0))


func _save_high_score() -> void:
	var config := ConfigFile.new()
	config.set_value("snake", "high_score", high_score)
	config.save(HIGH_SCORE_PATH)
