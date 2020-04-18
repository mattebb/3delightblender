import bpy
from ...rman_utils import transform_utils
from mathutils import Vector, Matrix
import math
import copy

CORNERS = [Vector((-0.5, 0.5, 0.0)), Vector((0.5, 0.5, 0.0)),
           Vector((0.5, -0.5, 0.0)), Vector((-0.5, -0.5, 0.0))]


def bilinear(vec, p00, p10, p01, p11):
    """vec is normalized but centered, i.e. we have a [-0.5, 0.5] range."""
    a = p00 * (0.5 - vec.x) + p10 * (vec.x + 0.5)
    b = p01 * (0.5 - vec.x) + p11 * (vec.x + 0.5)
    return a * (0.5 - vec.y) + b * (vec.y + 0.5)


def _gl_lines(idx_buffer, start_vtx, num_vtx, start_idx, loop=False):
    """Fills the index buffer to draw a number of lines.

    Args:
    - idx_buffer (MIndexBuffer): A pre-initialized index buffer to fill. May already contain valid data.
    - start_vtx (int): index of the primitive's first vertex in the vertex buffer.
    - num_vtx (int): number of vertices in the primitive
    - start_idx (p1_type): position of our first write in the index buffer.

    Kwargs:
    - loop:  add a line from the last vertex to the first one if True.
    """
    # print ('      _gl_lines(%s, start_vtx=%d, num_vtx=%d, start_idx=%d, loop=%s)'
    #        % (idx_buffer, start_vtx, num_vtx, start_idx, loop))
    num_indices = num_vtx * 2
    if not loop:
        num_indices -= 2
    vtx_idx = start_vtx
    last_idx = start_idx + num_indices - 2
    for i in range(start_idx, start_idx + num_indices, 2):
        idx_buffer[i] = vtx_idx
        if i == last_idx and loop:
            idx_buffer[i + 1] = start_vtx
        else:
            idx_buffer[i + 1] = vtx_idx + 1
        vtx_idx += 1        

def get_parented_lights(light_filter):
    parents = []

    for ob in [x for x in bpy.data.objects if x.type == 'LIGHT']:
        if not ob.data.renderman:
            continue
        rm = ob.data.renderman
        if rm.renderman_type == 'FILTER':
            continue
        for lf in rm.light_filters:
            if lf.filter_name == light_filter.name:
                parents.append(ob)
                break
    return parents        

