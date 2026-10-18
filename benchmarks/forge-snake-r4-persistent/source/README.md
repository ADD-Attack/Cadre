# R4 continuation sources

All asset changes start with the canonical own R3 GLB at the specified base commit. `build.py` removes asset meshes from the retained **own** R3 blend and uses its stage only. It never imports another entrant asset.

Required Windows Blender: `C:\Users\Moore\Blender\blender-4.5.14-windows-x64\blender.exe`. From the continuing checkout, pass each Python script's Windows UNC path (`wslpath -w`) with `-b --python`. `build.py` writes the canonical GLB before inserting review-only ORM-R multiplication, then saves a local ignored packed blend.

`render.py`: set `R4_MODE=preview` or `final`; `R4_TAG` labels iterations. `R4_BASELINE=1` imports untouched own R3; 0 renders the candidate. `R4_VIEWS=full,head` defaults to both frozen frames. Export environment names through `WSLENV` for Windows Blender. Final = 1920x1080, Cycles CPU256/adaptive0.01/OIDN. Do not use Workbench for judged captures.

`render_details.py` writes explicitly labeled 48-sample module, tail and terminal iteration views. These are not judged captures.

After the final GLB, `bash source/run-godot.sh` (from repository root, use the full benchmark-relative script path) starts a fresh evidence-project import with the requested Windows Godot4.7.2 binary, audits textures/tangents/shared mesh/rigid pose, then captures a native 1280x720 screenshot. The evidence project disables shader disk cache and uses the Linux-volume UNC path.

`validate_glb.py <GLB>` independently parses binary glTF using Python3 stdlib and enforces budgets, tangents, exact mesh-node counts, shared segment mesh, all-material packed ORM, opaque materials, no skin/Draco. `compare_rig.py <R3 GLB> <R4 GLB>` checks names/parents/local transforms.

Run `python3 source/finalize.py` only after actually viewing the final reference/checkpoints/production images. It checks all required files, paired active staging equality, intended glare sockets, PNG dimensions, engine results and binary hashes, and writes the evidence manifest into counts-and-log.json. Blender's process exit alone is not proof of Python success; final marker/file checks are mandatory.

Local `.blend` checkpoints and Godot derived import caches are intentionally ignored; the GLB, review captures, textures, previews, scripts, notes and evidence are delivered. Historical intermediate failures and superseded builds are isolated under logs/history; they are not the final outcome.
