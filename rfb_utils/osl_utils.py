import bpy
import re
import os

def get_osl_line_meta(line):
    if "%%meta" not in line:
        return {}
    meta = {}
    for m in re.finditer('meta{', line):
        sub_str = line[m.start(), line.find('}', beg=m.start())]
        item_type, item_name, item_value = sub_str.split(',', 2)
        val = item_value
        if item_type == 'string':
            val = val[1:-1]
        elif item_type == 'int':
            val = int(val)
        elif item_type == 'float':
            val = float(val)

        meta[item_name] = val
    return meta

def readOSO(filePath):
    line_number = 0
    shader_meta = {}
    prop_names = []
    shader_meta["shader"] = os.path.splitext(os.path.basename(filePath))[0]
    with open(filePath, encoding='utf-8') as osofile:
        for line in osofile:
            # if line.startswith("surface") or line.startswith("shader"):
            #    line_number += 1
            #    listLine = line.split()
            #    shader_meta["shader"] = listLine[1]
            if line.startswith("param"):
                line_number += 1
                listLine = line.split()
                name = listLine[2]
                type = listLine[1]
                if type == "point" or type == "vector" or type == "normal" or \
                        type == "color":
                    defaultString = []
                    defaultString.append(listLine[3])
                    defaultString.append(listLine[4])
                    defaultString.append(listLine[5])
                    default = []
                    for element in defaultString:
                        default.append(float(element))
                elif type == "matrix":
                    default = []
                    x = 3
                    while x <= 18:
                        default.append(float(listLine[x]))
                        x += 1
                elif type == "closure":
                    debug('error', "Closure types are not supported")
                    #type = "void"
                    #name = listLine[3]
                else:
                    default = listLine[3]

                prop_names.append(name)
                prop_meta = {"type": type, "default":  default, "IO": "in"}
                for tup in listLine:
                    if tup == '%meta{int,lockgeom,0}':
                        prop_meta['lockgeom'] = 0
                        break
                prop_meta.update(get_osl_line_meta(line))
                shader_meta[name] = prop_meta
            elif line.startswith("oparam"):
                line_number += 1
                listLine = line.split()
                name = listLine[2]
                type = listLine[1]
                if type == "point" or type == "vector" or type == "normal" or \
                        type == "color":
                    default = []
                    default.append(listLine[3])
                    default.append(listLine[4])
                    default.append(listLine[5])
                elif type == "matrix":
                    default = []
                    x = 3
                    while x <= 18:
                        default.append(listLine[x])
                        x += 1
                elif type == "closure":
                    debug('error', "Closure types are not supported")
                    type = "void"
                    name = listLine[3]
                else:
                    default = listLine[3]
                prop_names.append(name)
                prop_meta = {"type": type, "default":  default, "IO": "out"}
                prop_meta.update(get_osl_line_meta(line))
                shader_meta[name] = prop_meta
            else:
                line_number += 1
    return prop_names, shader_meta