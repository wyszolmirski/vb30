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

from vb30 import debug

from . import exp_init
from . import exp_scene
from . import exp_anim_full


@debug.TimeIt
def ExportSingleFrame(bus):
    o      = bus['output']
    scene  = bus['scene']

    err = None

    VRayScene    = scene.vray
    VRayExporter = VRayScene.Exporter

    if VRayExporter.frames_to_export > 1:
        frameStart = scene.frame_current
        frameEnd   = frameStart + VRayExporter.frames_to_export
        frameStep  = scene.frame_step

        err = exp_anim_full.ExportAnimation(
            bus,
            frameStart,
            frameEnd,
            frameStep
        )

    else:
        bus['exporter'] = exp_init.InitExporter(bus)
        err = exp_scene.ExportScene(bus)
        exp_init.ShutdownExporter(bus)

    return err
