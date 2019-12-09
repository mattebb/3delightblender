"""blah"""

# pylint: disable=missing-docstring
from . import (txm_log, TxManagerError, NW, IT)

# wrap modes
TX_WRAP_MODE_BLACK = 'black'
TX_WRAP_MODE_CLAMP = 'clamp'
TX_WRAP_MODE_PERIODIC = 'periodic'
TX_WRAP_MODES = [TX_WRAP_MODE_BLACK, TX_WRAP_MODE_CLAMP,
                 TX_WRAP_MODE_PERIODIC]
# texture types
TX_TYPE_REGULAR = 'regular'
TX_TYPE_ENVLATL = 'envlatl'
TX_TYPES = [TX_TYPE_REGULAR, TX_TYPE_ENVLATL]
# texture file formats
TX_FORMAT_PIXAR = 'pixar'
TX_FORMAT_TIFF = 'tiff'
TX_FORMAT_OPENEXR = 'openexr'
TX_FORMATS = [TX_FORMAT_PIXAR, TX_FORMAT_TIFF, TX_FORMAT_OPENEXR]
# filters
TX_FILTER_CATMULL_ROM = 'catmull-rom'
TX_FILTER_POINT = 'point'
TX_FILTER_BOX = 'box'
TX_FILTER_TRIANGLE = 'triangle'
TX_FILTER_SINC = 'sinc'
TX_FILTER_GAUSSIAN = 'gaussian'
TX_FILTER_GAUSSIAN_SOFT = 'gaussian-soft'
TX_FILTER_MITCHELL = 'mitchell'
TX_FILTER_CUBIC = 'cubic'
TX_FILTER_LANCZOS = 'lanczos'
TX_FILTER_BESSEL = 'bessel'
TX_FILTER_BLACKMAN_HARRIS = 'blackman-harris'
TX_FILTERS = [TX_FILTER_CATMULL_ROM, TX_FILTER_POINT, TX_FILTER_BOX,
              TX_FILTER_TRIANGLE, TX_FILTER_SINC, TX_FILTER_GAUSSIAN,
              TX_FILTER_GAUSSIAN_SOFT, TX_FILTER_MITCHELL, TX_FILTER_CUBIC,
              TX_FILTER_BESSEL, TX_FILTER_BLACKMAN_HARRIS]
# resize modes
TX_RESIZE_UP = 'up'
TX_RESIZE_UP_DASH = 'up-'
TX_RESIZE_DOWN = 'down'
TX_RESIZE_DOWN_DASH = 'down-'
TX_RESIZE_ROUND = 'round'
TX_RESIZE_ROUND_DASH = 'round-'
TX_RESIZE_NONE = 'none'
TX_RESIZES = [TX_RESIZE_UP, TX_RESIZE_NONE, TX_RESIZE_UP_DASH, TX_RESIZE_DOWN,
              TX_RESIZE_DOWN_DASH, TX_RESIZE_ROUND, TX_RESIZE_ROUND_DASH]
# data types
TX_DATATYPE_FLOAT = 'float'
TX_DATATYPE_HALF = 'half'
TX_DATATYPE_BYTE = 'byte'
TX_DATATYPE_SHORT = 'short'
TX_DATATYPES = [TX_DATATYPE_FLOAT, TX_DATATYPE_HALF, TX_DATATYPE_BYTE,
                TX_DATATYPE_SHORT]
# compression schemes
TX_COMPRESSION_NONE = 'none'
TX_COMPRESSION_LOSSLESS = 'lossless'
TX_COMPRESSION_LOSSY = 'lossy'
TX_COMPRESSIONS = [TX_COMPRESSION_NONE, TX_COMPRESSION_LOSSLESS,
                   TX_COMPRESSION_LOSSY]
TX_EXRCOMPRESSION_NONE = 'none'
TX_EXRCOMPRESSION_RLE = 'rle'
TX_EXRCOMPRESSION_ZIP = 'zip'
TX_EXRCOMPRESSION_PIZ = 'piz'
TX_EXRCOMPRESSION_PXR24 = 'pxr24'
TX_EXRCOMPRESSION_B44 = 'b44'
TX_EXRCOMPRESSION_B44A = 'b44a'
TX_EXRCOMPRESSION_DWAA = 'dwaa'
TX_EXRCOMPRESSION_DWAB = 'dwab'
TX_EXRCOMPRESSIONS = [TX_EXRCOMPRESSION_NONE, TX_EXRCOMPRESSION_RLE,
                      TX_EXRCOMPRESSION_ZIP, TX_EXRCOMPRESSION_PIZ,
                      TX_EXRCOMPRESSION_PXR24, TX_EXRCOMPRESSION_B44,
                      TX_EXRCOMPRESSION_B44A,
                      TX_EXRCOMPRESSION_DWAA,
                      TX_EXRCOMPRESSION_DWAB]
