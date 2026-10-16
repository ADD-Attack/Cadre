extends Node3D
## 3D Galaga demo. Arrow keys move, Space fires. Fully self-contained.
## r2: respawn shield, hit flashes, score popups, flapping enemies, engine trail,
## neon grid floor, parallax twinkling starfield, high score, safer restart.

const FIELD_W := 9.0
const FIELD_TOP := 11.0
const FIELD_BOTTOM := -1.0
const PLAYER_SPEED := 9.0
const BULLET_SPEED := 22.0
const ENEMY_BULLET_SPEED := 8.0
const FIRE_COOLDOWN := 0.18
const MAX_PLAYER_BULLETS := 6
const MAX_ENEMY_BULLETS := 14
const RESPAWN_SHIELD := 2.0
const GAME_OVER_DELAY := 1.2
const PLAYER_COL := Color(0.3, 0.8, 1.0)

var player: Node3D
var player_alive := true
var respawn_timer := 0.0
var shield_timer := 0.0
var fire_timer := 0.0
var game_over_timer := 0.0
var space_released := true
var bullets: Array = []
var enemy_bullets: Array = []
var enemies: Array = []
var particles: Array = []
var popups: Array = []
var stars: Array = []
var grid_lines: Array = []
var score := 0
var high_score := 0
var lives := 3
var wave := 0
var wave_delay := 0.0
var formation_t := 0.0
var shake := 0.0
var camera: Camera3D
var score_label: Label
var msg_label: Label
var lives_box: HBoxContainer
var shield_mesh: MeshInstance3D
var rng := RandomNumberGenerator.new()

var mat_player: StandardMaterial3D
var mat_bullet: StandardMaterial3D
var mat_ebullet: StandardMaterial3D
var mat_hit: StandardMaterial3D
var mat_trail: StandardMaterial3D
var mat_enemy: Array = []
var burst_mesh: BoxMesh
var burst_mats := {}


func _ready() -> void:
	rng.randomize()
	var win := get_window()
	win.size = Vector2i(1152, 648)
	# Scale the UI with the window so the HUD layout holds at any fullscreen resolution.
	win.content_scale_size = Vector2i(1152, 648)
	win.content_scale_mode = Window.CONTENT_SCALE_MODE_CANVAS_ITEMS
	win.content_scale_aspect = Window.CONTENT_SCALE_ASPECT_EXPAND
	win.mode = Window.MODE_FULLSCREEN
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
	mat_player = _emissive(PLAYER_COL, 1.2)
	mat_player.metallic = 0.6
	mat_player.roughness = 0.3
	mat_bullet = _emissive(Color(1.0, 1.0, 0.4), 4.0)
	mat_ebullet = _emissive(Color(1.0, 0.3, 0.3), 4.0)
	mat_hit = _emissive(Color(1, 1, 1), 6.0)
	mat_trail = _emissive(Color(1.0, 0.55, 0.15), 3.0)
	mat_trail.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat_enemy = [
		_emissive(Color(1.0, 0.3, 0.6), 1.5),
		_emissive(Color(0.4, 1.0, 0.4), 1.5),
		_emissive(Color(1.0, 0.7, 0.2), 1.5),
	]
	burst_mesh = BoxMesh.new()
	burst_mesh.size = Vector3.ONE * 0.12


