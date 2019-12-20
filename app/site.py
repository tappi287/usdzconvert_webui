

class SiteContent:
    title = 'USDZ Conversion Server'
    version = ''

    class FileField:
        def __init__(self, _id: str, label: str, desc: str, channels_available=False):
            self.id = _id
            self.label = label
            self.desc = desc
            self.channels_available = channels_available
            if channels_available:
                self.desc = f'{desc} [Optional] Select texture color channel (r, g, b or a)'

    file_fields = [
        FileField('diffuseColor', 'Diffuse Map', 'Use <file> as texture for diffuseColor.'),
        FileField('normal', 'Normal Map', 'Use <file> as texture for normal.'),
        FileField('emissiveColor', 'Emissive Map', 'Use <file> as texture for emissiveColor.'),
        FileField('metallic', 'Metallic Map', 'Use <file> as texture for metallic.', True),
        FileField('roughness', 'Roughness Map', 'Use <file> as texture for roughness.', True),
        FileField('occlusion', 'Occlusion Map', 'Use <file> as texture for occlusion.', True),
        FileField('opacity', 'Opacity Map', 'Use <file> as texture for opacity.', True),
        FileField('clearcoat', 'Clearcoat Map', 'Use <file> as texture for clearcoat.', True),
        FileField('clearcoatRoughness', 'Clearcoat Roughness Map', 'Use <file> as texture for clearcoat roughness.',
                  True)
    ]
