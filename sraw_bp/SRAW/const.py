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
PENETRABLE_BLOCK_TYPE = set("minecraft:" + block for block in {"air", "short_grass",
                                                               "flowing_water", "water", "flowing_lava", "lava",
                                                               "end_portal", "portal", "fire", "grass", "snow_layer",
                                                               "double_plant", "tall_grass", "vine", "redstone",
                                                               "torch",
                                                               "sapling", "red_flower", "yellow_flower"})
TRANSITION_DURATION = 0.25
ANIM_CACHE = {

    "1st_aim": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        13,
                        2,
                        -8
                    ]
                },
                "rotation": {
                    "0.0": [
                        107.53742,
                        4.92385,
                        -179.12962
                    ]
                }
            },
            "sraw": {
                "position": {},
                "rotation": {
                    "0.0": [
                        -15,
                        0,
                        0
                    ]
                }
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -8.77371,
                        1.13633,
                        -7.6302
                    ]
                },
                "rotation": {
                    "0.0": [
                        120.60877,
                        -5.77636,
                        -173.56335
                    ]
                }
            }
        },
        "length": 0.0
    },
    "1st_equip": {
        "bones": {
            "leftArm": {
                "position": {
                    "0.0": [
                        -8.97961,
                        -0.29206,
                        3.03978
                    ],
                    "0.5833": [
                        -8.77371,
                        1.13633,
                        2.3698
                    ]
                },
                "rotation": {
                    "0.0": [
                        162.9122,
                        -0.90268,
                        -171.37855
                    ],
                    "0.5833": [
                        125.40137,
                        0.33207,
                        -169.20468
                    ]
                }
            },
            "rightArm": {
                "position": {
                    "0.0": [
                        12,
                        0,
                        2
                    ],
                    "0.5833": [
                        12,
                        0,
                        2
                    ]
                },
                "rotation": {
                    "0.0": [
                        142.53742,
                        4.92385,
                        -179.12962
                    ],
                    "0.5833": [
                        107.53742,
                        4.92385,
                        -179.12962
                    ]
                }
            }
        },
        "length": 0.5833
    },
    "1st_idle": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        12,
                        0,
                        2
                    ]
                },
                "rotation": {
                    "0.0": [
                        107.53742,
                        4.92385,
                        -179.12962
                    ]
                }
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -8.77371,
                        1.13633,
                        2.3698
                    ]
                },
                "rotation": {
                    "0.0": [
                        125.40137,
                        0.33207,
                        -169.20468
                    ]
                }
            }
        },
        "length": 0.0
    },
    "1st_run": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        12,
                        0,
                        2
                    ],
                    "0.5": [
                        12,
                        0,
                        2
                    ],
                    "0.25": [
                        12,
                        0,
                        2
                    ]
                },
                "rotation": {
                    "0.0": [
                        127.52557,
                        23.70421,
                        -174.80172
                    ],
                    "0.5": [
                        127.52557,
                        23.70421,
                        -174.80172
                    ],
                    "0.25": [
                        136.51481,
                        27.63099,
                        -171.36639
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
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -8.51304,
                        0.36197,
                        -2.2018
                    ],
                    "0.5": [
                        -8.51304,
                        0.36197,
                        -2.2018
                    ],
                    "0.25": [
                        -9.21935,
                        0.1106,
                        -2.86357
                    ]
                },
                "rotation": {
                    "0.0": [
                        147.90137,
                        0.33207,
                        -169.20468
                    ],
                    "0.5": [
                        147.90137,
                        0.33207,
                        -169.20468
                    ],
                    "0.25": [
                        147.11818,
                        12.218,
                        -173.83722
                    ]
                }
            }
        },
        "length": 0.5
    },
    "3rd_idle": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        -1,
                        0,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        -57.5,
                        0,
                        0
                    ]
                }
            },
            "sraw": {
                "position": {},
                "rotation": {}
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -0.30071,
                        -0.61304,
                        -0.73059
                    ]
                },
                "rotation": {
                    "0.0": [
                        -48.65802,
                        13.31791,
                        11.45696
                    ]
                }
            }
        },
        "length": 0.0
    },

    "3rd_run": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        0,
                        -2,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        -59.61874,
                        -8.64917,
                        -5.03837
                    ]
                }
            },
            "sraw": {
                "position": {},
                "rotation": {}
            },
            "leftArm": {
                "position": {},
                "rotation": {
                    "0.0": [
                        -32.5,
                        0,
                        0
                    ]
                }
            }
        },
        "length": 0.0
    },
    "3rd_aim": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        -1,
                        0,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        -90,
                        0,
                        0
                    ]
                }
            },
            "sraw": {
                "position": {},
                "rotation": {}
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -0.24056,
                        -0.19747,
                        -0.73698
                    ]
                },
                "rotation": {
                    "0.0": [
                        -74.30716,
                        16.88547,
                        4.6653
                    ]
                }
            }
        },
        "length": 0.0
    },
    "3rd_equip": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        0,
                        0,
                        0
                    ],
                    "0.5833": [
                        -1,
                        0,
                        0
                    ]
                },
                "rotation": {
                    "0.0": [
                        0,
                        0,
                        0
                    ],
                    "0.5833": [
                        -57.5,
                        0,
                        0
                    ]
                }
            },
            "sraw": {
                "position": {},
                "rotation": {}
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        0,
                        0,
                        0
                    ],
                    "0.5833": [
                        -0.30071,
                        -0.61304,
                        -0.73059
                    ]
                },
                "rotation": {
                    "0.0": [
                        0,
                        0,
                        0
                    ],
                    "0.5833": [
                        -48.65802,
                        13.31791,
                        11.45696
                    ]
                }
            }
        },
        "length": 0.5833
    }
}