func _setup_world() -> void:
	var env := WorldEnvironment.new()
	var e := Environment.new()
	e.background_mode = Environment.BG_COLOR
	e.background_color = Color(0.01, 0.01, 0.04)
	e.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	e.ambient_light_color = Color(0.3, 0.3, 0.4)
	e.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	e.glow_enabled = true
	e.glow_intensity = 1.0
	e.glow_bloom = 0.2
	e.fog_enabled = true
	e.fog_light_color = Color(0.05, 0.02, 0.12)
	e.fog_density = 0.015
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

	# Parallax starfield: three depth layers with varied size/colour, twinkling.
	var star_mesh := SphereMesh.new()
	star_mesh.radius = 0.04
	star_mesh.height = 0.08
	star_mesh.radial_segments = 6
	star_mesh.rings = 3
	var star_cols := [Color(0.9, 0.9, 1.0), Color(0.6, 0.8, 1.0), Color(1.0, 0.85, 0.6)]
	for i in 160:
		var s := MeshInstance3D.new()
		s.mesh = star_mesh
		var m := _emissive(star_cols[i % 3], rng.randf_range(1.0, 3.0))
		s.material_override = m
		s.position = Vector3(rng.randf_range(-22, 22), rng.randf_range(-6, 20), rng.randf_range(-20, -3))
		s.scale = Vector3.ONE * rng.randf_range(0.6, 1.8)
		s.set_meta("phase", rng.randf() * TAU)
		s.set_meta("base", m.emission_energy_multiplier)
		add_child(s)
		stars.append(s)

	# Neon grid floor scrolling toward the camera.
	var grid_mat := _emissive(Color(0.6, 0.1, 0.9), 1.5)
	var line_mesh := BoxMesh.new()
	line_mesh.size = Vector3(60, 0.03, 0.03)
	for i in 16:
		var g := MeshInstance3D.new()
		g.mesh = line_mesh
		g.material_override = grid_mat
		g.position = Vector3(0, -3.0, -20.0 + i * 2.5)
		add_child(g)
		grid_lines.append(g)
	var rail_mesh := BoxMesh.new()
	rail_mesh.size = Vector3(0.03, 0.03, 40)
	for i in 13:
		var r := MeshInstance3D.new()
		r.mesh = rail_mesh
		r.material_override = grid_mat
		r.position = Vector3(-18.0 + i * 3.0, -3.0, 0.0)
		add_child(r)

	var ui := CanvasLayer.new()
	add_child(ui)
	score_label = Label.new()
	score_label.position = Vector2(20, 12)
	score_label.add_theme_font_size_override("font_size", 24)
	score_label.add_theme_color_override("font_outline_color", Color(0, 0, 0))
	score_label.add_theme_constant_override("outline_size", 6)
	ui.add_child(score_label)
	lives_box = HBoxContainer.new()
	lives_box.position = Vector2(1040, 14)
	lives_box.add_theme_constant_override("separation", 8)
	ui.add_child(lives_box)
	msg_label = Label.new()
	msg_label.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	msg_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	msg_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	msg_label.add_theme_font_size_override("font_size", 40)
	msg_label.add_theme_color_override("font_color", Color(1.0, 0.9, 0.4))
	msg_label.add_theme_color_override("font_outline_color", Color(0.6, 0.1, 0.3))
	msg_label.add_theme_constant_override("outline_size", 10)
	ui.add_child(msg_label)
	var help := Label.new()
	help.text = "Arrows: move   Space: fire"
	help.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	help.position = Vector2(20, 648 - 36)
	help.modulate = Color(1, 1, 1, 0.7)
	ui.add_child(help)


func _refresh_lives() -> void:
	for c in lives_box.get_children():
		c.queue_free()
	for i in maxi(lives, 0):
		var r := ColorRect.new()
		r.custom_minimum_size = Vector2(18, 18)
		r.color = PLAYER_COL
		r.rotation = PI / 4.0
		lives_box.add_child(r)


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
	var cockpit := MeshInstance3D.new()
	var cm := SphereMesh.new()
	cm.radius = 0.16
	cm.height = 0.32
	cockpit.mesh = cm
	cockpit.position = Vector3(0, 0.05, 0.22)
	cockpit.material_override = _emissive(Color(1.0, 1.0, 1.0), 3.0)
	player.add_child(cockpit)
	for side in [-1, 1]:
		var tip := MeshInstance3D.new()
		var tm := BoxMesh.new()
		tm.size = Vector3(0.12, 0.45, 0.12)
		tip.mesh = tm
		tip.position = Vector3(side * 0.8, -0.2, 0)
		tip.material_override = mat_ebullet
		player.add_child(tip)
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
	light.light_color = PLAYER_COL
	light.omni_range = 3.0
	player.add_child(light)
	shield_mesh = MeshInstance3D.new()
	var sm := SphereMesh.new()
	sm.radius = 1.0
	sm.height = 2.0
	shield_mesh.mesh = sm
	var smat := _emissive(Color(0.4, 0.9, 1.0), 2.0)
	smat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	smat.albedo_color.a = 0.18
	smat.cull_mode = BaseMaterial3D.CULL_DISABLED
	shield_mesh.material_override = smat
	shield_mesh.visible = false
	player.add_child(shield_mesh)
	player.position = Vector3.ZERO
	add_child(player)
	player_alive = true
	_refresh_lives()


