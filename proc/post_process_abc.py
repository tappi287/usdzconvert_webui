from __future__ import print_function
import os
import sys
import logging
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


def assign_materials_by_mesh_name(in_file):
    """
    Iterates a usd file UsdStage and binds materials to meshes with the exact same name (case insensitive)
    """
    if not os.path.exists(in_file):
        logging.error('Provided file path does not exist: %s', in_file)
        return False

    folder = os.path.dirname(in_file)
    file_name, file_ext = os.path.splitext(os.path.basename(in_file))
    tmp_usdc = os.path.join(folder, file_name + '_out' + file_ext)
    out_usdz = os.path.join(folder, file_name + '.usdz')

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
                logging.info('Bound mesh to material by name: %s', mesh_name)
        else:
            logging.warning('No material matching name of mesh: "%s" it will appear unshaded!', mesh_name)

    try:
        stage.GetRootLayer().Export(tmp_usdc)
        UsdUtils.CreateNewARKitUsdzPackage(Sdf.AssetPath(tmp_usdc), out_usdz)
        del stage
        os.remove(tmp_usdc)
        os.remove(in_file)
    except Exception as e:
        logging.fatal('Could not export scene file as USDZ: %s', e)
        return False

    return True


if __name__ == '__main__':
    # Define command line arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('file_path', help='Absolute path to the usdc file.', type=str)
    args = parser.parse_args()

    if not args.file_path:
        logging.error('File_path argument is missing.')
        sys.exit(1)

    logging.info('Started Alembic post processing.')
    result = assign_materials_by_mesh_name(args.file_path)

    if not result:
        sys.exit(2)

    # Happy End
    sys.exit(0)
