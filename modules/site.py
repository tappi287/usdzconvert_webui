

class JobFormFields:
    class OptionField:
        def __init__(self, _id: str, label: str, desc: str, input_type: str):
            self.id, self.label, self.desc = _id, label, desc
            self.input_type = input_type

    class FileField:
        def __init__(self, _id: str, label: str, desc: str, required: bool=False, channels_available: bool=False):
            self.id = _id
            self.channel_id = f'{_id}_channel'
            self.label = label
            self.desc = desc
            self.required = required
            self.channels_available = channels_available

            if channels_available:
                self.desc = f'{desc} [Optional] Select texture color channel (r, g, b or a)'

    file_fields = [
        FileField('scene_file', 'Scene file',
                  'Input file: OBJ/glTF(.gltf/glb)/FBX/Alembic(.abc)/USD(.usd/usda/usdc/usdz) files.', True),
        FileField('diffuseColor', 'Diffuse Map', 'Use <file> as texture for diffuseColor.'),
        FileField('normal', 'Normal Map', 'Use <file> as texture for normal.'),
        FileField('emissiveColor', 'Emissive Map', 'Use <file> as texture for emissiveColor.'),
        FileField('metallic', 'Metallic Map', 'Use <file> as texture for metallic.', channels_available=True),
        FileField('roughness', 'Roughness Map', 'Use <file> as texture for roughness.', channels_available=True),
        FileField('occlusion', 'Occlusion Map', 'Use <file> as texture for occlusion.', channels_available=True),
        FileField('opacity', 'Opacity Map', 'Use <file> as texture for opacity.', channels_available=True),
        FileField('clearcoat', 'Clearcoat Map', 'Use <file> as texture for clearcoat.', channels_available=True),
        FileField('clearcoatRoughness', 'Clearcoat Roughness Map', 'Use <file> as texture for clearcoat roughness.',
                  channels_available=True)
        ]

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
    ajax_upload = '/ajax_upload'
    static_downloads = 'static/downloads'

    navigation = {'jobs': job_page, 'manual': usd_man, 'downloads': downloads}

    templates = {root: 'index.html.j2', job_page: 'job.html.j2', usd_man: 'usdman.html.j2',
                 downloads: 'downloads.html.j2'}


class Site:
    title = 'USDZ Conversion Server'
    job_title = 'Job Page'
    version = ''

    urls = Urls
    job_form = JobFormFields()