func _spawn_wave() -> void:
	wave += 1
	var cols := 8
	var rows := 3
	for r in rows:
		for c in cols:
			var e := Node3D.new()
			var mi := MeshInstance3D.new()
			mi.name = "Body"
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
				w.name = "WingL" if side < 0 else "WingR"
				w.position.x = side * 0.55
				w.material_override = mat_enemy[(r + 1) % 3]
				e.add_child(w)
			for side in [-1, 1]:
				var eye := MeshInstance3D.new()
				var em := SphereMesh.new()
				em.radius = 0.07
				em.height = 0.14
				eye.mesh = em
				eye.position = Vector3(side * 0.15, 0.05, 0.32)
				eye.material_override = mat_hit
				e.add_child(eye)
			var home := Vector3((c - (cols - 1) / 2.0) * 1.6, 8.0 + r * 1.2, 0)
			# Stagger entry: each enemy swoops in from alternating sides.
			var side_in := -1.0 if c < cols / 2 else 1.0
			e.position = home + Vector3(side_in * 10.0, 8.0 + r * 1.5, 0)
			e.set_meta("home", home)
			e.set_meta("state", "enter")
			e.set_meta("dive_t", 0.0)
			e.set_meta("hp", 2 if r == 0 else 1)
			e.set_meta("base_mat", mat_enemy[r % 3])
			e.set_meta("flash", 0.0)
			e.set_meta("delay", (r * cols + c) * 0.05)
			add_child(e)
			enemies.append(e)
	_flash_msg("WAVE %d" % wave)


func _flash_msg(t: String) -> void:
	msg_label.text = t
	msg_label.modulate.a = 1.0


func _process(delta: float) -> void:
	delta = minf(delta, 0.05)  # Avoid tunnelling/huge jumps on hitches.
	_update_player(delta)
	_update_bullets(delta)
	_update_enemies(delta)
	_update_particles(delta)
	_update_popups(delta)
	_update_background(delta)
	_check_collisions()
	if enemies.is_empty() and lives > 0:
		wave_delay += delta
		if wave_delay > 1.0:
			wave_delay = 0.0
			_spawn_wave()
	if lives <= 0:
		msg_label.text = "GAME OVER\nSCORE %d\n%s" % [score, "Press Space to restart" if game_over_timer <= 0.0 else ""]
		msg_label.modulate.a = 0.75 + 0.25 * sin(formation_t * 4.0)
	else:
		msg_label.modulate.a = maxf(0.0, msg_label.modulate.a - delta * 0.6)
	high_score = maxi(high_score, score)
	score_label.text = "SCORE %06d   HI %06d   WAVE %d" % [score, high_score, wave]
	shake = maxf(0.0, shake - delta * 3.0)
	camera.h_offset = rng.randf_range(-1, 1) * shake * 0.3
	camera.v_offset = rng.randf_range(-1, 1) * shake * 0.3


