extends Node3D

const EDGE := 10.0
const RADIUS := 0.22
const PADDLE_Z := 4.65
const PADDLE_HALF := 1.45
const COLORS := [Color("ff637d"), Color("ffac61"), Color("ffe089"), Color("53ddbb"), Color("57b7ff")]
var paddle: MeshInstance3D
var ball: MeshInstance3D
var bricks: Array[MeshInstance3D] = []
var streaks: Array[MeshInstance3D] = []
var direction := Vector2(0.42, -0.91).normalized()
var speed := 8.0
var score := 0
var lives := 3
var launch_delay := 0.8
var ended := false
var score_text: Label
var status_text: Label
var lives_text: Label
var trail_clock := 0.0

func _ready() -> void:
	get_window().content_scale_size = Vector2i(1152, 648)
	get_window().content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	if DisplayServer.get_name() != "headless":
		DisplayServer.window_set_size(Vector2i(1152, 648))
		DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	RenderingServer.set_default_clear_color(Color("080f20"))
	var environment := WorldEnvironment.new()
	var sky := Environment.new()
	sky.background_mode = Environment.BG_COLOR
	sky.background_color = Color("080f20")
	sky.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	sky.ambient_light_color = Color("b7d5ff")
	sky.ambient_light_energy = 0.65
	environment.environment = sky
	add_child(environment)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-55, -25, 0)
	light.light_energy = 1.5
	add_child(light)
	var camera := Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 15.6
	camera.position = Vector3(0, 23, 9)
	add_child(camera)
	camera.look_at(Vector3.ZERO)
	camera.current = true
	box(Vector3(20.8, 0.35, 12.8), Vector3(0, -0.48, 0), Color("12243b"))
	box(Vector3(20, 0.06, 12), Vector3(0, -0.26, 0), Color("0c192c"))
	for x in range(-9, 10):
		box(Vector3(0.015, 0.012, 11.7), Vector3(x, -0.218, 0), Color("192c42"), true)
	for z in range(-5, 6):
		box(Vector3(19.7, 0.012, 0.015), Vector3(0, -0.218, z), Color("192c42"), true)
	for x in [-10.25, 10.25]:
		box(Vector3(0.25, 0.5, 12.5), Vector3(x, 0, 0), Color("3a7690"))
		box(Vector3(0.06, 0.025, 12.5), Vector3(x, 0.26, 0), Color("62e5e8"), true)
	box(Vector3(20.5, 0.5, 0.25), Vector3(0, 0, -6.2), Color("3a7690"))
	box(Vector3(20, 0.02, 0.045), Vector3(0, -0.2, 5.85), Color("f86488"), true)
	paddle = box(Vector3(PADDLE_HALF * 2, 0.42, 0.55), Vector3(0, 0.15, PADDLE_Z), Color("8ceef2"))
	var stripe := box(Vector3(0.6, 0.015, 0.4), Vector3(0, 0.22, 0), Color.WHITE, true)
	remove_child(stripe)
	paddle.add_child(stripe)
	ball = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = RADIUS
	sphere.height = RADIUS * 2
	ball.mesh = sphere
	ball.material_override = material(Color("ffffff"), true)
	add_child(ball)
	for i in range(12):
		var dot := MeshInstance3D.new()
		dot.mesh = sphere
		dot.material_override = material(Color("48a6c9").lerp(Color("142c44"), float(i) / 12.0), true)
		dot.scale = Vector3.ONE * (1.0 - float(i + 1) / 14.0) * 0.65
		dot.visible = false
		add_child(dot)
		streaks.append(dot)
	build_bricks()
	build_ui()
	serve()

func material(color: Color, luminous: bool = false) -> StandardMaterial3D:
	var result := StandardMaterial3D.new()
	result.albedo_color = color
	result.roughness = 0.38
	result.metallic = 0.15
	if luminous:
		result.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	return result

func box(size: Vector3, at: Vector3, color: Color, luminous: bool = false) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	var shape := BoxMesh.new()
	shape.size = size
	node.mesh = shape
	node.material_override = material(color, luminous)
	node.position = at
	add_child(node)
	return node

func build_bricks() -> void:
	for row in range(5):
		for column in range(9):
			var brick := box(Vector3(1.88, 0.55, 0.64), Vector3((column - 4) * 2.13, 0.18, -4.8 + row * 0.88), COLORS[row])
			bricks.append(brick)

func label_at(parent: Node, words: String, at: Vector2, font_size: int, tint: Color) -> Label:
	var label := Label.new()
	label.text = words
	label.position = at
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", tint)
	parent.add_child(label)
	return label

func build_ui() -> void:
	var canvas := CanvasLayer.new()
	add_child(canvas)
	var layout := Control.new()
	layout.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	layout.mouse_filter = Control.MOUSE_FILTER_IGNORE
	canvas.add_child(layout)
	label_at(layout, "PRISM / BREAKOUT", Vector2(40, 21), 29, Color("d6faff"))
	label_at(layout, "3D ARCADE     /     01", Vector2(42, 57), 12, Color("7599b7"))
	score_text = label_at(layout, "", Vector2(770, 25), 23, Color("ffe089"))
	lives_text = label_at(layout, "", Vector2(966, 25), 23, Color("8ceef2"))
	status_text = label_at(layout, "", Vector2(300, 568), 21, Color("d6faff"))
	status_text.size.x = 552
	status_text.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label_at(layout, "←  →   MOVE PADDLE", Vector2(42, 613), 15, Color("91b4cb"))
	label_at(layout, "SPACE   RESTART     /     ESC   QUIT", Vector2(787, 613), 14, Color("91b4cb"))
	refresh_ui()

