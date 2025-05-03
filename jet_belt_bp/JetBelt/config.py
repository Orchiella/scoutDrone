ModName = __file__.rsplit('/' if '/' in __file__ else '.', 2)[-2]
modName = ModName[0].lower() + ModName[1:]
mod_name = ''.join(['_' + c.lower() if c.isupper() and i != 0 else c.lower() for i, c in enumerate(ModName)])


def CreateEventData(funcName, args, kwargs):
    data = {'funcName': funcName}
    if args: data['args'] = args
    if kwargs: data['kwargs'] = kwargs
    return data
