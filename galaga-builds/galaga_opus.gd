extends Node3D
## Self-contained 3D Galaga demo. Arrows move, Space fires, R restarts after game over.

const FIELD_X := 9.0
const FIELD_TOP := 11.0
const FIELD_BOTTOM := -1.0
const PLAYER_SPEED := 10.0
const BULLET_SPEED := 22.0
const ENEMY_BULLET_SPEED := 8.0
const FIRE_COOLDOWN := 0.22

var player: Node3D
var player_vel := 0.0
var fire_timer := 0.0
var bullets: Array = []
var enemy_bullets: Array = []
var enemies: Array = []
var particles: Array = []
var stars: Array = []
var score := 0
var lives := 3
var wave := 0
var formation_t := 0.0
var invuln := 0.0
var game_over := false
var shake := 0.0
var camera: Camera3D
var hud: Label
var banner: Label
var rng := RandomNumberGenerator.new()
var mat_cache := {}

func _ready() -> void:
	rng.randomize()
	var win := get_window()
	if win and DisplayServer.get_name() != "headless":
		win.size = Vector2i(1152, 648)
		win.mode = Window.MODE_FULLSCREEN
	_build_world()
	_spawn_player()
	_spawn_wave()

func _mat(color: Color, emit := 1.5) -> StandardMaterial3D:
	var key := "%s_%s" % [color.to_html(), emit]
	if mat_cache.has(key):
		return mat_cache[key]
	var m := StandardMaterial3D.new()
	m.albedo_color = color
	m.emission_enabled = true
	m.emission = color
	m.emission_energy_multiplier = emit
	mat_cache[key] = m
	return m

func _box(size: Vector3, color: Color, emit := 1.5) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var b := BoxMesh.new()
	b.size = size
	mi.mesh = b
	mi.material_override = _mat(color, emit)
	return mi

func _build_world() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.01, 0.01, 0.04)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.4, 0.4, 0.5)
	e.glow_enabled = true
	e.glow_intensity = 1.0
	e.glow_bloom = 0.2
	env.environment = e
	add_child(env)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-50, 30, 0)
	add_child(light)
	camera = Camera3D.new()
	camera.position = Vector3(0, 4.0, 16.0)
	camera.look_at_from_position(camera.position, Vector3(0, 5.0, 0))
	camera.fov = 60
	add_child(camera)
	camera.make_current()
	for i in 120:
		var s := _box(Vector3.ONE * rng.randf_range(0.03, 0.08), Color(0.8, 0.85, 1.0), 2.0)
		s.position = Vector3(rng.randf_range(-20, 20), rng.randf_range(-6, 18), rng.randf_range(-15, -3))
		add_child(s)
		stars.append({"node": s, "speed": rng.randf_range(1.0, 4.0)})
	var layer := CanvasLayer.new()
	add_child(layer)
	hud = Label.new()
	hud.position = Vector2(16, 10)
	hud.add_theme_font_size_override("font_size", 22)
	layer.add_child(hud)
	banner = Label.new()
	banner.set_anchors_preset(Control.PRESET_FULL_RECT)
	banner.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	banner.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	banner.add_theme_font_size_override("font_size", 40)
	layer.add_child(banner)

func _spawn_player() -> void:
	player = Node3D.new()
	var body := _box(Vector3(0.5, 1.0, 0.4), Color(0.9, 0.9, 1.0), 0.6)
	player.add_child(body)
	var wings := _box(Vector3(1.6, 0.3, 0.3), Color(0.2, 0.5, 1.0), 1.2)
	wings.position.y = -0.2
	player.add_child(wings)
	var nose := _box(Vector3(0.2, 0.4, 0.2), Color(1, 0.2, 0.2), 2.0)
	nose.position.y = 0.65
	player.add_child(nose)
	var flame := _box(Vector3(0.25, 0.3, 0.2), Color(1.0, 0.6, 0.1), 4.0)
	flame.name = "Flame"
	flame.position.y = -0.65
	player.add_child(flame)
	player.position = Vector3(0, 0, 0)
	add_child(player)