TX_ALL_COMPRESSIONS = TX_COMPRESSIONS + TX_EXRCOMPRESSIONS
# presets
PRESET_REGULAR = {'texture_type': TX_TYPE_REGULAR,
                  'smode': TX_WRAP_MODE_PERIODIC,
                  'tmode': TX_WRAP_MODE_PERIODIC,
                  'texture_format': TX_FORMAT_PIXAR,
                  'texture_filter': TX_FILTER_CATMULL_ROM,
                  'resize': TX_RESIZE_UP_DASH,
                  'data_type': None,
                  'compression': TX_COMPRESSION_LOSSLESS,
                  'compression_level': None}
PRESET_ENVMAP = {'texture_type': TX_TYPE_ENVLATL,
                 'smode': None,
                 'tmode': None,
                 'texture_format': TX_FORMAT_OPENEXR,
                 'texture_filter': TX_FILTER_GAUSSIAN,
                 'resize': None,
                 'data_type': None,
                 'compression': TX_EXRCOMPRESSION_PXR24,
                 'compression_level': None}
PRESET_IMAGEPLANE = {'texture_type': TX_TYPE_REGULAR,
                     'smode': TX_WRAP_MODE_BLACK,
                     'tmode': TX_WRAP_MODE_BLACK,
                     'texture_format': TX_FORMAT_PIXAR,
                     'texture_filter': TX_FILTER_CATMULL_ROM,
                     'resize': TX_RESIZE_UP,
                     'data_type': None,
                     'compression': TX_COMPRESSION_LOSSLESS,
                     'compression_level': None}
TXMAKE_PRESETS = {'texture': PRESET_REGULAR,
                  'env': PRESET_ENVMAP,
                  'imageplane': PRESET_IMAGEPLANE}


