from modules.globals import VERSION
from modules.settings import JsonPickleHelper


class WithJsonDictMethod:
    @classmethod
    def as_json_dict(cls):
        json_friendly_class_dict = dict()

        for k, v in cls.__dict__.items():
            if k.startswith('__'):
                continue
            if JsonPickleHelper.is_serializable(v):
                json_friendly_class_dict[k] = v

        return json_friendly_class_dict


class JobFormFields:
    class TextureMap(WithJsonDictMethod):
        """ FrontEnd will enumerate eg. texture_file_1 """
        file = 'texture_file'  # FrontEnd class name, BackEnd Form key
        file_label = 'texture_file_label'
        type = 'texture_type'
        type_desc = 'texture_type_description'
        channel = 'texture_channel'
        material = 'texture_material'
        uv_coord = 'uv_coord'
        material_color = 'material_color'
        material_color_desc = 'Use RGBA color as fallback value for the current map.'
        uv_desc = "Leave blank to auto-detect appropriate UV set. [Optional] Enter the name of the UV set to " \
                  "use for the current material."
        material_desc = "Leave blank to assign map to the Default material. [Optional] enter the name of the input " \
                        "file material you want this texture map assigned to"
        file_storage = 'texture_map'
        add_color_btn_id = 'add_button'
        add_color_btn_desc = "Add empty texture map entry to define a material and it's fallback color"

        # Html template will use above to set html element class name
        # FrontEnd will iterate html_elements list and enumerate eg. texture_type_1
        html_element_class_names = [file_label, file, type, channel, material, type_desc, uv_coord, material_color]

        # Template values
        texture_map_types = ['diffuseColor', 'normal', 'emissiveColor', 'metallic', 'roughness', 'occlusion',
                             'opacity', 'clearcoat', 'clearcoatRoughness']
        texture_map_channel = [False, False, False, True, True, True, True, True, True]
        texture_map_labels = [
            'Diffuse Map', 'Normal Map', 'Emissive Map', 'Metallic Map', 'Roughness Map', 'Occlusion Map',
            'Opacity Map',
            'Clearcoat Map', 'Clearcoat Roughness Map']
        texture_map_desc = ['Use <file> as texture for diffuseColor. [Optional] Use Color Pickr to define a fallback color',
                            'Use <file> as texture for normal. [Optional] Use Color Pickr to define x y z fallback values',
                            'Use <file> as texture for emissiveColor. [Optional] Use Color Pickr to define a fallback color',
                            'Use <file> as texture for metallic. [Optional] Select texture color channel (r, g, '
                            'b or a). [Optional] Use Color Pickr to define a fallback luminosity(hue will be ignored)',
                            'Use <file> as texture for roughness. [Optional] Select texture color channel (r, g, '
                            'b or a). [Optional] Use Color Pickr to define a fallback luminosity(hue will be ignored)',
                            'Use <file> as texture for occlusion. [Optional] Select texture color channel (r, g, '
                            'b or a). [Optional] Use Color Pickr to define a fallback luminosity(hue will be ignored)',
                            'Use <file> as texture for opacity. [Optional] Select texture color channel (r, g, b or a). '
                            '[Optional] Use Color Pickr to define a fallback luminosity(hue will be ignored)',
                            'Use <file> as texture for clearcoat. [Optional] Select texture color channel (r, g, '
                            'b or a). [Optional] Use Color Pickr to define a fallback luminosity(hue will be ignored)',
                            'Use <file> as texture for clearcoat roughness. [Optional] Select texture color channel '
                            '(r, g, b or a). [Optional] Use Color Pickr to define a fallback luminosity'
                            '(hue will be ignored)']
        texture_map_list = [(t, l, d) for t, l, d in zip(texture_map_types, texture_map_labels, texture_map_desc)]

    class TextureMapColor:
        rgb = 0
        rgba = 1
        xyz = 2
        lum = 3

        # Ordered by TextureMap.texture_map_types
        # diffuse, normal, emissive, metallic, rough, occlu, opacity, clearc, clearc-rough
        params = [rgb, xyz, rgb, lum, lum, lum, lum, lum, lum]

    class OptionField:
        def __init__(self, _id: str, label: str, desc: str, input_type: str):
            self.id, self.label, self.desc = _id, label, desc
            self.input_type = input_type

    class FileField:
        def __init__(self, _id: str, label: str, desc: str, required: bool=False):
            self.id = _id
            self.channel_id = f'{_id}_channel'
            self.label = label
            self.desc = desc
            self.required = required

    scene_file_field = FileField('scene_file', 'Scene file',
                                 'OBJ / glTF(.gltf/glb) / FBX / Alembic(.abc) / USD(.usd/usda/usdc/usdz)',
                                 True)

    option_fields = [
        OptionField('url', 'Url', 'Add URL metadata', 'url'),
        OptionField('copyright', 'Copyright', 'Add copyright metadata', 'textarea'),
        OptionField('copytextures', 'Copy textures', 'Copy texture files (for .usd/usda/usdc) workflows', 'checkbox'),
        OptionField('metersPerUnit', 'Meters Per Unit', 'Set metersPerUnit attribute with float value', 'float'),
        OptionField('loop', 'Loop', 'Set animation loop flag to 1', 'checkbox'),
        OptionField('no-loop', 'No Loop', 'Set animation loop flag to 0', 'checkbox'),
        OptionField('iOS12', 'iOS12', 'Make output file compatible with iOS 12 frameworks', 'checkbox'),
        OptionField('outSuffix', 'Format', 'Output .usd/usda/usdc/usdz files', 'format-select'),
        OptionField('v', 'Verbose', 'Verbose output.', 'checkbox'),
        ]
    options_by_id = {o.id: o for o in option_fields}

    additional_args = 'additional_args'
    additional_args_text = 'usdzconvert additional arguments'


class Urls:
    root = '/'
    job_page = '/jobs'
    job_download = '/job_download'
    job_delete = '/job_delete'
    usd_man = '/usd_manual'
    downloads = '/downloads'
    download_delete = '/downloads/delete'
    about = '/about'
    host = '/addhost'
    share = '/share'
    share_template = 'share/template'
    log = '/log'

    static_images = 'static/img'

    navigation = {'jobs': job_page, 'manual': usd_man, 'downloads': downloads, 'share': host}

    templates = {root: 'index.html.j2', job_page: 'job.html.j2', usd_man: 'usdman.html.j2', log: 'log.html.j2',
                 downloads: 'downloads.html.j2', about: 'about.html.j2', host: 'host.html.j2',
                 share: 'share.html.j2', share_template: 'share_template.html.j2'}


class Site:
    title = 'USDZ Conversion Server'
    job_title = 'Job Page'
    version = VERSION

    urls = Urls
    job_form = JobFormFields()
