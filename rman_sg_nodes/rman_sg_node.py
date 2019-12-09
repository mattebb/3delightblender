class RmanSgNode(object):
    '''
    RmanSgNode and subclasses are meant to be a thin layer class around a RixSceneGraph node.

    Attributes:
        rman_scene (RmanScene) - pointer back to RmanScene instance
        sg_node (RixSgNode) - main scene graph node
        db_name (str) - unique datablock name for this node
        instances (dict) - instances that uses this sg_node
        motion_steps (list) - the full list of motion time samples that are required for this Blender object
        is_frame_sensitive (bool) - indicates that the sg_node should be updated on frame changes
 
    '''
    def __init__(self, rman_scene, sg_node, db_name):
        self.rman_scene = rman_scene
        self.sg_node = sg_node
        self.db_name = db_name
        self.instances = dict()
        self.motion_steps = []

        # indicates that this node needs updating
        # when the frame changes. This is mostly for
        # materials and lights using the {F} frame variable
        # in texture paths
        self.is_frame_sensitive = False

    @property
    def rman_scene(self):
        return self.__rman_scene

    @rman_scene.setter
    def rman_scene(self, rman_scene):
        self.__rman_scene = rman_scene

    @property
    def sg_node(self):
        return self.__sg_node

    @sg_node.setter
    def sg_node(self, sg_node):
        self.__sg_node = sg_node

    @property
    def db_name(self):
        return self.__db_name

    @db_name.setter
    def db_name(self, db_name):
        self.__db_name = db_name

    @property
    def instances(self):
        return self.__instances

    @instances.setter
    def instances(self, instances):
        self.__instances = instances  

    @property
    def motion_steps(self):
        return self.__motion_steps

    @motion_steps.setter
    def motion_steps(self, motion_steps):
        self.__motion_steps = motion_steps        

    @property
    def is_frame_sensitive(self):
        return self.__is_frame_sensitive

    @is_frame_sensitive.setter
    def is_frame_sensitive(self, is_frame_sensitive):
        self.__is_frame_sensitive = is_frame_sensitive             