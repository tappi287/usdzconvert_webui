

class JobFormFields:
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

    additional_args = 'additional_args'
    additional_args_text = 'usdzconvert additional arguments'


class Urls:
    root = '/'
    current_job = '/current_job'
    usd_man = '/usd_manual'
    ajax_upload = '/ajax_upload'
    job_download = '/job_download'

    templates = {root: 'index.html.j2', current_job: 'job.html.j2', usd_man: 'usdman.html.j2'}


class Site:
    title = 'USDZ Conversion Server'
    job_title = 'Job Page'
    version = ''

    urls = Urls
    job_form = JobFormFields()
