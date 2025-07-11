# coding=utf-8
import json

target_bones = {"sraw", "sraw_right_offset", "sraw_left_offset"}

animation_cache = {}
with open("../../sraw_rp/animations/sraw.animation_1st.json", "r") as f:
    json_data = json.load(f)

for anim_name, anim in json_data.get("animations", {}).items():
    length = anim.get("animation_length", 0.0)
    bones = anim.get("bones", {})
    bone_data = {}
    for bone_name, transforms in bones.items():
        if bone_name in target_bones:
            bone_data[bone_name] = {"rotation": {}, "position": {}}
            for attr in ["rotation", "position"]:
                if attr in transforms:
                    if isinstance(transforms[attr], list):
                        bone_data[bone_name][attr][0.0] = transforms[attr]
                    elif isinstance(transforms[attr], dict):
                        for k, v in transforms[attr].items():
                            bone_data[bone_name][attr][float(k)] = v
    animation_cache[anim_name.split(".")[2][4:]] = {
        "length": length,
        "bones": bone_data
    }
animation_cache["idle"] = {"bones": {}, "length": 0.0}

print(json.dumps(animation_cache, indent=4))
