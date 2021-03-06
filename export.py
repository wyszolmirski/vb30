#
# V-Ray For Blender
#
# http://chaosgroup.com
#
# Author: Andrei Izrantcev
# E-Mail: andrei.izrantcev@chaosgroup.com
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# All Rights Reserved. V-Ray(R) is a registered trademark of Chaos Software.
#

import os
import time
import datetime

import bpy

from vb30.lib.VRayStream import VRayExportFiles
from vb30.lib.VRayStream import VRayPluginExporter
from vb30.lib.VRayStream import VRayFilePaths

from vb30.lib import SysUtils, BlenderUtils

from vb30.nodes import export as NodesExport

from vb30.exporting import exp_init
from vb30.exporting import exp_settings
from vb30.exporting import exp_channels
from vb30.exporting import exp_frame
from vb30.exporting import exp_run
from vb30.exporting import exp_anim_full
from vb30.exporting import exp_anim_camera_loop

from vb30 import debug

HAS_VB35 = SysUtils.hasRtExporter()
if HAS_VB35:
    import _vray_for_blender_rt

@debug.TimeIt
def Export(bus, scene, engine, isPreview=False):
    o = bus['output']

    VRayScene    = scene.vray
    VRayExporter = VRayScene.Exporter

    ts = time.time()

    o.write('MAIN', "\n")
    o.write('MAIN', SysUtils.GetVRsceneTemplate("defaults.vrscene"))

    if VRayExporter.draft:
        o.write('MAIN', "\n")
        o.write('MAIN', SysUtils.GetVRsceneTemplate("draft.vrscene"))

    exp_channels.ExportRenderElements(bus)

    if VRayExporter.animation_mode in {'FRAMEBYFRAME', 'NONE'}:
        err = exp_frame.ExportSingleFrame(bus)

    elif VRayExporter.animation_mode == 'CAMERA_LOOP':
        err = exp_anim_camera_loop.ExportCameraLoop(bus)

    else:
        err = exp_anim_full.ExportAnimation(bus,
            scene.frame_start,
            scene.frame_end,
            scene.frame_step
        )

    if VRayScene.Includer.use:
        if VRayScene.Includer.use:
            o.write('MAIN', "\n// Include additional *.vrscene files")
            for includeFile in VRayScene.Includer.nodes:
                if not includeFile.use:
                    continue
                filepath = BlenderUtils.GetFullFilepath(includeFile.scene)
                o.write('MAIN', '\n#include "%s" // %s' % (filepath, includeFile.name))
            o.write('MAIN', '\n')

    # No need for interpolate() anymore
    o.setAnimation(False)
    exp_settings.ExportSettings(bus)

    te = time.time() - ts
    td = datetime.timedelta(seconds=te)
    d  = datetime.datetime(1,1,1) + td

    if not bus['preview']:
        debug.PrintMsg("Export done [%.2i:%.2i:%.2i]" % (d.hour, d.minute, d.second))

    return err


