import rman

def convert_matrix(m):
    v = [m[0][0], m[1][0], m[2][0], m[3][0],
        m[0][1], m[1][1], m[2][1], m[3][1],
        m[0][2], m[1][2], m[2][2], m[3][2],
        m[0][3], m[1][3], m[2][3], m[3][3]]

    return v    

def convert_matrix4x4(m):
    mtx = convert_matrix( m )
    rman_mtx = rman.Types.RtMatrix4x4( mtx[0],mtx[1],mtx[2],mtx[3],
                                mtx[4],mtx[5],mtx[6],mtx[7],
                                mtx[8],mtx[9],mtx[10],mtx[11],
                                mtx[12],mtx[13],mtx[14],mtx[15])

    return rman_mtx

def convert_ob_bounds(ob_bb):
    return (ob_bb[0][0], ob_bb[7][0], ob_bb[0][1],
            ob_bb[7][1], ob_bb[0][2], ob_bb[1][2])    

def transform_points(transform_mtx, P):
    transform_pts = []
    mtx = convert_matrix( transform_mtx )
    m = rman.Types.RtMatrix4x4( mtx[0],mtx[1],mtx[2],mtx[3],
                                mtx[4],mtx[5],mtx[6],mtx[7],
                                mtx[8],mtx[9],mtx[10],mtx[11],
                                mtx[12],mtx[13],mtx[14],mtx[15])
    for i in range(0, len(P), 3):
        pt = m.pTransform( rman.Types.RtFloat3(P[i], P[i+1], P[i+2]) )
        transform_pts.append(pt.x)
        transform_pts.append(pt.y)
        transform_pts.append(pt.z)

    return transform_pts 