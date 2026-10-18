extends SceneTree
func _init():
	print("R3_USER_DATA ",OS.get_user_data_dir())
	for p in ProjectSettings.get_property_list():
		var nm = String(p.name)
		if nm.contains("shader_cache") or nm.contains("shader_compiler"):
			print("R3_CACHE_SETTING ",nm," = ",ProjectSettings.get_setting(nm))
	quit()