class TxParams(object):
    """A class to hold various txmake options that affects texture making"""

    def __init__(self):
        self.log = txm_log()
        self.texture_type = TX_TYPE_REGULAR
        self.smode = TX_WRAP_MODE_PERIODIC
        self.tmode = TX_WRAP_MODE_PERIODIC
        self.texture_format = TX_FORMAT_PIXAR
        self.texture_filter = TX_FILTER_CATMULL_ROM
        self.resize = TX_RESIZE_UP_DASH
        self.data_type = None        # same as input file
        self.compression = TX_COMPRESSION_LOSSLESS
        self.compression_level = 45.0

    def set_texture_type(self, texture_type):
        if texture_type in TX_TYPES:
            self.texture_type = texture_type

    def set_s_mode(self, smode):
        if smode in TX_WRAP_MODES:
            self.smode = smode

    def set_t_mode(self, tmode):
        if tmode in TX_WRAP_MODES:
            self.tmode = tmode

    def set_texture_format(self, texture_format):
        if texture_format in TX_FORMATS:
            self.texture_format = texture_format

    def set_texture_filter(self, texture_filter):
        if texture_filter in TX_FILTERS:
            self.texture_filter = texture_filter

    def set_texture_resize(self, texture_resize):
        if texture_resize in TX_RESIZES:
            self.resize = texture_resize

    def set_data_type(self, data_type):
        if data_type in TX_DATATYPES:
            self.data_type = data_type

    def set_compression(self, comp):
        if self.texture_format is TX_FORMAT_OPENEXR:
            if comp in TX_EXRCOMPRESSIONS:
                self.compression = comp
        else:
            if comp in TX_COMPRESSIONS:
                self.compression = comp

    def set_compression_level(self, level):
        self.compression_level = level

    def get_texture_type(self):
        return self.texture_type

    def get_s_mode(self):
        return self.smode

    def get_t_mode(self):
        return self.tmode

    def get_texture_format(self):
        return self.texture_format

    def get_texture_filter(self):
        return self.texture_filter

    def get_resize(self):
        return self.resize

    def get_data_type(self):
        return self.data_type

    def get_compression(self):
        return self.compression

    def get_compression_level(self):
        return self.compression_level

    def __eq__(self, other):
        return (
            (self.texture_type, self.smode, self.tmode, self.texture_format,
             self.texture_filter, self.resize, self.data_type, self.compression,
             self.compression_level) ==
            (other.texture_type, other.smode, other.tmode, other.texture_format,
             other.texture_filter, other.resize, other.data_type, other.compression,
             self.compression_level))

    def __ne__(self, other):
        return (
            (self.texture_type, self.smode, self.tmode, self.texture_format,
             self.texture_filter, self.resize, self.data_type, self.compression,
             self.compression_level) !=
            (other.texture_type, other.smode, other.tmode, other.texture_format,
             other.texture_filter, other.resize, other.data_type, other.compression,
             self.compression_level))

    def __str__(self):
        sstr = '|_ TxParams:\n'
        sstr += '   |_ type: %s\n' % self.texture_type
        sstr += '   |_ wrap modes: %s %s\n' % (self.smode, self.tmode)
        sstr += '   |_ format: %s\n' % self.texture_format
        sstr += '   |_ filter: %s\n' % self.texture_filter
        sstr += '   |_ resize: %s\n' % self.resize
        sstr += '   |_ data type: %s\n' % self.data_type
        sstr += '   |_ compression: %s (%s)' % (self.compression,
                                                self.compression_level)
        return sstr

    def tooltip(self):
        html = '%s<div><b>TxParams</b>:</div>' % NW
        html += '%s&#8226; type: %s</div>' % (IT, self.texture_type)
        html += ('%s&#8226; wrap modes: %s %s</div>' %
                 (IT, self.smode, self.tmode))
        html += '%s&#8226; format: %s</div>' % (IT, self.texture_format)
        html += '%s&#8226; filter: %s</div>' % (IT, self.texture_filter)
        html += '%s&#8226; resize: %s</div>' % (IT, self.resize)
        html += '%s&#8226; data type: %s</div>' % (IT, self.data_type)
        html += ('%s&#8226; compression: %s (level=%s)</div>' %
                 (IT, self.compression, self.compression_level))
        html += '</div>'
        return html

    def get_params_as_list(self):
        def _append_if_valid(flag, attr):
            if attr is not None:
                params.append(flag)
                params.append(attr)

        params = []
        if self.texture_type is TX_TYPE_ENVLATL:
            params.append('-envlatl')

        if self.data_type is not None:
            params.append('-' + self.data_type)

        _append_if_valid('-smode', self.smode)
        _append_if_valid('-tmode', self.tmode)
        _append_if_valid('-format', self.texture_format)
        _append_if_valid('-filter', self.texture_filter)
        _append_if_valid('-resize', self.resize)
        _append_if_valid('-compression', self.compression)
        if self.compression in [TX_EXRCOMPRESSION_DWAA, TX_EXRCOMPRESSION_DWAB]:
            _append_if_valid('-compressionlevel', self.compression_level)

        return params

    def get_params_as_dict(self):
        params = {}
        try:
            params['texture_ype'] = self.texture_type
            params['data_type'] = self.data_type
            params['smode'] = self.smode
            params['tmode'] = self.tmode
            params['texture_format'] = self.texture_format
            params['texture_filter'] = self.texture_filter
            params['resize'] = self.resize
            params['compression'] = self.compression
            params['compression_level'] = self.compression_level
        except:
            raise TxManagerError('Unable to convert TxParams to a dictionary.')

        return params

    def set_params_from_dict(self, vardict):
        for key, val in vardict.items():
            try:
                setattr(self, key, val)
            except AttributeError:
                # warn but don't raise an error.
                self.log.warning('%s is not an attribute of TxParams ! vardict = %r',
                                 key, vardict)

    def fingerprint(self):
        def _get_index(array, value):
            try:
                return str(array.index(value))
            except IndexError:
                return '-'

        fgp = _get_index(TX_TYPES, self.texture_type)
        fgp += _get_index(TX_WRAP_MODES, self.smode)
        fgp += _get_index(TX_WRAP_MODES, self.tmode)
        fgp += _get_index(TX_FORMATS, self.texture_format)
        fgp += _get_index(TX_FILTERS, self.texture_filter)
        fgp += _get_index(TX_RESIZES, self.resize)
        fgp += _get_index(TX_DATATYPES, self.data_type)
        fgp += _get_index(TX_ALL_COMPRESSIONS, self.compression)
        return fgp
