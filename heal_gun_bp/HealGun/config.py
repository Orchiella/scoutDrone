ModName = __file__.rsplit('/' if '/' in __file__ else '.', 2)[-2]


def CreateEventData(funcName, args, kwargs):
    data = {'funcName': funcName}
    if args: data['args'] = args
    if kwargs: data['kwargs'] = kwargs
    return data
