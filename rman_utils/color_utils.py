import math

def linearizeSRGB(col):
    ret = []
    for i in range(0, len(col)):
        if col[i] < 0.04045:
            ret.append(col[i] * 0.07739938)
        else:
            ret.append(math.pow((col[i] + 0.055) * 0.947867299, 2.4))
    return ret