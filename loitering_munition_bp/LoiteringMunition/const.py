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
            "loitering_munition_launcher": {
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
            "loitering_munition_launcher": {
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
    "1st_inspect": {
        "bones": {
            "leftArm": {
                "position": {
                    "0.0": [
                        -8.77371,
                        1.13633,
                        2.3698
                    ],
                    "4.9583": [
                        -12.81632,
                        -7.4715,
                        11.14416
                    ],
                    "3.8333": [
                        -8.29,
                        -11.07,
                        7.99
                    ],
                    "6.0": [
                        -8.77371,
                        1.13633,
                        2.3698
                    ],
                    "4.75": [
                        -12.81632,
                        -7.4715,
                        11.14416
                    ],
                    "5.5833": [
                        -10.9,
                        -3.39,
                        6.51
                    ],
                    "5.2083": [
                        -12.81632,
                        -7.4715,
                        11.14416
                    ],
                    "3.5833": [
                        -4.89254,
                        -13.76529,
                        5.62242
                    ],
                    "4.375": [
                        -12.81632,
                        -7.4715,
                        11.14416
                    ],
                    "4.5417": [
                        -12.81632,
                        -7.4715,
                        11.14416
                    ],
                    "2.5": [
                        -4.89254,
                        -13.76529,
                        5.62242
                    ],
                    "5.75": [
                        -10.04976,
                        -3.56916,
                        4.24201
                    ],
                    "0.625": [
                        -8.12512,
                        2.34845,
                        -0.47413
                    ],
                    "4.1667": [
                        -12.81632,
                        -7.4715,
                        11.14416
                    ],
                    "1.75": [
                        -8.12512,
                        2.34845,
                        -0.47413
                    ]
                },
                "rotation": {
                    "0.0": [
                        125.40137,
                        0.33207,
                        -169.20468
                    ],
                    "4.9583": [
                        29.34313,
                        -48.83088,
                        -189.95586
                    ],
                    "3.8333": [
                        47.58067,
                        9.30961,
                        -224.69463
                    ],
                    "6.0": [
                        125.40137,
                        0.33207,
                        -169.20468
                    ],
                    "4.75": [
                        41.84313,
                        -48.83088,
                        -189.95586
                    ],
                    "5.5833": [
                        76.349,
                        1.12896,
                        -187.06699
                    ],
                    "5.2083": [
                        29.34313,
                        -48.83088,
                        -189.95586
                    ],
                    "3.5833": [
                        69.56883,
                        15.94213,
                        -219.84413
                    ],
                    "4.375": [
                        44.34313,
                        -48.83088,
                        -189.95586
                    ],
                    "4.5417": [
                        29.34313,
                        -48.83088,
                        -189.95586
                    ],
                    "2.5": [
                        69.56883,
                        15.94213,
                        -219.84413
                    ],
                    "0.625": [
                        133.35069,
                        8.4675,
                        -163.36743
                    ],
                    "4.1667": [
                        29.34313,
                        -48.83088,
                        -189.95586
                    ],
                    "1.75": [
                        133.35069,
                        8.4675,
                        -163.36743
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
                    "1.75": [
                        13.30154,
                        -3.05832,
                        8.88172
                    ],
                    "3.5833": [
                        13.56497,
                        -2.19212,
                        8.93513
                    ],
                    "6.0": [
                        12,
                        0,
                        2
                    ],
                    "0.625": [
                        12.9976,
                        -2.90152,
                        8.51699
                    ],
                    "5.2083": [
                        13.56497,
                        -2.19212,
                        8.93513
                    ],
                    "4.1667": [
                        13.56497,
                        -2.19212,
                        7.93513
                    ],
                    "2.5": [
                        13.56497,
                        -2.19212,
                        8.93513
                    ]
                },
                "rotation": {
                    "0.0": [
                        107.53742,
                        4.92385,
                        -179.12962
                    ],
                    "1.75": [
                        121.93126,
                        46.84176,
                        -152.71147
                    ],
                    "3.5833": [
                        61.45118,
                        25.93232,
                        -228.93009
                    ],
                    "6.0": [
                        107.53742,
                        4.92385,
                        -179.12962
                    ],
                    "0.625": [
                        124.11454,
                        45.47893,
                        -149.68508
                    ],
                    "5.2083": [
                        67.51234,
                        -12.29105,
                        -240.3614
                    ],
                    "4.1667": [
                        67.0302,
                        -11.32499,
                        -238.00571
                    ],
                    "2.5": [
                        60.41692,
                        24.71758,
                        -231.34756
                    ]
                }
            }
        },
        "length": 6
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
