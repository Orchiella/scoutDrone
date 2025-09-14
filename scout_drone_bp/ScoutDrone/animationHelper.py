# coding=utf-8
import json

ModName = "ScoutDrone"
mod_name = ''.join(['_' + c.lower() if c.isupper() and i != 0 else c.lower() for i, c in enumerate(ModName)])

animation_cache = {}
for perspective in {"1st","3rd"}:
    target_bones = {"drone", "rightArm", "leftArm"}
    with open(
            "D:/MCStudioDownload/work/valorin233@163.com/Cpp/AddOn/{}/{}_rp/animations/{}_launcher.animation_{}.json".format(
                ModName,
                mod_name,
                mod_name,
                perspective),
            "r") as f:
        json_data = json.load(f)

    for anim_name, anim in json_data.get("animations", {}).items():
        loop = anim.get("loop", False)
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
                                if isinstance(v, dict):
                                    bone_data[bone_name][attr][float(k)] = v['post']
                                else:
                                    if isinstance(v[0], str):
                                        continue
                                    bone_data[bone_name][attr][float(k)] = v
            animation_cache[perspective + "_" + anim_name.split(".")[2][4:]] = {
                "loop": loop,
                "length": length,
                "bones": bone_data
            }

print(json.dumps(animation_cache, indent=4))
