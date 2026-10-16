extends Node3D

const FIELD_WIDTH := 18.0
const FIELD_HEIGHT := 10.0
const BALL_RADIUS := 0.22
const PADDLE_WIDTH := 2.3
const PADDLE_HEIGHT := 0.30
const PADDLE_SPEED := 11.0
const BRICK_COLUMNS := 9
const BRICK_ROWS := 5
const BRICK_WIDTH := 1.68
const BRICK_HEIGHT := 0.62
const BRICK_GAP := 0.16

var ball_position := Vector2(0.0, -2.65)
var ball_velocity := Vector2(4.2, 5.4)
var paddle_x := 0.0
var bricks: Array[Dictionary] = []
var score := 0
var lives := 3
var game_over := false

var ball_mesh: MeshInstance3D
var paddle_mesh: MeshInstance3D
var status_label: Label
var score_label: Label
var field_material: StandardMaterial3D

func _ready() -> void:
	_setup_viewport()
	_build_field()
	_build_paddle()
	_build_ball()
	_build_bricks()
	_build_hud()
	_update_hud()

func _setup_viewport() -> void:
	var viewport := get_viewport()
	viewport.size = Vector2i(1152, 648)
	viewport.use_xr = false
	if not DisplayServer.get_name() == "headless":
		DisplayServer.window_set_size(Vector2i(1152, 648))
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	var camera := Camera3D.new()
	camera.name = "Camera3D"
	camera.position = Vector3(0.0, 0.0, 19.0)
	camera.current = true
	camera.fov = 38.0
	add_child(camera)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-16.0, 0.0, 0.0)
	light.light_energy = 1.4
	add_child(light)
	var environment := WorldEnvironment.new()
	var world := Environment.new()
	world.background_mode = Environment.BG_COLOR
	world.background_color = Color(0.018, 0.028, 0.075)
	world.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	world.ambient_light_color = Color(0.55, 0.64, 0.95)
	world.ambient_light_energy = 0.8
	environment.environment = world
	add_child(environment)

func _build_field() -> void:
	var backdrop := MeshInstance3D.new()
	backdrop.name = "NeonPlayfield"
	var plane := PlaneMesh.new()
	plane.size = Vector2(FIELD_WIDTH + 0.8, FIELD_HEIGHT + 0.8)
	backdrop.mesh = plane
	backdrop.position.z = -0.55
	var material := StandardMaterial3D.new()
	material.albedo_color = Color(0.035, 0.055, 0.13)
	material.metallic = 0.25
	material.roughness = 0.34
	backdrop.material_override = material
	add_child(backdrop)
	for edge_x in [-FIELD_WIDTH * 0.5, FIELD_WIDTH * 0.5]:
		_add_box("SideRail", Vector3(0.16, FIELD_HEIGHT, 0.20), Vector3(edge_x, 0.0, 0.0), Color(0.12, 0.72, 1.0), 0.35)
	_add_box("TopRail", Vector3(FIELD_WIDTH, 0.16, 0.20), Vector3(0.0, FIELD_HEIGHT * 0.5, 0.0), Color(0.12, 0.72, 1.0), 0.35)
	_add_box("BottomRail", Vector3(FIELD_WIDTH, 0.12, 0.16), Vector3(0.0, -FIELD_HEIGHT * 0.5, 0.0), Color(0.12, 0.72, 1.0), 0.2)

func _build_paddle() -> void:
	paddle_mesh = _add_box("Paddle", Vector3(PADDLE_WIDTH, PADDLE_HEIGHT, 0.28), Vector3(paddle_x, -4.05, 0.15), Color(0.16, 0.9, 1.0), 0.65)

func _build_ball() -> void:
	ball_mesh = MeshInstance3D.new()
	ball_mesh.name = "Ball"
	var sphere := SphereMesh.new()
	sphere.radius = BALL_RADIUS
	sphere.height = BALL_RADIUS * 2.0
	ball_mesh.mesh = sphere
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 0.96, 0.78)
	mat.emission_enabled = true
	mat.emission = Color(0.95, 0.78, 0.38)
	mat.emission_energy_multiplier = 1.1
	ball_mesh.material_override = mat
	ball_mesh.position = Vector3(ball_position.x, ball_position.y, 0.38)
	add_child(ball_mesh)

func _build_bricks() -> void:
	var palette: Array[Color] = [Color(1.0, 0.27, 0.42), Color(1.0, 0.54, 0.23), Color(1.0, 0.83, 0.30), Color(0.28, 0.91, 0.72), Color(0.36, 0.58, 1.0)]
	var total_width := BRICK_COLUMNS * BRICK_WIDTH + (BRICK_COLUMNS - 1) * BRICK_GAP
	for row in range(BRICK_ROWS):
		for column in range(BRICK_COLUMNS):
			var x := -total_width * 0.5 + BRICK_WIDTH * 0.5 + column * (BRICK_WIDTH + BRICK_GAP)
			var y := 3.25 - row * (BRICK_HEIGHT + 0.14)
			var node := _add_box("Brick_%02d_%02d" % [row, column], Vector3(BRICK_WIDTH, BRICK_HEIGHT, 0.25), Vector3(x, y, 0.16), palette[row], 0.28)
			bricks.append({"node": node, "center": Vector2(x, y), "half": Vector2(BRICK_WIDTH * 0.5, BRICK_HEIGHT * 0.5)})

