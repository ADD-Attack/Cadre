extends Node3D
## 3D Galaga demo. Arrow keys move, Space fires. Fully self-contained.

const FIELD_W := 9.0
const FIELD_TOP := 11.0
const FIELD_BOTTOM := -1.0
const PLAYER_SPEED := 9.0
const BULLET_SPEED := 22.0
const ENEMY_BULLET_SPEED := 8.0
const FIRE_COOLDOWN := 0.18

var player: Node3D
var player_alive := true
var respawn_timer := 0.0
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
var shake := 0.0
var camera: Camera3D
var score_label: Label
var msg_label: Label
var rng := RandomNumberGenerator.new()

var mat_player: StandardMaterial3D
var mat_bullet: StandardMaterial3D
var mat_ebullet: StandardMaterial3D
var mat_enemy: Array = []


func _ready() -> void:
	rng.randomize()
	get_window().size = Vector2i(1152, 648)
	get_window().mode = Window.MODE_FULLSCREEN
	_make_materials()
	_setup_world()
	_spawn_player()
	_spawn_wave()


func _emissive(c: Color, energy := 2.0) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.emission_enabled = true
	m.emission = c
	m.emission_energy_multiplier = energy
	return m


func _make_materials() -> void:
	mat_player = _emissive(Color(0.3, 0.8, 1.0), 1.2)
	mat_bullet = _emissive(Color(1.0, 1.0, 0.4), 4.0)
	mat_ebullet = _emissive(Color(1.0, 0.3, 0.3), 4.0)
	mat_enemy = [
		_emissive(Color(1.0, 0.3, 0.6), 1.5),
		_emissive(Color(0.4, 1.0, 0.4), 1.5),
		_emissive(Color(1.0, 0.7, 0.2), 1.5),
	]


func _setup_world() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.01, 0.01, 0.04)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.3, 0.3, 0.4)
	e.glow_enabled = true
	e.glow_intensity = 1.0
	e.glow_bloom = 0.2
	env.environment = e
	add_child(env)

	var sun := DirectionalLight3D.new()
	sun.rotation_degrees = Vector3(-50, 30, 0)
	add_child(sun)

	camera = Camera3D.new()
	camera.fov = 55
	add_child(camera)
	camera.look_at_from_position(Vector3(0, 2.0, 16.0), Vector3(0, 5.0, 0))
	camera.current = true

	# Starfield
	var star_mesh := SphereMesh.new()
	star_mesh.radius = 0.04
	star_mesh.height = 0.08
	var star_mat := _emissive(Color(0.9, 0.9, 1.0), 2.0)
	for i in 120:
		var s := MeshInstance3D.new()
		s.mesh = star_mesh
		s.material_override = star_mat
		s.position = Vector3(rng.randf_range(-18, 18), rng.randf_range(-6, 20), rng.randf_range(-15, -3))
		add_child(s)
		stars.append(s)

	var ui := CanvasLayer.new()
	add_child(ui)
	score_label = Label.new()
	score_label.position = Vector2(20, 12)
	score_label.add_theme_font_size_override("font_size", 24)
	ui.add_child(score_label)
	msg_label = Label.new()
	msg_label.set_anchors_preset(Control.PRESET_CENTER)
	msg_label.position = Vector2(576 - 200, 300)
	msg_label.size = Vector2(400, 60)
	msg_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	msg_label.add_theme_font_size_override("font_size", 32)
	ui.add_child(msg_label)
	var help := Label.new()
	help.text = "Arrows: move   Space: fire"
	help.position = Vector2(20, 610)
	ui.add_child(help)


func _spawn_player() -> void:
	player = Node3D.new()
	var body := MeshInstance3D.new()
	var pm := PrismMesh.new()
	pm.size = Vector3(1.0, 1.2, 0.5)
	body.mesh = pm
	body.material_override = mat_player
	player.add_child(body)
	var wings := MeshInstance3D.new()
	var wm := BoxMesh.new()
	wm.size = Vector3(1.6, 0.2, 0.3)
	wings.mesh = wm
	wings.position.y = -0.35
	wings.material_override = mat_player
	player.add_child(wings)
	var flame := MeshInstance3D.new()
	var fm := SphereMesh.new()
	fm.radius = 0.15
	fm.height = 0.4
	flame.mesh = fm
	flame.name = "Flame"
	flame.position.y = -0.7
	flame.material_override = _emissive(Color(1.0, 0.5, 0.1), 5.0)
	player.add_child(flame)
	var light := OmniLight3D.new()
	light.light_color = Color(0.3, 0.8, 1.0)
	light.omni_range = 3.0
	player.add_child(light)
	player.position = Vector3(0, 0, 0)
	add_child(player)
	player_alive = true


