extends Node3D
## 3D Breakout demo. Left/Right arrows move the paddle, Space launches/restarts.

const FIELD_W := 14.0
const FIELD_TOP := 9.0
const FIELD_BOTTOM := -9.0
const PADDLE_Y := -7.5
const PADDLE_W := 2.6
const PADDLE_H := 0.4
const PADDLE_SPEED := 14.0
const BALL_R := 0.25
const BALL_SPEED := 9.0
const BRICK_COLS := 10
const BRICK_ROWS := 6
const BRICK_W := 1.2
const BRICK_H := 0.5
const BRICK_GAP := 0.12

var paddle: MeshInstance3D
var ball: MeshInstance3D
var ball_vel := Vector3.ZERO
var ball_live := false
var bricks: Array[MeshInstance3D] = []
var score := 0
var lives := 3
var hud: Label

func _ready() -> void:
	DisplayServer.window_set_size(Vector2i(1152, 648))
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_FULLSCREEN)
	_build_world()
	_build_bricks()
	_reset_ball()
	_update_hud()

func _mat(c: Color, emit := 0.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	if emit > 0.0:
		m.emission_enabled = true
		m.emission = c
		m.emission_energy_multiplier = emit
	return m

func _box(size: Vector3, pos: Vector3, c: Color, emit := 0.0) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var bm := BoxMesh.new()
	bm.size = size
	bm.material = _mat(c, emit)
	mi.mesh = bm
	mi.position = pos
	add_child(mi)
	return mi

func _build_world() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.03, 0.03, 0.08)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.4, 0.4, 0.5)
	env.environment = e
	add_child(env)

	var cam := Camera3D.new()
	cam.position = Vector3(0, -6.0, 20.0)
	cam.fov = 55.0
	add_child(cam)
	cam.look_at(Vector3(0, -0.5, 0))

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-40, 25, 0)
	add_child(sun)

	# Back plate and walls
	_box(Vector3(FIELD_W + 1.0, FIELD_TOP - FIELD_BOTTOM + 1.0, 0.2), Vector3(0, 0, -0.6), Color(0.08, 0.09, 0.15))
	var wall_c := Color(0.5, 0.55, 0.7)
	_box(Vector3(0.5, FIELD_TOP - FIELD_BOTTOM, 1.0), Vector3(-FIELD_W / 2 - 0.25, 0, 0), wall_c)
	_box(Vector3(0.5, FIELD_TOP - FIELD_BOTTOM, 1.0), Vector3(FIELD_W / 2 + 0.25, 0, 0), wall_c)
	_box(Vector3(FIELD_W + 1.0, 0.5, 1.0), Vector3(0, FIELD_TOP + 0.25, 0), wall_c)

	paddle = _box(Vector3(PADDLE_W, PADDLE_H, 0.8), Vector3(0, PADDLE_Y, 0), Color(0.2, 0.8, 1.0), 0.4)

	ball = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = BALL_R
	sm.height = BALL_R * 2.0
	sm.material = _mat(Color(1, 1, 0.9), 1.0)
	ball.mesh = sm
	add_child(ball)

	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Label.new()
	hud.position = Vector2(16, 10)
	hud.add_theme_font_size_override("font_size", 22)
	layer.add_child(hud)

func _build_bricks() -> void:
	for b in bricks:
		b.queue_free()
	bricks.clear()
	var total_w := BRICK_COLS * BRICK_W + (BRICK_COLS - 1) * BRICK_GAP
	for r in BRICK_ROWS:
		var c := Color.from_hsv(float(r) / BRICK_ROWS, 0.75, 1.0)
		for col in BRICK_COLS:
			var x := -total_w / 2.0 + BRICK_W / 2.0 + col * (BRICK_W + BRICK_GAP)
			var y := FIELD_TOP - 1.5 - r * (BRICK_H + BRICK_GAP)
			bricks.append(_box(Vector3(BRICK_W, BRICK_H, 0.8), Vector3(x, y, 0), c, 0.25))

func _reset_ball() -> void:
	ball_live = false
	ball_vel = Vector3.ZERO

func _launch() -> void:
	ball_live = true
	var dir := Vector3(randf_range(-0.5, 0.5), 1.0, 0).normalized()
	ball_vel = dir * BALL_SPEED

func _update_hud() -> void:
	var msg := "Score: %d   Lives: %d" % [score, lives]
	if lives <= 0:
		msg += "   GAME OVER - Space to restart"
	elif bricks.is_empty():
		msg += "   YOU WIN - Space to restart"
	elif not ball_live:
		msg += "   Space to launch"
	hud.text = msg

func _process(delta: float) -> void:
	var dir := 0.0
	if Input.is_key_pressed(KEY_LEFT):
		dir -= 1.0
	if Input.is_key_pressed(KEY_RIGHT):
		dir += 1.0
	var lim := FIELD_W / 2.0 - PADDLE_W / 2.0
	paddle.position.x = clampf(paddle.position.x + dir * PADDLE_SPEED * delta, -lim, lim)

	if Input.is_key_pressed(KEY_SPACE) and not ball_live:
		if lives <= 0 or bricks.is_empty():
			score = 0
			lives = 3
			_build_bricks()
		_launch()

	if not ball_live:
		ball.position = paddle.position + Vector3(0, PADDLE_H / 2.0 + BALL_R + 0.02, 0)
	else:
		_step_ball(delta)
	_update_hud()

func _step_ball(delta: float) -> void:
	var p := ball.position + ball_vel * delta
	var half := FIELD_W / 2.0 - BALL_R
	if p.x < -half:
		p.x = -half
		ball_vel.x = absf(ball_vel.x)
	elif p.x > half:
		p.x = half
		ball_vel.x = -absf(ball_vel.x)
	if p.y > FIELD_TOP - BALL_R:
		p.y = FIELD_TOP - BALL_R
		ball_vel.y = -absf(ball_vel.y)

	# Paddle
	if ball_vel.y < 0.0 and absf(p.x - paddle.position.x) < PADDLE_W / 2.0 + BALL_R \
			and absf(p.y - PADDLE_Y) < PADDLE_H / 2.0 + BALL_R:
		var off := (p.x - paddle.position.x) / (PADDLE_W / 2.0)
		ball_vel = Vector3(off * 0.8, 1.0, 0).normalized() * BALL_SPEED
		p.y = PADDLE_Y + PADDLE_H / 2.0 + BALL_R

	# Bricks: one hit per frame, reflect on the shallower overlap axis
	for i in bricks.size():
		var b := bricks[i]
		var dx := p.x - b.position.x
		var dy := p.y - b.position.y
		var ox := BRICK_W / 2.0 + BALL_R - absf(dx)
		var oy := BRICK_H / 2.0 + BALL_R - absf(dy)
		if ox > 0.0 and oy > 0.0:
			if ox < oy:
				ball_vel.x = absf(ball_vel.x) * signf(dx)
			else:
				ball_vel.y = absf(ball_vel.y) * signf(dy)
			b.queue_free()
			bricks.remove_at(i)
			score += 10
			if bricks.is_empty():
				_reset_ball()
			break

	ball.position = p
	if p.y < FIELD_BOTTOM:
		lives -= 1
		_reset_ball()