func refresh_ui() -> void:
	score_text.text = "SCORE  %04d" % score
	lives_text.text = "LIVES  %d" % lives

func serve() -> void:
	ball.position = Vector3(paddle.position.x, 0.23, PADDLE_Z - 0.7)
	direction = Vector2(0.42 if lives % 2 == 1 else -0.42, -0.91).normalized()
	launch_delay = 0.9
	for dot in streaks:
		dot.visible = false

func _unhandled_key_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		if event.keycode == KEY_ESCAPE:
			get_tree().quit()
		elif event.keycode == KEY_SPACE:
			for brick in bricks:
				brick.queue_free()
			bricks.clear()
			build_bricks()
			score = 0
			lives = 3
			speed = 8.0
			ended = false
			serve()
			refresh_ui()

func _physics_process(delta: float) -> void:
	if ended:
		return
	var axis := float(Input.is_physical_key_pressed(KEY_RIGHT)) - float(Input.is_physical_key_pressed(KEY_LEFT))
	paddle.position.x = clampf(paddle.position.x + axis * delta * 13.0, -EDGE + PADDLE_HALF, EDGE - PADDLE_HALF)
	if launch_delay > 0:
		launch_delay -= delta
		ball.position.x = paddle.position.x
		status_text.text = "READY / KEEP THE BALL IN PLAY"
		return
	status_text.text = "BREAK THE WALL  /  %02d REMAINING" % bricks.size()
	# Small fixed-distance steps prevent tunneling through thin bricks.
	var steps := maxi(1, ceili(speed * delta / 0.12))
	for step in range(steps):
		advance_ball(delta / steps)
		if ended or launch_delay > 0:
			break
	trail_clock += delta
	if trail_clock > 0.018:
		trail_clock = 0
		for i in range(streaks.size() - 1, 0, -1):
			streaks[i].position = streaks[i - 1].position
			streaks[i].visible = streaks[i - 1].visible
		streaks[0].position = ball.position
		streaks[0].visible = true

func advance_ball(dt: float) -> void:
	ball.position += Vector3(direction.x, 0, direction.y) * speed * dt
	if absf(ball.position.x) > EDGE - RADIUS:
		ball.position.x = clampf(ball.position.x, -EDGE + RADIUS, EDGE - RADIUS)
		direction.x *= -1
	if ball.position.z < -6.0 + RADIUS:
		ball.position.z = -6.0 + RADIUS
		direction.y = absf(direction.y)
	if direction.y > 0 and absf(ball.position.z - PADDLE_Z) < 0.275 + RADIUS and absf(ball.position.x - paddle.position.x) < PADDLE_HALF + RADIUS:
		var offset := clampf((ball.position.x - paddle.position.x) / PADDLE_HALF, -1, 1)
		direction = Vector2(offset * 0.84, -1).normalized()
		ball.position.z = PADDLE_Z - 0.275 - RADIUS
	for i in range(bricks.size()):
		var brick := bricks[i]
		var offset := Vector2(ball.position.x - brick.position.x, ball.position.z - brick.position.z)
		var penetration := Vector2(0.94 + RADIUS - absf(offset.x), 0.32 + RADIUS - absf(offset.y))
		if penetration.x > 0 and penetration.y > 0:
			if penetration.x < penetration.y:
				direction.x *= -1
				ball.position.x += signf(offset.x) * penetration.x
			else:
				direction.y *= -1
				ball.position.z += signf(offset.y) * penetration.y
			shatter(brick)
			bricks.remove_at(i)
			brick.queue_free()
			score += 10
			speed = minf(12.5, speed + 0.075)
			refresh_ui()
			if bricks.is_empty():
				ended = true
				status_text.text = "WALL CLEARED!   /   SPACE TO PLAY AGAIN"
			break
	if ball.position.z > 6.5:
		lives -= 1
		refresh_ui()
		if lives <= 0:
			ended = true
			status_text.text = "OUT OF BALLS   /   SPACE TO TRY AGAIN"
		else:
			serve()

func shatter(brick: MeshInstance3D) -> void:
	var tint: Color = (brick.material_override as StandardMaterial3D).albedo_color
	for i in range(5):
		var chip := box(Vector3(0.22, 0.2, 0.22), brick.position, tint, true)
		var target := chip.position + Vector3(randf_range(-1, 1), randf_range(0.4, 1.3), randf_range(-0.7, 0.7))
		var tween := create_tween().set_parallel(true)
		tween.tween_property(chip, "position", target, 0.42).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(chip, "scale", Vector3.ZERO, 0.42)
		tween.chain().tween_callback(chip.queue_free)
