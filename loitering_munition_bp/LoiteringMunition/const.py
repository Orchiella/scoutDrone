STATES = {"transition", "re_transition", "idle", "run", "aim", "equip", "inspect"}
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

LIQUID_TYPE = set("minecraft:" + block for block in {"flowing_water", "water", "flowing_lava", "lava"})
TRANSITION_DURATION = 0.25
ANIM_CACHE = {
    "1st_aim": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        13,
                        -1,
                        -8
                    ]
                },
                "rotation": {
                    "0.0": [
                        90,
                        0,
                        -180
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
    "1st_inspect": {
        "bones": {
            "leftArm": {
                "position": {
                    "2.625": [
                        -12.5866,
                        -15.69106,
                        -1.88195
                    ],
                    "0.0": [
                        -10.73026,
                        -6.20303,
                        8.25787
                    ],
                    "2.0833": [
                        -12.5866,
                        -15.69106,
                        -1.88195
                    ],
                    "3.0": [
                        -10.73026,
                        -6.20303,
                        8.25787
                    ],
                    "1.3333": [
                        -10.08224,
                        -5.30119,
                        0.72164
                    ],
                    "3.5": [
                        -10.73026,
                        -6.20303,
                        8.25787
                    ],
                    "0.5417": [
                        -10.08224,
                        -5.30119,
                        0.72164
                    ]
                },
                "rotation": {
                    "2.625": [
                        103.69132,
                        0.16035,
                        -166.40897
                    ],
                    "0.0": [
                        100.57169,
                        -29.83633,
                        -169.60164
                    ],
                    "2.0833": [
                        103.69132,
                        0.16035,
                        -166.40897
                    ],
                    "3.0": [
                        100.57169,
                        -29.83633,
                        -169.60164
                    ],
                    "1.3333": [
                        103.69132,
                        0.16035,
                        -166.40897
                    ],
                    "3.5": [
                        100.57169,
                        -29.83633,
                        -169.60164
                    ],
                    "0.5417": [
                        103.69132,
                        0.16035,
                        -166.40897
                    ]
                }
            },
            "rightArm": {
                "position": {
                    "2.625": [
                        13.26874,
                        -6.71847,
                        5.98424
                    ],
                    "0.0": [
                        15,
                        -7,
                        6
                    ],
                    "3.0": [
                        15,
                        -7,
                        6
                    ],
                    "1.3333": [
                        14.62872,
                        -5,
                        11.33703
                    ],
                    "2.0833": [
                        13.29939,
                        -6.85652,
                        5.98348
                    ],
                    "0.5417": [
                        14.62872,
                        -5.1,
                        11.33703
                    ],
                    "3.5": [
                        15,
                        -7,
                        6
                    ]
                },
                "rotation": {
                    "2.625": [
                        90.23077,
                        0.20237,
                        -235.01836
                    ],
                    "0.0": [
                        90,
                        0,
                        -180
                    ],
                    "3.0": [
                        90,
                        0,
                        -177.5
                    ],
                    "1.3333": [
                        90,
                        47.5,
                        -180
                    ],
                    "2.0833": [
                        90.22172,
                        0.21225,
                        -237.51836
                    ],
                    "0.5417": [
                        90,
                        50,
                        -180
                    ],
                    "3.5": [
                        90,
                        0,
                        -180
                    ]
                }
            }
        },
        "length": 3.5
    },
    "1st_equip": {
        "bones": {
            "leftArm": {
                "position": {
                    "0.0": [
                        -9.81188,
                        -5.96655,
                        4.80258
                    ],
                    "0.5833": [
                        -10.73026,
                        -6.20303,
                        8.25787
                    ]
                },
                "rotation": {
                    "0.0": [
                        162.9122,
                        -0.90268,
                        -171.37855
                    ],
                    "0.5833": [
                        100.57169,
                        -29.83633,
                        -169.60164
                    ]
                }
            },
            "rightArm": {
                "position": {
                    "0.0": [
                        15,
                        -13,
                        6
                    ],
                    "0.5833": [
                        15,
                        -7,
                        6
                    ]
                },
                "rotation": {
                    "0.0": [
                        147.5,
                        0,
                        -180
                    ],
                    "0.5833": [
                        90,
                        0,
                        -180
                    ]
                }
            }
        },
        "length": 0.5833
    },
    "1st_run": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        15.08138,
                        -7.85835,
                        5.74189
                    ],
                    "0.4167": [
                        15.08138,
                        -7.85835,
                        5.74189
                    ],
                    "0.8333": [
                        15.08138,
                        -7.85835,
                        5.74189
                    ]
                },
                "rotation": {
                    "0.0": [
                        105.08017,
                        19.607,
                        -187.5937
                    ],
                    "0.4167": [
                        100.08017,
                        19.607,
                        -187.5937
                    ],
                    "0.8333": [
                        105.08017,
                        19.607,
                        -187.5937
                    ]
                }
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -11.81777,
                        -9.70677,
                        3.4756
                    ],
                    "0.4167": [
                        -12.0285,
                        -10.09413,
                        3.23993
                    ],
                    "0.8333": [
                        -11.81777,
                        -9.70677,
                        3.4756
                    ]
                },
                "rotation": {
                    "0.0": [
                        122.19807,
                        -34.10593,
                        -172.67056
                    ],
                    "0.4167": [
                        114.69807,
                        -34.10593,
                        -172.67056
                    ],
                    "0.8333": [
                        122.19807,
                        -34.10593,
                        -172.67056
                    ]
                }
            }
        },
        "length": 0.8333
    },
    "1st_idle": {
        "bones": {
            "rightArm": {
                "position": {
                    "0.0": [
                        15,
                        -7,
                        6
                    ]
                },
                "rotation": {
                    "0.0": [
                        90,
                        0,
                        -180
                    ]
                }
            },
            "leftArm": {
                "position": {
                    "0.0": [
                        -10.73026,
                        -6.20303,
                        8.25787
                    ]
                },
                "rotation": {
                    "0.0": [
                        100.57169,
                        -29.83633,
                        -169.60164
                    ]
                }
            }
        },
        "length": 0.0
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
            "loitering_munition_launcher": {
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
            "loitering_munition_launcher": {
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
            "loitering_munition_launcher": {
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
            "loitering_munition_launcher": {
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
    },
    "3rd_inspect": {
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
            "loitering_munition_launcher": {
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
    }
}