func _build_hud() -> void:
	var canvas := CanvasLayer.new()
	canvas.name = "HUD"
	add_child(canvas)
	var panel := ColorRect.new()
	panel.position = Vector2(0, 0)
	panel.size = Vector2(1152, 54)
	panel.color = Color(0.015, 0.025, 0.07, 0.88)
	canvas.add_child(panel)
	var title := Label.new()
	title.text = "NEON BREAKOUT     ◂  ARROW KEYS  ▸"
	title.position = Vector2(28, 14)
	title.add_theme_color_override("font_color", Color(0.40, 0.88, 1.0))
	title.add_theme_font_size_override("font_size", 21)
	canvas.add_child(title)
	score_label = Label.new()
	score_label.position = Vector2(850, 14)
	score_label.size = Vector2(270, 32)
	score_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	score_label.add_theme_color_override("font_color", Color(1.0, 0.86, 0.43))
	score_label.add_theme_font_size_override("font_size", 21)
	canvas.add_child(score_label)
	status_label = Label.new()
	status_label.position = Vector2(0, 574)
	status_label.size = Vector2(1152, 36)
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.add_theme_color_override("font_color", Color(0.64, 0.78, 1.0))
	status_label.add_theme_font_size_override("font_size", 18)
	canvas.add_child(status_label)

func _process(delta: float) -> void:
	if game_over:
		return
	var direction := 0.0
	if Input.is_key_pressed(KEY_LEFT):
		direction -= 1.0
	if Input.is_key_pressed(KEY_RIGHT):
		direction += 1.0
	paddle_x = clampf(paddle_x + direction * PADDLE_SPEED * delta, -FIELD_WIDTH * 0.5 + PADDLE_WIDTH * 0.5 + 0.18, FIELD_WIDTH * 0.5 - PADDLE_WIDTH * 0.5 - 0.18)
	paddle_mesh.position.x = paddle_x
	_step_ball(delta)
	ball_mesh.position = Vector3(ball_position.x, ball_position.y, 0.38)

func _step_ball(delta: float) -> void:
	var previous := ball_position
	ball_position += ball_velocity * delta
	var left := -FIELD_WIDTH * 0.5 + BALL_RADIUS
	var right := FIELD_WIDTH * 0.5 - BALL_RADIUS
	var top := FIELD_HEIGHT * 0.5 - BALL_RADIUS
	if ball_position.x < left:
		ball_position.x = left
		ball_velocity.x = absf(ball_velocity.x)
	elif ball_position.x > right:
		ball_position.x = right
		ball_velocity.x = -absf(ball_velocity.x)
	if ball_position.y > top:
		ball_position.y = top
		ball_velocity.y = -absf(ball_velocity.y)
	var paddle_y := -4.05
	if ball_velocity.y < 0.0 and ball_position.y - BALL_RADIUS <= paddle_y + PADDLE_HEIGHT * 0.5 and previous.y - BALL_RADIUS >= paddle_y - PADDLE_HEIGHT * 0.5 and absf(ball_position.x - paddle_x) <= PADDLE_WIDTH * 0.5 + BALL_RADIUS:
		ball_position.y = paddle_y + PADDLE_HEIGHT * 0.5 + BALL_RADIUS
		var hit_offset := clampf((ball_position.x - paddle_x) / (PADDLE_WIDTH * 0.5), -1.0, 1.0)
		ball_velocity = Vector2(hit_offset * 6.5, absf(ball_velocity.y) + 0.15).normalized() * maxf(ball_velocity.length(), 6.9)
	for index in range(bricks.size() - 1, -1, -1):
		var brick: Dictionary = bricks[index]
		var center: Vector2 = brick["center"]
		var half: Vector2 = brick["half"]
		if absf(ball_position.x - center.x) <= half.x + BALL_RADIUS and absf(ball_position.y - center.y) <= half.y + BALL_RADIUS:
			var overlap_x := half.x + BALL_RADIUS - absf(ball_position.x - center.x)
			var overlap_y := half.y + BALL_RADIUS - absf(ball_position.y - center.y)
			if overlap_x < overlap_y:
				ball_velocity.x = -ball_velocity.x
		else:
			continue
			ball_velocity.y = -ball_velocity.y
		ball_position = previous
		(brick["node"] as Node3D).queue_free()
		bricks.remove_at(index)
		score += 10
		_update_hud()
		break
	if ball_position.y < -FIELD_HEIGHT * 0.5 - 0.2:
		lives -= 1
		if lives <= 0:
			game_over = true
			status_label.text = "GAME OVER  •  SCORE %d  •  CLOSE TO RESTART" % score
		else:
			ball_position = Vector2(paddle_x, -2.65)
			ball_velocity = Vector2(4.2 * (1.0 if lives % 2 == 1 else -1.0), 5.4)
		_update_hud()
	if bricks.is_empty():
		game_over = true
		status_label.text = "ALL CLEAR  •  SCORE %d" % score

func _update_hud() -> void:
	if score_label != null:
		score_label.text = "SCORE  %04d     LIVES  %d" % [score, lives]
	if status_label != null and not game_over:
		status_label.text = "Move with ← → to keep the ball in play  •  %d bricks remaining" % bricks.size()

func _add_box(node_name: String, dimensions: Vector3, location: Vector3, tint: Color, glow: float) -> MeshInstance3D:
	var item := MeshInstance3D.new()
	item.name = node_name
	var box := BoxMesh.new()
	box.size = dimensions
	item.mesh = box
	var material := StandardMaterial3D.new()
	material.albedo_color = tint
	material.metallic = 0.18
	material.roughness = 0.32
	if glow > 0.0:
		material.emission_enabled = true
		material.emission = tint
		material.emission_energy_multiplier = glow
	item.material_override = material
	item.position = location
	add_child(item)
	return item