def ExportEx(bus):
    debug.Debug("ExportEx()")

    err = None

    scene  = bus['scene']
    engine = bus['engine']
    o      = bus['output']

    VRayScene    = scene.vray
    VRayExporter = VRayScene.Exporter
    VRayDR       = VRayScene.VRayDR

    pm = VRayFilePaths()

    # Setting user defined value here
    # It could be overriden in 'initFromScene'
    # depending on VRayDR settings
    pm.setSeparateFiles(VRayExporter.useSeparateFiles)

    pm.initFromScene(engine, scene)
    pm.printInfo()

    fm = VRayExportFiles(pm)
    fm.setOverwriteGeometry(VRayExporter.auto_meshes)

    try:
        fm.init()
    except Exception as e:
        debug.ExceptionInfo(e)
        return "Error initing files!"

    o.setFileManager(fm)
    o.setPreview(engine.is_preview)

    bus['exporter'] = exp_init.InitExporter(bus)

    try:
        # We do everything here basically because we want to close files
        # if smth goes wrong...
        rtExporter = HAS_VB35 and engine.bl_idname == 'VRAY_RENDER_RT'
        if not rtExporter:
            err = Export(bus, scene, engine, engine.is_preview)
        else:
            if not VRayExporter.animation_mode in {'NONE', 'CAMERA_LOOP'}:
                o.setAnimation(True)
                o.setFrameStart(scene.frame_start)
                o.setFrameEnd(scene.frame_end)
                o.setFrameStep(scene.frame_step)
            elif VRayExporter.animation_mode == 'CAMERA_LOOP':
                cameraCount = len([1 for o in scene.objects if o.type == 'CAMERA' and o.data.vray.use_camera_loop])
                o.setAnimation(True)
                o.setFrameStart(1)
                o.setFrameEnd(cameraCount)
                o.setFrameStep(1)

            init = {
                'context'      : bpy.context.as_pointer(),
                'engine'       : engine.as_pointer(),
                'data'         : bpy.data.as_pointer(),
                'scene'        : scene.as_pointer(),
                'mainFile'     : fm.getFileByPluginType('MAIN'),
                'objectFile'   : fm.getFileByPluginType('OBJECT'),
                'envFile'      : fm.getFileByPluginType('WORLD'),
                'geometryFile' : fm.getFileByPluginType('GEOMETRY'),
                'lightsFile'   : fm.getFileByPluginType('LIGHT'),
                'materialFile' : fm.getFileByPluginType('MATERIAL'),
                'textureFile'  : fm.getFileByPluginType('TEXTURE'),
                'cameraFile'   : fm.getFileByPluginType('CAMERA'),
            }

            # Free anything we have
            if engine.renderer:
                del engine.renderer

            renderer = _vray_for_blender_rt.init(**init)
            if renderer:
                # Write settings for new exporter.
                # TODO: Move this to cpp.
                exp_settings.ExportSettings(bus)

                setattr(engine, 'renderer', renderer)

                _vray_for_blender_rt.render(renderer)

    except Exception as e:
        debug.ExceptionInfo(e)
        err = str(e)
    finally:
        exp_init.ShutdownExporter(bus)
        o.done()

    return err


def ExportAndRun(engine, scene):
    if engine.test_break():
        return "Export is interrupted!"

    VRayScene    = scene.vray
    VRayExporter = VRayScene.Exporter

    o = VRayPluginExporter()

    bus = {
        'output' : o,

        'engine' : engine,
        'scene'  : scene,
        'camera' : scene.camera,

        'skipObjects'        : set(),
        'environment_volume' : set(),
        'gizmos'             : set(),

        'preview'    : engine.is_preview,

        # Used to pass nodes into plugin exporter
        # to access some special data like "fake" textures
        'context' : {
            'node' : None,
        },

        'cache' : {
            'plugins' : set(),
            'mesh'    : set(),
        },

        'defaults' : {
            'brdf'     : "BRDFNOBRDFISSET",
            'material' : "MANOMATERIALISSET",
            'texture'  : "TENOTEXTUREIESSET",
            'uvwgen'   : "DEFAULTUVWC",
            'blend'    : "TEDefaultBlend",
        },
    }

    err = ExportEx(bus)
    if err is not None:
        return err

    err = exp_run.RunEx(bus)
    if err is not None:
        return err

    return None


# First check the animation type:
#
# 'FRAMEBYFRAME' "Export and render frame by frame"
# 'FULL'         "Export full animation range then render"
# 'NOTMESHES'    "Export full animation range without meshes"
# 'CAMERA'       "Export full animation of camera motion"
#
# 'FRAMEBYFRAME' should also support exporting of 2 (or more) frames at once for correct motion blur
#
def RenderScene(engine, scene):
    VRayScene    = scene.vray
    VRayExporter = VRayScene.Exporter

    err = None

    if VRayExporter.animation_mode == 'FRAMEBYFRAME':
        # Store current frame
        selected_frame = scene.frame_current

        f = scene.frame_start
        while(f <= scene.frame_end):
            scene.frame_set(f)

            err = ExportAndRun(engine, scene)
            if err is not None:
                break

            f += scene.frame_step

        # Restore selected frame
        scene.frame_set(selected_frame)

    else:
        err = ExportAndRun(engine, scene)

    return err