func _update_player(delta: float) -> void:
	var space := Input.is_physical_key_pressed(KEY_SPACE)
	if lives <= 0:
		# Require a fresh press after the delay so a held fire key can't skip the screen.
		game_over_timer -= delta
		if not space:
			space_released = true
		elif space_released and game_over_timer <= 0.0:
			_restart()
		return
	if not player_alive:
		respawn_timer -= delta
		if respawn_timer <= 0.0:
			player.visible = true
			player.position = Vector3.ZERO
			player.rotation = Vector3.ZERO
			player_alive = true
			shield_timer = RESPAWN_SHIELD
		return
	shield_timer = maxf(0.0, shield_timer - delta)
	shield_mesh.visible = shield_timer > 0.0 and fmod(shield_timer, 0.2) > 0.07
	var dir := Vector2.ZERO
	if Input.is_physical_key_pressed(KEY_LEFT): dir.x -= 1
	if Input.is_physical_key_pressed(KEY_RIGHT): dir.x += 1
	if Input.is_physical_key_pressed(KEY_UP): dir.y += 1
	if Input.is_physical_key_pressed(KEY_DOWN): dir.y -= 1
	player.position.x = clampf(player.position.x + dir.x * PLAYER_SPEED * delta, -FIELD_W, FIELD_W)
	player.position.y = clampf(player.position.y + dir.y * PLAYER_SPEED * delta, FIELD_BOTTOM, 3.0)
	player.rotation.y = lerpf(player.rotation.y, -dir.x * 0.5, delta * 8.0)
	player.rotation.z = lerpf(player.rotation.z, -dir.x * 0.25, delta * 8.0)
	var flame: Node3D = player.get_node("Flame")
	var thrust := 1.4 if dir.y > 0 else 1.0
	flame.scale = Vector3(1, thrust, 1) * rng.randf_range(0.8, 1.3)
	if rng.randf() < 0.6:
		_trail(player.position + Vector3(rng.randf_range(-0.08, 0.08), -0.8, 0))
	fire_timer -= delta
	if space and fire_timer <= 0.0 and bullets.size() < MAX_PLAYER_BULLETS:
		fire_timer = FIRE_COOLDOWN
		_fire(player.position + Vector3(0, 0.8, 0), Vector3.UP * BULLET_SPEED, false)
		_burst(player.position + Vector3(0, 0.8, 0), Color(1, 1, 0.5), 4, 2.0, 0.15)


func _trail(pos: Vector3) -> void:
	var p := MeshInstance3D.new()
	p.mesh = burst_mesh
	p.material_override = mat_trail
	p.position = pos
	p.set_meta("vel", Vector3(rng.randf_range(-0.3, 0.3), -3.0, 0))
	p.set_meta("life", 0.3)
	p.set_meta("max", 0.3)
	add_child(p)
	particles.append(p)


func _fire(pos: Vector3, vel: Vector3, enemy: bool) -> void:
	if enemy and enemy_bullets.size() >= MAX_ENEMY_BULLETS:
		return
	var b := MeshInstance3D.new()
	var cm := CapsuleMesh.new()
	cm.radius = 0.08 if not enemy else 0.12
	cm.height = 0.6 if not enemy else 0.35
	b.mesh = cm
	b.material_override = mat_ebullet if enemy else mat_bullet
	b.position = pos
	b.set_meta("vel", vel)
	# Orient the capsule along its velocity.
	if vel.length() > 0.01 and not enemy:
		b.rotation.z = atan2(-vel.x, vel.y)
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
			if list == enemy_bullets:
				b.rotation.y += delta * 10.0
			if b.position.y > FIELD_TOP + 8 or b.position.y < FIELD_BOTTOM - 3 or absf(b.position.x) > 20:
				list.erase(b)
				b.queue_free()


