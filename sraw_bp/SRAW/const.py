STATES = {"transition", "re_transition", "idle", "run", "aim", "equip"}
SPECIAL_ENTITIES = set("minecraft:" + entity for entity in [
    "npc", "armor_stand", "tripod_camera", "item", "tnt", "falling_block", "moving_block", "xp_bottle",
    "xp_orb", "eye_of_ender_signal", "fireworks_rocket", "thrown_trident", "shulker_bullet", "fishing_hook",
    "chalkboard", "dragon_fireball", "arrow", "snowball", "egg", "painting",
    "fireball", "splash_potion", "ender_pearl", "leash_knot", "wither_skull", "wither_skull_dangerous",
    "boat", "lightning_bolt", "small_fireball", "area_effect_cloud",
    "chest_minecart", "command_block_minecart", "lingering_potion", "llama_spit",
    "evocation_fang"]) | set("orchiella:" + entity for entity in [
    "absorption_bomb",
    "remote_bomb", "remote_bomb_lightning", "remote_bomb_flame",
    "remote_bomb_quake",
    "heal_bomb",
    "electric_arrow"])
PENETRABLE_BLOCK_TYPE = set("minecraft:" + block for block in {"air","short_grass",
                                                               "flowing_water", "water", "flowing_lava", "lava",
                                                               "end_portal", "portal", "fire", "grass", "snow_layer",
                                                               "double_plant", "tall_grass", "vine", "redstone", "torch",
                                                               "sapling", "red_flower", "yellow_flower"})
ANIM_CACHE = {
    "aim": {
        "bones": {
            "sraw_right_offset": {
                "position": {
                    "0.0": [
                        0,
                        5,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        0,
                        0,
                        0
                    ]
                }
            },
            "sraw_left_offset": {
                "position": {
                    "0.0": [
                        0,
                        7,
                        2
                    ]
                },
                "rotation": {
                    "0.0": [
                        -5,
                        0,
                        0
                    ]
                }
            },
            "sraw": {
                "position": {
                    "0.0": [
                        0,
                        0,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        -20,
                        0,
                        5
                    ]
                }
            }
        },
        "length": 0.0
    },
    "equip": {
        "bones": {
            "sraw_right_offset": {
                "position": {
                    "0.0": [
                        0,
                        -0.79335,
                        -0.60876
                    ],
                    "0.5833": [
                        0,
                        0,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        31.31893,
                        13.80192,
                        10.86531
                    ],
                    "0.5833": [
                        0,
                        0,
                        0
                    ]
                }
            },
            "sraw_left_offset": {
                "position": {
                    "0.0": [
                        -0.2706,
                        -0.78633,
                        -0.5554
                    ],
                    "0.5833": [
                        0,
                        0,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        27.47766,
                        -1.15408,
                        2.21783
                    ],
                    "0.5833": [
                        0,
                        0,
                        0
                    ]
                }
            }
        },
        "length": 0.5833
    },
    "idle": {
        "bones": {},
        "length": 0.0
    },
    "run": {
        "bones": {
            "sraw_right_offset": {
                "position": {},
                "rotation": {
                    "0.0": [
                        12.5,
                        0,
                        0
                    ],
                    "0.5": [
                        12.5,
                        0,
                        0
                    ],
                    "0.25": [
                        17.48436,
                        0.75155,
                        -2.38443
                    ]
                }
            },
            "sraw_left_offset": {
                "position": {},
                "rotation": {
                    "0.0": [
                        19.8423,
                        2.55868,
                        -7.05239
                    ],
                    "0.5": [
                        19.8423,
                        2.55868,
                        -7.05239
                    ],
                    "0.25": [
                        42.39865,
                        -0.81209,
                        -3.35848
                    ]
                }
            },
            "sraw": {
                "position": {
                    "0.0": [
                        0,
                        1,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        0,
                        0,
                        0
                    ]
                }
            }
        },
        "length": 0.5
    }
}