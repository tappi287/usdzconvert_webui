

class JobFormFields:
    class TextureMap:
        """ FrontEnd will enumerate eg. texture_file_1 """
        file = 'texture_file'  # FrontEnd class name, BackEnd Form key
        type = 'texture_type'
        channel = 'texture_channel'
        material = 'texture_material'
        material_desc = "Leave blank to assign map to the Default material. [Optional] enter the name of the input " \
                        "file material you want this texture map assigned to"
        file_storage = 'texture_map'

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

    texture_map_types = ['diffuseColor', 'normal', 'emissiveColor', 'metallic', 'roughness', 'occlusion',
                         'opacity', 'clearcoat', 'clearcoatRoughness']
    texture_map_channel = [False, False, False, True, True, True, True, True, True]
    texture_map_labels = [
        'Diffuse Map', 'Normal Map', 'Emissive Map', 'Metallic Map', 'Roughness Map', 'Occlusion Map', 'Opacity Map',
        'Clearcoat Map', 'Clearcoat Roughness Map']

    texture_map_desc = ['Use <file> as texture for diffuseColor.', 'Use <file> as texture for normal.',
                        'Use <file> as texture for emissiveColor.',
                        'Use <file> as texture for metallic. [Optional] Select texture color channel (r, g, b or a)',
                        'Use <file> as texture for roughness. [Optional] Select texture color channel (r, g, b or a)',
                        'Use <file> as texture for occlusion. [Optional] Select texture color channel (r, g, b or a)',
                        'Use <file> as texture for opacity. [Optional] Select texture color channel (r, g, b or a)',
                        'Use <file> as texture for clearcoat. [Optional] Select texture color channel (r, g, b or a)',
                        'Use <file> as texture for clearcoat roughness. [Optional] Select texture color channel '
                        '(r, g, b or a)']
    texture_map_list = [(t, l, d) for t, l, d in zip(texture_map_types, texture_map_labels, texture_map_desc)]

    option_fields = [
        OptionField('url', 'Url', 'Add URL metadata', 'url'),
        OptionField('copyright', 'Copyright', 'Add copyright metadata', 'textarea'),
        OptionField('copytextures', 'Copy textures', 'Copy texture files (for .usd/usda/usdc) workflows', 'checkbox'),
        OptionField('metersPerUnit', 'Meters Per Unit', 'Set metersPerUnit attribute with float value', 'float'),
        OptionField('loop', 'Loop', 'Set animation loop flag to 1', 'checkbox'),
        OptionField('no-loop', 'No Loop', 'Set animation loop flag to 0', 'checkbox'),
        OptionField('iOS12', 'iOS12', 'Make output file compatible with iOS 12 frameworks', 'checkbox'),
        OptionField('v', 'Verbose', 'Verbose output.', 'checkbox'),
        ]

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
    static_downloads = 'static/downloads'
    about = '/about'
    log = '/log'

    navigation = {'jobs': job_page, 'manual': usd_man, 'downloads': downloads}

    templates = {root: 'index.html.j2', job_page: 'job.html.j2', usd_man: 'usdman.html.j2', log: 'log.html.j2',
                 downloads: 'downloads.html.j2', about: 'about.html.j2'}


class Site:
    title = 'USDZ Conversion Server'
    job_title = 'Job Page'
    version = ''

    urls = Urls
    job_form = JobFormFields()