func _spawn_wave() -> void:
	wave += 1
	var cols := 8
	var rows := 3
	for r in rows:
		for c in cols:
			var e := Node3D.new()
			var mi := MeshInstance3D.new()
			if r == 0:
				var bm := BoxMesh.new()
				bm.size = Vector3(0.9, 0.6, 0.6)
				mi.mesh = bm
			else:
				var sm := SphereMesh.new()
				sm.radius = 0.4
				sm.height = 0.6
				mi.mesh = sm
			mi.material_override = mat_enemy[r % 3]
			e.add_child(mi)
			for side in [-1, 1]:
				var w := MeshInstance3D.new()
				var wb := BoxMesh.new()
				wb.size = Vector3(0.35, 0.5, 0.1)
				w.mesh = wb
				w.position.x = side * 0.55
				w.material_override = mat_enemy[(r + 1) % 3]
				e.add_child(w)
			var home := Vector3((c - (cols - 1) / 2.0) * 1.6, 8.0 + r * 1.2, 0)
			e.position = home + Vector3(0, 8, 0)
			e.set_meta("home", home)
			e.set_meta("state", "enter")
			e.set_meta("dive_t", 0.0)
			e.set_meta("hp", 2 if r == 0 else 1)
			add_child(e)
			enemies.append(e)
	_flash_msg("WAVE %d" % wave)


func _flash_msg(t: String) -> void:
	msg_label.text = t
	msg_label.modulate.a = 1.0


func _process(delta: float) -> void:
	_update_player(delta)
	_update_bullets(delta)
	_update_enemies(delta)
	_update_particles(delta)
	_update_stars(delta)
	_check_collisions()
	if enemies.is_empty():
		_spawn_wave()
	msg_label.modulate.a = maxf(0.0, msg_label.modulate.a - delta * 0.6)
	if lives <= 0:
		msg_label.text = "GAME OVER - Space to restart"
		msg_label.modulate.a = 1.0
	score_label.text = "SCORE %06d   LIVES %d   WAVE %d" % [score, maxi(lives, 0), wave]
	shake = maxf(0.0, shake - delta * 3.0)
	camera.h_offset = rng.randf_range(-1, 1) * shake * 0.3
	camera.v_offset = rng.randf_range(-1, 1) * shake * 0.3


func _update_player(delta: float) -> void:
	if lives <= 0:
		if Input.is_physical_key_pressed(KEY_SPACE) and fire_timer <= 0.0:
			_restart()
		fire_timer -= delta
		return
	if not player_alive:
		respawn_timer -= delta
		if respawn_timer <= 0.0:
			player.visible = true
			player.position = Vector3(0, 0, 0)
			player_alive = true
		return
	var dir := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_LEFT): dir.x -= 1
	if Input.is_physical_key_pressed(KEY_RIGHT): dir.x += 1
	if Input.is_physical_key_pressed(KEY_UP): dir.y += 1
	if Input.is_physical_key_pressed(KEY_DOWN): dir.y -= 1
	player.position.x = clampf(player.position.x + dir.x * PLAYER_SPEED * delta, -FIELD_W, FIELD_W)
	player.position.y = clampf(player.position.y + dir.y * PLAYER_SPEED * delta, FIELD_BOTTOM, 3.0)
	player.rotation.y = lerpf(player.rotation.y, -dir.x * 0.5, delta * 8.0)
	var flame: Node3D = player.get_node("Flame")
	flame.scale = Vector3.ONE * rng.randf_range(0.8, 1.3)
	fire_timer -= delta
	if Input.is_physical_key_pressed(KEY_SPACE) and fire_timer <= 0.0:
		fire_timer = FIRE_COOLDOWN
		_fire(player.position + Vector3(0, 0.8, 0), Vector3.UP * BULLET_SPEED, false)
		_burst(player.position + Vector3(0, 0.8, 0), Color(1, 1, 0.5), 4, 2.0, 0.15)


func _fire(pos: Vector3, vel: Vector3, enemy: bool) -> void:
	var b := MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = 0.08 if not enemy else 0.12
	cm.height = 0.6 if not enemy else 0.35
	b.mesh = cm
	b.material_override = mat_ebullet if enemy else mat_bullet
	b.position = pos
	b.set_meta("vel", vel)
	var l := OmniLight3D.new()
	l.light_color = Color(1, 0.3, 0.3) if enemy else Color(1, 1, 0.4)
	l.omni_range = 1.5
	b.add_child(l)
	add_child(b)
	(enemy_bullets if enemy else bullets).append(b)


func _update_bullets(delta: float) -> void:
	for list in [bullets, enemy_bullets]:
		for b in list.duplicate():
			b.position += b.get_meta("vel") * delta
			if b.position.y > FIELD_TOP + 8 or b.position.y < FIELD_BOTTOM - 3 or absf(b.position.x) > 20:
				list.erase(b)
				b.queue_free()