class BarnLightFilterDrawHelper(object):

    static_shp = {}
    nshapes = 4
    nedges = 4

    def __init__(self):

        self.subdivs = 32
        self._shapekey = '%d' % self.subdivs
        self.axis = 2
        self.edge_mode = False
        self.xy = [(1, 2), (0, 2), (0, 1)]

        self.barnMode = 0
        self.mode = 0
        self.directional = 0
        self.shearX = 0.0
        self.shearY = 0.0
        self.apex = 25.0
        self.useLightDirection = 0
        self.width = 1.0
        self.height = 1.0
        self.radius = 1.0
        self.edge = 0.0
        self.scaleWidth = 1.0
        self.scaleHeight = 1.0
        self.left = 0.0
        self.right = 0.0
        self.bottom = 0.0
        self.top = 0.0
        self.leftEdge = 0.0
        self.rightEdge = 0.0
        self.bottomEdge = 0.0
        self.topEdge = 0.0
        self.invert = 0
        self.depth = 10.0

    def update_input_params(self, obj):   

        self.parents = get_parented_lights(obj)
        self.num_lights = len(self.parents)

        light = obj.data
        rm = light.renderman.get_light_node() 
        self.barnMode = int(getattr(rm, "barnMode", 0))
        self.mode = self.barnMode
        self.directional = getattr(rm, "directional", 0)
        self.shearX = getattr(rm, "shearX", 0.0)
        self.shearY = getattr(rm, "shearY", 0.0)
        self.apex = getattr(rm, "apex", 25.0)
        self.useLightDirection = getattr(rm, "useLightDirection", 0)
        self.width = getattr(rm, "width", 1.0)
        self.height = getattr(rm, "height", 1.0)
        self.radius = getattr(rm, "radius", 1.0)
        self.edge = getattr(rm, "edge", 0.0)
        self.scaleWidth = getattr(rm, "scaleWidth", 1.0)
        self.scaleHeight = getattr(rm, "scaleHeight", 1.0)
        self.left = getattr(rm, "left", 0.0)
        self.right = getattr(rm, "right", 0.0)
        self.bottom = getattr(rm, "bottom", 0.0)
        self.top = getattr(rm, "top", 0.0)
        self.leftEdge = getattr(rm, "leftEdge", 0.0)
        self.rightEdge = getattr(rm, "rightEdge", 0.0)
        self.bottomEdge = getattr(rm, "bottomEdge", 0.0)
        self.topEdge = getattr(rm, "topEdge", 0.0)
        self.invert = getattr(rm, "invert", 0)    

        self.set_connected_lights_data(obj)    

    @property
    def shape(self):
        shp = []
        try:
            shp = self.static_shp[self._shapekey][self.axis]
        except KeyError:
            self.static_shp[self._shapekey] = [[], [], []]
            self._build_static_shape()
        except IndexError:
            self._build_static_shape()
        else:
            if shp == []:
                self._build_static_shape()
        return self.static_shp[self._shapekey][self.axis]

    def _build_static_shape(self):
        """Build a static buffer we can manipulate later.

        The rounded rect is build as a sphere with repeated vertices at 0, 90,
        180 and 270 degrees. static_shp being a static member, it will be
        inherited by all instances using the same number of subdivisions.
        32 is a good tradeoff and the recommended value.
        """

        # print '+ self.subdivs: %d' % self.subdivs
        radius = 1.0
        arc_len = self.subdivs / 4
        theta_step = (2.0 * math.pi) / float(self.subdivs)
        # print '  |_ full rev = %f' % round(2.0 * math.pi, 4)
        # print '  |_ theta_step = %f' % theta_step

        # get indices to draw on the requested axis
        idx1, idx2 = self.xy[self.axis]

        # draw a circle and insert an additional vertex at 0, 90, 180 and
        # 270 degrees.
        #
        vtxs = []
        theta = 0.0
        for i in range(self.subdivs):
            theta = float(i) * theta_step
            p = [0.0, 0.0, 0.0]
            p[idx1] = radius * math.cos(theta)
            p[idx2] = radius * math.sin(theta)
            vtxs.append(p)
            # print '  |_ #%d %s   (%.04f)' % (len(vtxs) - 1, p, theta)
            if i > 0 and i % arc_len == 0:
                # NOTE: use list(p) to pass a copy of p instead of a reference
                # to p. Previously, edits to p would change the other array
                # entry too causing really hard to debug redraw issues.
                vtxs.append(list(p))
                # print '  |_ #%d %s   COPY' % (len(vtxs) - 1, p)
        # repeat: append a copy 1st vertex for the last edge.
        vtxs.append(list(vtxs[0]))
        # append a ref to the first vertex to loop when using 'lines' index
        # buffers.
        # NOTE: this is a reference to the first vertex which means that modifying
        # the 1st vertex modifies the last vertex too (and vice versa).
        vtxs.append(vtxs[0])
        # print '  |_ #%d %s  REF' % (len(vtxs) - 1, p)

        # if len(vtxs) != self.subdivs + 4 + 1:
        #     print '  |_ UNEXPECTED ISSUE -> %d : should be %d' % (len(vtxs), self.subdivs + 4 + 1)

        # update static variable
        self.static_shp[self._shapekey][self.axis] = vtxs

    def base_vtx_buffer_count(self):
        return len(self.shape)

    def vtx_buffer_count(self):
        """Return the number of vertices in this buffer."""
        # return self.subdivs + 4 doubled vtxs + 1 closing vtx

        nv = self.base_vtx_buffer_count() * 2  # near/soft near
        nv += nv * self.num_lights                      # n time far/soft far
        # print '>> vtx_buffer_count %s = %s (%s lights)' % (self, nv, self.num_lights)
        return nv        
        
    def base_vtx_buffer(self):
        """Return a list of vertices (list) in local space.

        We process each corner one by one, applying the following
        transformations:
        1. Apply the radius, which scales the corner toward the rect's
        center.
        2. Apply the edge offset, enlarging the shape.
        3. Apply the global scale controls
        """
        grp = int(self.subdivs / 4)
        # NOTE: check deepcopy really faster than repeated insertion ?
        vtxs = copy.deepcopy(self.shape)

        # print 'RoundedRect.vtx_buffer'
        # print '   + width = %r' % self.width
        # print '   + height = %r' % self.height
        # print '   + vtxs'
        # for i, v in enumerate(vtxs):
        #     print '     |_  #%d  [%.03f, %.03f, %.03f]' % (i, v[0], v[1], v[2])

        x, y = self.xy[self.axis]

        l_pos = self.width + self.left
        r_pos = self.width + self.right
        t_pos = self.height + self.top
        b_pos = self.height + self.bottom

        if self.edge_mode:
            l_edge = self.edge * self.leftEdge
            r_edge = self.edge * self.rightEdge
            t_edge = self.edge * self.topEdge
            b_edge = self.edge * self.bottomEdge
        else:
            l_edge = 0.0
            r_edge = 0.0
            t_edge = 0.0
            b_edge = 0.0

        # top right arc
        sidx = 0
        eidx = sidx + grp + 1
        # print '   |__ top right'
        # i = sidx
        for vtx in vtxs[sidx:eidx]:
            # print '       |__ #%d' % i
            vtx[x] = (vtx[x] * (self.radius + r_edge) + r_pos) * self.scaleWidth
            vtx[y] = (vtx[y] * (self.radius + t_edge) + t_pos) * self.scaleHeight
            # i += 1
            # print '   |__ %s' % vtx

        # top left arc
        sidx = eidx
        eidx = sidx + grp + 1
        # print '   |__ top left'
        # i = sidx
        for vtx in vtxs[sidx:eidx]:
            # print '       |__ #%d' % i
            vtx[x] = (vtx[x] * (self.radius + l_edge) - l_pos) * self.scaleWidth
            vtx[y] = (vtx[y] * (self.radius + t_edge) + t_pos) * self.scaleHeight
            # i += 1
            # print '   |__ %s' % vtx

        # bottom left arc
        sidx = eidx
        eidx = sidx + grp + 1
        # print '   |__ %d -> %d' % (sidx, eidx)
        # i = sidx
        for vtx in vtxs[sidx:eidx]:
            # print '       |__ #%d' % i
            vtx[x] = (vtx[x] * (self.radius + l_edge) - l_pos) * self.scaleWidth
            vtx[y] = (vtx[y] * (self.radius + b_edge) - b_pos) * self.scaleHeight
            # i += 1
            # print '   |__ %s' % vtx

        # bottom right arc
        sidx = eidx
        eidx = sidx + grp + 1   # do not transform the very last vertex
        # print '   |__ %d -> %d' % (sidx, eidx)
        # i = sidx
        for vtx in vtxs[sidx:eidx]:
            # print '       |__ #%d' % i
            vtx[x] = (vtx[x] * (self.radius + r_edge) + r_pos) * self.scaleWidth
            vtx[y] = (vtx[y] * (self.radius + b_edge) - b_pos) * self.scaleHeight
            # i += 1
            # print '   |__ %s' % vtx

        # print '   + mod vtxs'
        # for i, v in enumerate(vtxs):
        #     print '     |_  #%d  [%.03f, %.03f, %.03f]' % (i, v[0], v[1], v[2])

        return vtxs        

    def set_connected_lights_data(self, this_obj):
        """Get data from connected lights to be able to draw the frustum.

        - For each connected light
          - compute its matrix in filter-space
          - compute the position of the light's corners in filter-space and store
            them for later use.

        Args:
        - this_obj (bpy.type.Light): The light filter object
        """

        self.light_corners = []
        self.light_positions = []
        self.light_names = []

        # z-up to y-up
        m = Matrix.Identity(4)
        m[1][1] = 0.0
        m[1][2] = -1.0
        m[2][1] = 1.0
        m[2][2] = 0.0 

        world_to_filter_matrix = this_obj.matrix_world @ m
        for light_obj in self.parents:
            corners = []
            # print('      |__ %s' % light_obj.name)

            # get the light ws matrix
            lgt_to_world_matrix = light_obj.matrix_world
            # print('      |__ matrix = %s' % lgt_to_world_matrix)
            lgt_to_fltr_matrix = lgt_to_world_matrix.inverted_safe() @ world_to_filter_matrix @ m         
 
            # get the light position in filter space
            trans, rotation, scale = lgt_to_world_matrix.decompose()
            lgt_pos = trans
            lgt_pos = world_to_filter_matrix @ lgt_pos

            # print('      |__ Clgt: %s' % lgt_pos)

            # get the light corners in filter space
            for corner in CORNERS:
                pl = Vector((corner[0], corner[1], corner[2]))
                pl = lgt_to_fltr_matrix @ pl
                corners.append(pl)
                # print('      |__ Plgt: %s' % pl)

            self.light_corners.append(corners)
            self.light_positions.append(lgt_pos)
            self.light_names.append(light_obj.name)

    def ordered_proj_vectors(self, light_idx):
        """Generator to get the vectors from one corner of a light filter to
        another corner of the light.
        """
        w = self.width + self.radius
        h = self.height + self.radius

        f_vtxs = [ Vector((-0.5 * w, 0.5 * h, 0.0)),
                Vector((0.5 * w, 0.5 * h, 0.0)),
                Vector((0.5 * w, -0.5 * h, 0.0)),
                Vector((-0.5 * w, -0.5 * h, 0.0))
                ]

        # in 'physical' mode, the vectors are built from one filter corner to
        # the opposite light corner. This gives us a perspective projections.
        order = [(0, 2), (1, 3), (2, 0), (3, 1)]
        if self.mode == 1:
            # in 'analytic' mode, vector are built from one filter corner to the
            # same light corner. This gives us an orthographic projection.
            order = [(0, 0), (1, 1), (2, 2), (3, 3)]

        for pf, pl in order:
            p_fltr = f_vtxs[pf]
            p_lgt = self.light_corners[light_idx][pl]
            if self.mode == 1:

                if not self.useLightDirection:
                    p_lgt = Vector(p_fltr) #om.MPoint(p_fltr)
                    if self.directional:
                        # project orthogonaly to the filter
                        p_lgt.z += -1.0
                    else:
                        # project from the center of the filter offset in Z.
                        p_lgt.x = 0.0
                        p_lgt.y = 0.0
                        p_lgt.z += -self.apex
                else:
                    # use light direction
                    if self.directional:
                        # translate the filter corner to the light position

                        p_lgt = Vector( (
                             self.light_positions[light_idx][0] + p_fltr.x,       
                             self.light_positions[light_idx][1] + p_fltr.y,
                             self.light_positions[light_idx][2] + p_fltr.z
                        ))

                    else:
                        # project the filter center towards the light center at
                        # distance apex.

                        vec_to_lgt = Vector(self.light_positions[light_idx]).normalized() * self.apex
                        p_lgt = Vector(vec_to_lgt)

                # compute the vector and normalize it.
                v = Vector(p_lgt - p_fltr).normalized()

                # add the shearing and re-normalize
                v = Vector((v.x - self.shearX, v.y - self.shearY, v.z )).normalized()
            else:
                p_lgt = self.light_corners[light_idx][pl]
                v = p_lgt - p_fltr
                v.normalize()
            # print ('    |__ %s - %s = %s  len = %f (%s, %s)' %
            #        (str(p_lgt), str(p_fltr), str(v), v.length, pf, pl))
            yield p_fltr, v        

    def vtx_buffer(self):
        """Return a list of vertices (list) in local space.

        Use the vtx_list (the original light shape) to build the outer coneAngle
        at the specified depth.
        """
        # print '>> vtx_buffer %s' % self

        self.base_shape = self.base_vtx_buffer()

        # we need to halve the size of the rounded rect to match the renderer.
        base_scale = 0.5
        for vtx in self.base_shape[:-1]:
            vtx[0] *= base_scale
            vtx[1] *= base_scale
            vtx[2] *= base_scale

        vertices = []

        # near shape
        for vtx in self.base_shape:
            vertices.append(vtx)

        # near softness
        # print '   |__ near softness'
        soft_scale = 1.0 + self.edge
        for vtx in self.base_shape:
            vertices.append([vtx[0] * soft_scale,
                             vtx[1] * soft_scale,
                             vtx[2]])

        # iterate through lights
        nlights = self.num_lights
        for i in range(nlights):

            # compute the corners of the projection at a given depth.
            npos = []
            for vtx, vec in self.ordered_proj_vectors(i):
                p = vtx + vec * (-max(0.0, self.depth) / max(abs(vec.z), 0.001))
                npos.append(p)

            # far shape
            # print '   |__ far angle'
            for vtx in self.base_shape:
                nv = bilinear(Vector(vtx),
                              Vector(npos[3]), Vector(npos[2]),
                              Vector(npos[0]), Vector(npos[1]))
                vertices.append(nv)

            # far softness
            # print '   |__ far softness'
            for vtx in self.base_shape:
                nv = bilinear(Vector((vtx[0] * soft_scale,
                                      vtx[1] * soft_scale,
                                      vtx[2])),
                              Vector(npos[3]), Vector(npos[2]),
                              Vector(npos[0]), Vector(npos[1]))
                vertices.append(nv)

        return vertices        

    def idx_buffer(self, num_vtx, start_idx, inst_idx):
        """
        Fill the provided index buffer to draw the shape.

        Args:
        - idx_buffer (omr.MIndexBuffer): un-allocated storage for our result.
        - num_vtx (int): The total number of vertices in the VBO.
        - startIdx (int): the index of our first vtx in the VBO
        - item_idx (int): 0 = outer frustum, 1 = inner frustum, 2 = frustum edges
        """
        # print 'idx_buffer: %s' % self.__class__
        # print('>> frustum.idx_buffer(%s, %d, %d, %d)' %
        #       (idx_buffer, num_vtx, start_idx, inst_idx))

        # 3 shapes in the frustum with same number of vtxs. Plus 4 edges.
        num_lights = self.num_lights
        grp_n_vtx = self.base_vtx_buffer_count()
        grp_n_idxs = grp_n_vtx * 2

        n_indices = (grp_n_idxs * 2 +                   # near/soft near
                     grp_n_idxs * 2 * num_lights +      # n * far/soft far
                     self.nedges * 2 * num_lights)      # frustum edges
        # print '   |__ generating %s indices' % n_indices
        indices = list([None] * n_indices)

        # near shape
        _gl_lines(indices, start_idx, grp_n_vtx, 0, loop=True)
        # near soft shape
        _gl_lines(indices, start_idx + grp_n_vtx, grp_n_vtx, grp_n_idxs,
                  loop=True)

        # compute offsets
        vtx_start = start_idx + grp_n_vtx * 2
        idx_start = grp_n_idxs * 2
        stride = int(grp_n_vtx / self.nedges)

        for lgt in range(num_lights):
            # far shape
            _gl_lines(indices, vtx_start, grp_n_vtx, idx_start, loop=True)

            # far soft shape
            vtx_start += grp_n_vtx
            idx_start += grp_n_idxs
            _gl_lines(indices, vtx_start, grp_n_vtx, idx_start, loop=True)

            # build edge lines
            near_vtx_start = start_idx + grp_n_vtx # second shape in VBO
            far_vtx_start = vtx_start  # last drawn shape in vbo
            idx_start += grp_n_idxs
            vtx_start += grp_n_vtx
            for i in range(idx_start, idx_start + 4 * 2, 2):             
                indices[i] = near_vtx_start
                indices[i + 1] = far_vtx_start
                near_vtx_start += stride
                far_vtx_start += stride
            idx_start += 4 * 2

        return indices     