func _update_enemies(delta: float) -> void:
	formation_t += delta
	var sway := sin(formation_t * 0.8) * 1.5
	var breathe := 1.0 + sin(formation_t * 1.6) * 0.06
	var divers := 0
	for e in enemies:
		if e.get_meta("state") == "dive":
			divers += 1
	for e in enemies:
		var h: Vector3 = e.get_meta("home")
		var home := Vector3(h.x * breathe + sway, h.y, h.z)
		var state: String = e.get_meta("state")
		# Wing flap + hit flash for every enemy.
		var flap := sin(formation_t * 10.0 + h.x) * 0.5
		(e.get_node("WingL") as Node3D).rotation.y = flap
		(e.get_node("WingR") as Node3D).rotation.y = -flap
		var fl: float = e.get_meta("flash")
		if fl > 0.0:
			fl -= delta
			e.set_meta("flash", fl)
			if fl <= 0.0:
				(e.get_node("Body") as MeshInstance3D).material_override = e.get_meta("base_mat")
		match state:
			"enter":
				var dl: float = e.get_meta("delay")
				if dl > 0.0:
					e.set_meta("delay", dl - delta)
					continue
				e.position = e.position.lerp(home, delta * 2.5)
				e.rotation.z = (home.x - e.position.x) * -0.1
				if e.position.distance_to(home) < 0.15:
					e.set_meta("state", "form")
			"form":
				e.position = e.position.lerp(home, delta * 5.0)
				e.rotation.z = sin(formation_t * 3.0 + h.x) * 0.15
				e.rotation.y = lerpf(e.rotation.y, 0.0, delta * 5.0)
				if player_alive and lives > 0 and divers < 2 + wave and rng.randf() < 0.002 * (1 + wave * 0.5):
					e.set_meta("state", "dive")
					e.set_meta("dive_t", 0.0)
					e.set_meta("dive_start", e.position)
					e.set_meta("dive_dir", 1.0 if rng.randf() < 0.5 else -1.0)
					divers += 1
				if player_alive and lives > 0 and rng.randf() < 0.0008 * wave:
					_fire(e.position, Vector3.DOWN * ENEMY_BULLET_SPEED, true)
			"dive":
				var t: float = e.get_meta("dive_t") + delta
				e.set_meta("dive_t", t)
				var start: Vector3 = e.get_meta("dive_start")
				var d: float = e.get_meta("dive_dir")
				e.position = start + Vector3(sin(t * 2.0) * 4.0 * d, -t * 5.0, 0)
				e.position.x = clampf(e.position.x, -FIELD_W - 2.0, FIELD_W + 2.0)
				e.rotation.z = cos(t * 2.0) * d * 0.8
				e.rotation.y += delta * 6.0
				# Only fire while above the player, aimed, and only if the player can be hit.
				if player_alive and lives > 0 and e.position.y > player.position.y + 1.5 and rng.randf() < 0.02:
					var aim: Vector3 = (player.position - e.position).normalized() * ENEMY_BULLET_SPEED
					_fire(e.position, aim, true)
				if e.position.y < FIELD_BOTTOM - 3:
					e.position = Vector3(home.x, FIELD_TOP + 6.0, 0)
					e.rotation = Vector3.ZERO
					e.set_meta("delay", 0.0)
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
					var col: Color = (e.get_meta("base_mat") as StandardMaterial3D).albedo_color
					_explode(e.position, col)
					var pts := 200 if e.get_meta("state") == "dive" else 100
					score += pts
					_popup(e.position, str(pts), col)
					e.queue_free()
				else:
					(e.get_node("Body") as MeshInstance3D).material_override = mat_hit
					e.set_meta("flash", 0.08)
					_burst(e.position, Color.WHITE, 8, 4.0, 0.3)
				break
	if not player_alive or lives <= 0:
		return
	var shielded := shield_timer > 0.0
	for b in enemy_bullets.duplicate():
		if b.position.distance_to(player.position) < 0.6:
			enemy_bullets.erase(b)
			b.queue_free()
			if shielded:
				_burst(b.position, Color(0.4, 0.9, 1.0), 6, 3.0, 0.25)
				continue
			_kill_player()
			return
	for e in enemies.duplicate():
		if e.position.distance_to(player.position) < 0.9:
			enemies.erase(e)
			_explode(e.position, Color(1, 0.5, 0.2))
			score += 100 if shielded else 0
			e.queue_free()
			if not shielded:
				_kill_player()
				return


func _kill_player() -> void:
	_explode(player.position, PLAYER_COL, 60)
	player.visible = false
	shield_mesh.visible = false
	player_alive = false
	lives -= 1
	_refresh_lives()
	respawn_timer = 1.5
	shake = 1.5
	fire_timer = 1.0
	# Clear incoming fire so the respawn isn't an instant death.
	for b in enemy_bullets:
		b.queue_free()
	enemy_bullets.clear()
	if lives <= 0:
		game_over_timer = GAME_OVER_DELAY
		space_released = false