func _spawn_wave() -> void:
	wave += 1
	var colors := [Color(1, 0.2, 0.3), Color(0.3, 1, 0.4), Color(1, 0.8, 0.2)]
	for row in 3:
		for col in 6:
			var e := Node3D.new()
			var c: Color = colors[row]
			e.add_child(_box(Vector3(0.8, 0.5, 0.4), c, 1.8))
			var wl := _box(Vector3(0.25, 0.6, 0.25), c.lightened(0.4), 1.0)
			wl.position.x = -0.5
			e.add_child(wl)
			var wr := wl.duplicate()
			wr.position.x = 0.5
			e.add_child(wr)
			var home := Vector3((col - 2.5) * 1.8, 8.5 - row * 1.3, 0)
			e.position = home + Vector3(0, 8, 0)
			add_child(e)
			enemies.append({"node": e, "home": home, "state": "enter", "t": 0.0,
				"hp": 2 if row == 0 else 1, "phase": rng.randf() * TAU, "dive_dir": 1.0})

func _process(delta: float) -> void:
	delta = min(delta, 0.05)
	_update_stars(delta)
	_update_particles(delta)
	_update_camera(delta)
	if game_over:
		if Input.is_physical_key_pressed(KEY_R) or Input.is_key_pressed(KEY_R):
			_restart()
		_update_hud()
		return
	_update_player(delta)
	_update_bullets(delta)
	_update_enemies(delta)
	_check_collisions()
	if enemies.is_empty():
		_spawn_wave()
	_update_hud()

func _update_stars(delta: float) -> void:
	for s in stars:
		var n: Node3D = s.node
		n.position.y -= s.speed * delta
		if n.position.y < -6:
			n.position.y = 18

func _update_camera(delta: float) -> void:
	shake = max(shake - delta * 3.0, 0.0)
	var off := Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), 0) * shake * 0.3
	camera.position = Vector3(0, 4.0, 16.0) + off

func _update_player(delta: float) -> void:
	var dir := 0.0
	if Input.is_key_pressed(KEY_LEFT): dir -= 1.0
	if Input.is_key_pressed(KEY_RIGHT): dir += 1.0
	var vdir := 0.0
	if Input.is_key_pressed(KEY_UP): vdir += 1.0
	if Input.is_key_pressed(KEY_DOWN): vdir -= 1.0
	player_vel = lerp(player_vel, dir * PLAYER_SPEED, 10.0 * delta)
	player.position.x = clamp(player.position.x + player_vel * delta, -FIELD_X, FIELD_X)
	player.position.y = clamp(player.position.y + vdir * PLAYER_SPEED * 0.5 * delta, 0.0, 2.5)
	player.rotation.y = -player_vel / PLAYER_SPEED * 0.6
	var flame: Node3D = player.get_node("Flame")
	flame.scale.y = 0.7 + rng.randf() * 0.8
	fire_timer -= delta
	if Input.is_key_pressed(KEY_SPACE) and fire_timer <= 0.0:
		fire_timer = FIRE_COOLDOWN
		_fire_player()
	if invuln > 0.0:
		invuln -= delta
		player.visible = int(invuln * 15.0) % 2 == 0
	else:
		player.visible = true

func _fire_player() -> void:
	for xo in [-0.3, 0.3]:
		var b := _box(Vector3(0.12, 0.6, 0.12), Color(0.4, 1.0, 1.0), 5.0)
		b.position = player.position + Vector3(xo, 0.7, 0)
		add_child(b)
		bullets.append(b)
	_burst(player.position + Vector3(0, 0.8, 0), Color(0.5, 1, 1), 4, 3.0, 0.15)

func _update_bullets(delta: float) -> void:
	for b in bullets.duplicate():
		b.position.y += BULLET_SPEED * delta
		if b.position.y > FIELD_TOP + 3:
			_remove(bullets, b)
	for b in enemy_bullets.duplicate():
		b.position += b.get_meta("vel") * delta
		if b.position.y < FIELD_BOTTOM - 4:
			_remove(enemy_bullets, b)

