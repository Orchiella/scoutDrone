from math import sqrt

import mod.server.extraServerApi as serverApi

CF = serverApi.GetEngineCompFactory()


def GetEntityBodyLocation(entityId):
    footPos = CF.CreatePos(entityId).GetFootPos()
    if not footPos:
        return None
    bodyHeight = CF.CreateCollisionBox(entityId).GetSize()[1] * 0.8
    return footPos[0], footPos[1] + bodyHeight, footPos[2]


def GetDistance(pos1, pos2):
    return sqrt(pow(pos1[0] - pos2[0], 2) + pow(pos1[1] - pos2[1], 2) + pow(pos1[2] - pos2[2], 2))