func _update_enemies(delta: float) -> void:
	formation_t += delta
	var sway := sin(formation_t * 0.8) * 1.5
	var divers := 0
	for e in enemies:
		if e.get_meta("state") == "dive":
			divers += 1
	for e in enemies:
		var home: Vector3 = e.get_meta("home") + Vector3(sway, 0, 0)
		var state: String = e.get_meta("state")
		match state:
			"enter":
				e.position = e.position.lerp(home, delta * 2.0)
				if e.position.distance_to(home) < 0.1:
					e.set_meta("state", "form")
			"form":
				e.position = e.position.lerp(home, delta * 5.0)
				e.rotation.z = sin(formation_t * 3.0 + home.x) * 0.15
				if player_alive and lives > 0 and divers < 2 + wave and rng.randf() < 0.002 * (1 + wave * 0.5):
					e.set_meta("state", "dive")
					e.set_meta("dive_t", 0.0)
					e.set_meta("dive_start", e.position)
					e.set_meta("dive_dir", 1.0 if rng.randf() < 0.5 else -1.0)
					divers += 1
				if lives > 0 and rng.randf() < 0.0008 * wave:
					_fire(e.position, Vector3.DOWN * ENEMY_BULLET_SPEED, true)
			"dive":
				var t: float = e.get_meta("dive_t") + delta
				e.set_meta("dive_t", t)
				var start: Vector3 = e.get_meta("dive_start")
				var d: float = e.get_meta("dive_dir")
				e.position = start + Vector3(sin(t * 2.0) * 4.0 * d, -t * 5.0, 0)
				e.rotation.z = cos(t * 2.0) * d * 0.8
				e.rotation.y += delta * 6.0
				if rng.randf() < 0.02 and lives > 0:
					var aim: Vector3 = (player.position - e.position).normalized() * ENEMY_BULLET_SPEED
					_fire(e.position, aim, true)
				if e.position.y < FIELD_BOTTOM - 3:
					e.position = home + Vector3(0, 8, 0)
					e.rotation = Vector3.ZERO
					e.set_meta("state", "enter")


func _check_collisions() -> void:
	for b in bullets.duplicate():
		for e in enemies.duplicate():
			if b.position.distance_to(e.position) < 0.7:
				bullets.erase(b)
				b.queue_free()
				var hp: int = e.get_meta("hp") - 1
				e.set_meta("hp", hp)
				if hp <= 0:
					enemies.erase(e)
					var col: Color = (e.get_child(0) as MeshInstance3D).material_override.albedo_color
					_explode(e.position, col)
					score += 200 if e.get_meta("state") == "dive" else 100
					e.queue_free()
				else:
					_burst(e.position, Color.WHITE, 8, 4.0, 0.3)
				break
	if not player_alive or lives <= 0:
		return
	for b in enemy_bullets.duplicate():
		if b.position.distance_to(player.position) < 0.6:
			enemy_bullets.erase(b)
			b.queue_free()
			_kill_player()
			return
	for e in enemies:
		if e.position.distance_to(player.position) < 0.9:
			enemies.erase(e)
			_explode(e.position, Color(1, 0.5, 0.2))
			e.queue_free()
			_kill_player()
			return


func _kill_player() -> void:
	_explode(player.position, Color(0.3, 0.8, 1.0), 60)
	player.visible = false
	player_alive = false
	lives -= 1
	respawn_timer = 1.5
	shake = 1.5
	fire_timer = 1.0


func _explode(pos: Vector3, col: Color, n := 30) -> void:
	_burst(pos, col, n, 8.0, 0.8)
	_burst(pos, Color(1, 0.9, 0.5), n / 2, 4.0, 0.5)
	var flash := OmniLight3D.new()
	flash.light_color = col
	flash.light_energy = 6.0
	flash.omni_range = 5.0
	flash.position = pos
	add_child(flash)
	var tw := create_tween()
	tw.tween_property(flash, "light_energy", 0.0, 0.4)
	tw.tween_callback(flash.queue_free)
	shake = maxf(shake, 0.4)


func _burst(pos: Vector3, col: Color, n: int, speed: float, life: float) -> void:
	var mesh := BoxMesh.new()
	mesh.size = Vector3.ONE * 0.12
	var mat := _emissive(col, 4.0)
	mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	for i in n:
		var p := MeshInstance3D.new()
		p.mesh = mesh
		p.material_override = mat
		p.position = pos
		var v := Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1)).normalized()
		p.set_meta("vel", v * speed * rng.randf_range(0.3, 1.0))
		p.set_meta("life", life * rng.randf_range(0.6, 1.0))
		p.set_meta("max", p.get_meta("life"))
		add_child(p)
		particles.append(p)


func _update_particles(delta: float) -> void:
	for p in particles.duplicate():
		var life: float = p.get_meta("life") - delta
		if life <= 0:
			particles.erase(p)
			p.queue_free()
			continue
		p.set_meta("life", life)
		var v: Vector3 = p.get_meta("vel") * (1.0 - delta * 2.0)
		p.set_meta("vel", v)
		p.position += v * delta
		p.rotation += Vector3(delta * 5, delta * 7, 0)
		p.scale = Vector3.ONE * (life / p.get_meta("max"))


func _update_stars(delta: float) -> void:
	for s in stars:
		s.position.y -= delta * (2.0 + s.position.z * -0.2)
		if s.position.y < -6:
			s.position.y = 20
			s.position.x = rng.randf_range(-18, 18)


func _restart() -> void:
	for list in [bullets, enemy_bullets, enemies, particles]:
		for n in list:
			n.queue_free()
		list.clear()
	score = 0
	lives = 3
	wave = 0
	fire_timer = FIRE_COOLDOWN
	player.visible = true
	player.position = Vector3.ZERO
	player_alive = true
	_spawn_wave()