func _update_enemies(delta: float) -> void:
	formation_t += delta
	var sway := sin(formation_t * 0.8) * 1.5
	var divers := 0
	for e in enemies:
		if e.state == "dive": divers += 1
	for e in enemies:
		var n: Node3D = e.node
		var target: Vector3 = e.home + Vector3(sway, sin(formation_t * 2.0 + e.phase) * 0.15, 0)
		match e.state:
			"enter":
				n.position = n.position.lerp(target, 3.0 * delta)
				if n.position.distance_to(target) < 0.1:
					e.state = "form"
			"form":
				n.position = target
				n.rotation.y = sin(formation_t * 3.0 + e.phase) * 0.3
				if divers < 2 + wave and rng.randf() < 0.004:
					e.state = "dive"
					e.t = 0.0
					e.dive_dir = 1.0 if n.position.x < player.position.x else -1.0
					divers += 1
				if rng.randf() < 0.0015 * wave:
					_fire_enemy(n.position)
			"dive":
				e.t += delta
				n.position.y -= (5.0 + wave) * delta
				n.position.x += sin(e.t * 3.0) * e.dive_dir * 6.0 * delta
				n.position.x = move_toward(n.position.x, player.position.x, 1.5 * delta)
				n.rotation.z = sin(e.t * 3.0) * 0.8
				if rng.randf() < 0.02:
					_fire_enemy(n.position)
				if n.position.y < FIELD_BOTTOM - 3:
					n.position = Vector3(target.x, FIELD_TOP + 3, 0)
					n.rotation = Vector3.ZERO
					e.state = "enter"

func _fire_enemy(pos: Vector3) -> void:
	var b := _box(Vector3(0.2, 0.2, 0.2), Color(1.0, 0.3, 0.8), 4.0)
	b.position = pos + Vector3(0, -0.4, 0)
	var aim := (player.position - b.position).normalized()
	aim = (aim + Vector3(0, -1, 0)).normalized()
	b.set_meta("vel", aim * ENEMY_BULLET_SPEED)
	add_child(b)
	enemy_bullets.append(b)

func _check_collisions() -> void:
	for b in bullets.duplicate():
		for e in enemies.duplicate():
			var n: Node3D = e.node
			if abs(b.position.x - n.position.x) < 0.6 and abs(b.position.y - n.position.y) < 0.5:
				_remove(bullets, b)
				e.hp -= 1
				_burst(b.position, Color(1, 1, 0.6), 6, 4.0, 0.3)
				if e.hp <= 0:
					score += 200 if e.state == "dive" else 100
					_burst(n.position, (n.get_child(0) as MeshInstance3D).material_override.albedo_color, 24, 7.0, 0.7)
					shake = max(shake, 0.6)
					enemies.erase(e)
					n.queue_free()
				break
	if invuln > 0.0:
		return
	for b in enemy_bullets.duplicate():
		if b.position.distance_to(player.position) < 0.6:
			_remove(enemy_bullets, b)
			_player_hit()
			return
	for e in enemies:
		if e.node.position.distance_to(player.position) < 0.9:
			_player_hit()
			return

func _player_hit() -> void:
	lives -= 1
	_burst(player.position, Color(1, 0.6, 0.2), 40, 9.0, 1.0)
	shake = 1.2
	invuln = 2.0
	if lives <= 0:
		game_over = true
		player.visible = false

func _remove(arr: Array, n: Node) -> void:
	arr.erase(n)
	n.queue_free()

func _burst(pos: Vector3, color: Color, count: int, speed: float, life: float) -> void:
	for i in count:
		var p := _box(Vector3.ONE * rng.randf_range(0.08, 0.18), color, 4.0)
		p.position = pos
		add_child(p)
		var v := Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1)).normalized() * speed * rng.randf_range(0.3, 1.0)
		particles.append({"node": p, "vel": v, "life": life, "max": life})

func _update_particles(delta: float) -> void:
	for p in particles.duplicate():
		p.life -= delta
		var n: Node3D = p.node
		if p.life <= 0.0:
			particles.erase(p)
			n.queue_free()
			continue
		n.position += p.vel * delta
		p.vel *= 0.94
		n.scale = Vector3.ONE * (p.life / p.max)
		n.rotation += Vector3(5, 7, 3) * delta

func _update_hud() -> void:
	hud.text = "SCORE %d    LIVES %d    WAVE %d\nArrows: move   Space: fire" % [score, lives, wave]
	banner.text = "GAME OVER\nPress R to restart" if game_over else ""

func _restart() -> void:
	for arr in [bullets, enemy_bullets]:
		for b in arr: b.queue_free()
		arr.clear()
	for e in enemies: e.node.queue_free()
	enemies.clear()
	score = 0
	lives = 3
	wave = 0
	invuln = 2.0
	game_over = false
	player.position = Vector3.ZERO
	_spawn_wave()
