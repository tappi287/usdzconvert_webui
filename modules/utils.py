from modules.site import JobFormFields
from typing import Tuple


def rgba_string_to_int_list(c: str) -> Tuple[int, int, int, int]:
    """ Split an rgba(255, 255, 255, 1) css string into tuple of integers [255, 255, 255, 1] """
    c = c.replace('rgba(', '').replace(')', '')
    c = [int(c) for c in c.split(', ')]
    if len(c) < 4:
        return 0, 0, 0, 0
    return c[0], c[1], c[2], c[3]


def srgb_to_linear(color: float):
    """ Convert a sRGB gamma encoded color value to linear color value """
    if color <= 0.04045:
        return color / 12.92
    else:
        return pow(((color+0.055) / 1.055), 2.4)


def convert_srgb_to_rgb_linear(sr: int, sg: int, sb: int) -> Tuple[float, float, float]:
    return srgb_to_linear(sr / 255), srgb_to_linear(sg / 255), srgb_to_linear(sb / 255)


def convert_srgb_to_luminance(sr: int, sg: int, sb: int):
    """ Convert sRGB color values to a linear luminosity float value
        eg. 123, 123, 123 > 0.19806931955994886
        https://stackoverflow.com/a/56678483/4340869

        :param int sr: red color component in 8bit sRGB 0-255
        :param int sg: green color component in 8bit sRGB 0-255
        :param int sb: blue color component in 8bit sRGB 0-255
        :returns: linear luminosity value between 0..1
        :rtype: float
    """
    # Convert to linear 0-1 rgb values
    vr, vg, vb = convert_srgb_to_rgb_linear(sr, sg, sb)

    # Convert a gamma encoded RGB values to a linear luminosity
    y = (0.2126 * vr + 0.7152 * vg + 0.0722 * vb)
    return y


def get_color_param_by_map_type(map_type: str):
    """ Return color parameter type rgb/xyz/lum by texture map type """
    i = JobFormFields.TextureMap.texture_map_types.index(map_type)
    return JobFormFields.TextureMapColor.params[i]


def rgba_string_to_rgb_argument(rgba: str) -> str:
    """ Convert rgba(123, 123, 123, 1) to usdzconvert argument '0.19, 0.19, 0.19' """
    c = rgba_string_to_int_list(rgba)
    vr, vg, vb = convert_srgb_to_rgb_linear(*c[0:3])
    return f'{str(vr)}, {str(vg)}, {str(vb)}'


def get_usdz_color_argument(map_type: str, rgba_string: str) -> str:
    """ Get the usdzconvert color argument by texture map type.

        Example:
        diffuse -> '123 123 123'
        metallic -> '0.19806931955994886'

        :param str map_type: the texture map type as string, must be one of JobFormField.TextureMap.texture_map_types
        :param str rgba_string: color value as html rgba string rgba(123, 123, 123, 1)
        :returns: a valid usdzconvert string cli argument for the color/luminosity value(s)
        :rtype: str
    """
    if not rgba_string:
        return ''

    map_type = get_color_param_by_map_type(map_type)

    if map_type in (JobFormFields.TextureMapColor.rgb, JobFormFields.TextureMapColor.xyz):
        return rgba_string_to_rgb_argument(rgba_string)
    elif map_type == JobFormFields.TextureMapColor.lum:
        rgb = rgba_string_to_int_list(rgba_string)
        return str(convert_srgb_to_luminance(*rgb[0:3]))