func _explode(pos: Vector3, col: Color, n := 30) -> void:
	_burst(pos, col, n, 8.0, 0.8)
	_burst(pos, Color(1, 0.9, 0.5), n / 2, 4.0, 0.5)
	# Expanding shockwave ring.
	var ring := MeshInstance3D.new()
	var tm := TorusMesh.new()
	tm.inner_radius = 0.45
	tm.outer_radius = 0.5
	ring.mesh = tm
	var rm := _emissive(col, 4.0)
	rm.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	ring.material_override = rm
	ring.position = pos
	ring.rotation.x = PI / 2.0
	add_child(ring)
	var rt := create_tween().set_parallel()
	rt.tween_property(ring, "scale", Vector3.ONE * 4.0, 0.4).set_ease(Tween.EASE_OUT).set_trans(Tween.TRANS_CUBIC)
	rt.tween_property(rm, "albedo_color:a", 0.0, 0.4)
	rt.chain().tween_callback(ring.queue_free)
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
	# Cache one material per colour instead of allocating every burst.
	var key := col.to_html()
	if not burst_mats.has(key):
		burst_mats[key] = _emissive(col, 4.0)
	var mat: StandardMaterial3D = burst_mats[key]
	for i in n:
		var p := MeshInstance3D.new()
		p.mesh = burst_mesh
		p.material_override = mat
		p.position = pos
		var v := Vector3(rng.randf_range(-1, 1), rng.randf_range(-1, 1), rng.randf_range(-1, 1)).normalized()
		p.set_meta("vel", v * speed * rng.randf_range(0.3, 1.0))
		p.set_meta("life", life * rng.randf_range(0.6, 1.0))
		p.set_meta("max", p.get_meta("life"))
		add_child(p)
		particles.append(p)


func _popup(pos: Vector3, text: String, col: Color) -> void:
	var l := Label3D.new()
	l.text = text
	l.modulate = col.lightened(0.4)
	l.outline_modulate = Color(0, 0, 0)
	l.font_size = 48
	l.pixel_size = 0.01
	l.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	l.no_depth_test = true
	l.position = pos + Vector3(0, 0, 0.5)
	l.set_meta("life", 0.8)
	add_child(l)
	popups.append(l)


func _update_popups(delta: float) -> void:
	for l in popups.duplicate():
		var life: float = l.get_meta("life") - delta
		if life <= 0.0:
			popups.erase(l)
			l.queue_free()
			continue
		l.set_meta("life", life)
		l.position.y += delta * 1.5
		l.modulate.a = clampf(life / 0.4, 0.0, 1.0)
		l.outline_modulate.a = l.modulate.a


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
		p.scale = Vector3.ONE * maxf(0.01, life / p.get_meta("max"))


func _update_background(delta: float) -> void:
	for s in stars:
		s.position.y -= delta * (2.0 + s.position.z * -0.2)
		if s.position.y < -6:
			s.position.y = 20
			s.position.x = rng.randf_range(-22, 22)
		var m: StandardMaterial3D = s.material_override
		m.emission_energy_multiplier = s.get_meta("base") * (0.6 + 0.4 * sin(formation_t * 3.0 + s.get_meta("phase")))
	for g in grid_lines:
		g.position.z += delta * 4.0
		if g.position.z > 20.0:
			g.position.z -= 40.0


func _restart() -> void:
	for list in [bullets, enemy_bullets, enemies, particles, popups]:
		for n in list:
			n.queue_free()
		list.clear()
	score = 0
	lives = 3
	wave = 0
	wave_delay = 0.0
	fire_timer = FIRE_COOLDOWN
	shield_timer = RESPAWN_SHIELD
	player.visible = true
	player.position = Vector3.ZERO
	player.rotation = Vector3.ZERO
	player_alive = true
	msg_label.modulate.a = 0.0
	_refresh_lives()
	_spawn_wave()
