from __future__ import print_function
import os
import sys
import logging
import subprocess
import argparse

# Remove polluted OS Env when debugging or directly run without Popen env
# --
# os.environ['PATH'] = '..\\converter\\USD\\lib;..\\converter\\USD\\bin;..\\converter\\USD\\plugin\\usd;'
# --
try:
    from pxr import Usd, UsdShade, UsdUtils, Sdf
except ImportError:
    print('Failed to import Usd modules. Add USD_INSTALL/lib/python to PYTHONPATH')
    sys.exit(3)

logging.basicConfig(stream=sys.stdout, format='%(asctime)s %(name)s %(levelname)s: %(message)s',
                    datefmt='%d.%m.%Y %H:%M', level=logging.INFO)


def connect_material_inputs_to_uv_set(material):
    """
material_prim = usdviewApi.prim
from pxr import Sdr, UsdShade
material = UsdShade.Material(material_prim)
uv_input = UsdShade.ConnectableAPI(material.GetPrim()).GetInput('varname')
    :param UsdShade.Maetrial material:
    :return:
    """
    surface = material.GetSurfaceOutput()
    # uv_input = UsdShade.ConnectableAPI(material.GetPrim()).GetInput('varname')
    # uv_input = usdMaterial.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
    uv_input = material.GetPrim().GetAttribute('inputs:frame:stPrimvarName')
    if not uv_input:
        uv_input = material.CreateInput('frame:stPrimvarName', Sdf.ValueTypeNames.Token)
    uv_input.Set('uv')


def assign_materials_by_mesh_name(in_file, tmp_usdc):
    """
    Iterates a usd file UsdStage and binds materials to meshes with the exact same name (case insensitive)
    """
    if not os.path.exists(in_file):
        logging.error('Provided file path does not exist: %s', in_file)
        return False

    stage = Usd.Stage.Open(in_file)
    predicate = Usd.TraverseInstanceProxies(Usd.PrimIsActive & Usd.PrimIsDefined & ~Usd.PrimIsAbstract)

    mesh_prims = dict()
    material_prims = dict()

    # Iterate stage and get materials and mesh prims with lowercase names
    for prim in stage.Traverse(predicate):
        if prim.GetTypeName() == "Mesh":
            # Skip meshes that are already bound to a material
            bound_material, binding_rel = UsdShade.MaterialBindingAPI(prim).ComputeBoundMaterial(UsdShade.Tokens.full)
            if bound_material:
                logging.info('Mesh %s is already bound to material: %s',
                             prim.GetName(), bound_material.GetPrim().GetName())
                continue

            # Store ref to mesh without a material bound
            mesh_prims[prim.GetName().lower()] = prim

        elif prim.GetTypeName() == "Material":
            # Store ref to a scene material
            material_prims[prim.GetName().lower()] = prim

    # Compare mesh names with material names
    for mesh_name, prim in mesh_prims.items():
        mesh_name = mesh_name.lower()

        if mesh_name in material_prims:
            # Construct a Material from the material prim
            material = UsdShade.Material(material_prims[mesh_name])

            try:
                # Bind the UsdShadeMaterial to the mesh prim
                assign_result = UsdShade.MaterialBindingAPI(prim).Bind(material)
            except Exception as e:
                assign_result = False
                logging.error('Could not bind %s to material: %s', mesh_name, e)

            if assign_result:
                connect_material_inputs_to_uv_set(material)
                logging.info('Bound mesh to material by name: %s', mesh_name)
        else:
            logging.warning('No material matching name of mesh: "%s" it will appear unshaded!', mesh_name)

    try:
        stage.GetRootLayer().Export(tmp_usdc)
        del stage
    except Exception as e:
        logging.fatal('Could not export scene file: %s', e)
        return False

    return True


def get_usdzip_bin_path():
    for path in os.environ['PATH'].split(os.pathsep):
        if os.path.exists(os.path.join(path, 'usdzip')):
            return os.path.join(path, 'usdzip')


def main(in_file):
    usdzip_script = get_usdzip_bin_path()
    if not usdzip_script:
        logging.fatal('Pixar usdzip script could not be found. Did you put usd/bin on your PATH?')
        sys.exit(3)

    folder = os.path.dirname(in_file)
    file_name, file_ext = os.path.splitext(os.path.basename(in_file))
    tmp_usdc = os.path.join(folder, file_name + '_out' + file_ext)
    out_usdz = os.path.join(folder, file_name + '.usdz')

    logging.info('Started Alembic post processing.')
    result = assign_materials_by_mesh_name(in_file, tmp_usdc)

    if not result:
        sys.exit(2)

    usdzip_args = [sys.executable, usdzip_script, out_usdz, '--arkitAsset', tmp_usdc]
    p = subprocess.Popen(usdzip_args, env=os.environ)
    out, error = p.communicate()
    logging.debug(out)
    logging.error(error)

    if p.returncode and p.returncode != 0:
        logging.error('Error while creating USDZ package with usdzip')
        sys.exit(4)
    else:
        try:
            os.remove(in_file)
            os.remove(tmp_usdc)
        except Exception as e:
            # Notice the error but Happy End either way!
            logging.error('Deleted temp file with result:', e)


if __name__ == '__main__':
    # Define and parse command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='Job files as json dict')
    args = parser.parse_args()
    logging.info('Received args: %s', args.file_path)

    if not args.file_path:
        logging.error('Argument is missing.')
        sys.exit(1)

    main(args.file_path)

    # Happy End
    sys.exit(0)
