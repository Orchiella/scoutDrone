ModName = __file__.rsplit('/' if '/' in __file__ else '.', 2)[-2]
modName = ModName[0].lower() + ModName[1:]
mod_name = ''.join(['_' + c.lower() if c.isupper() and i != 0 else c.lower() for i, c in enumerate(ModName)])
mn = mod_name.split('_')[0][0] + mod_name.split('_')[1][0]


def CreateEventData(funcName, args, kwargs):
    data = {'funcName': funcName}
    if args: data['args'] = args
    if kwargs: data['kwargs'] = kwargs
    return data
