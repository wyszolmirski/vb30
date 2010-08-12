'''

 V-Ray/Blender 2.5

 http://vray.cgdo.ru

 Author: Andrey M. Izrantsev (aka bdancer)
 E-Mail: izrantsev@gmail.com

 This plugin is protected by the GNU General Public License v.2

 This program is free software: you can redioutibute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 (at your option) any later version.

 This program is dioutibuted in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with this program.  If not, see <http://www.gnu.org/licenses/>.

 All Rights Reserved. V-Ray(R) is a registered trademark of Chaos Software.

'''


''' Python modules  '''
import os
import sys
import tempfile
import math
import subprocess
import time

''' Blender modules '''
import bpy


PLATFORM= sys.platform


def	debug(sce, s):
	if(sce.vray_debug):
		print("V-Ray/Blender: %s"%(s))

def p(t):
	if type(t) == type(True):
		return "%i"%(t)
	elif type(t) == type(1):
		return "%i"%(t)
	elif type(t) == type(1.0):
		return "%.6f"%(t)
	elif str(type(t)) == "<class 'color'>":
		return "Color(%.3f,%.3f,%.3f)"%(tuple(t))
	elif str(type(t)) == "<class 'vector'>":
		return "Color(%.3f,%.3f,%.3f)"%(tuple(t))
	elif type(t) == type(""):
		if(t == "True"):
			return "1"
		elif(t == "False"):
			return "0"
		else:
			return t
	else:
		return "%s"%(t)

def a(sce,t):
	return "interpolate((%i,%s))"%(sce.frame_current,p(t))

def transform(m):
	return "Transform(Matrix(Vector(%f, %f, %f),Vector(%f, %f, %f),Vector(%f, %f, %f)),Vector(%f, %f, %f))"\
            %(m[0][0], m[0][1], m[0][2],\
              m[1][0], m[1][1], m[1][2],\
              m[2][0], m[2][1], m[2][2],\
              m[3][0], m[3][1], m[3][2])

def clean_string(s):
	s= s.replace("+", "p")
	s= s.replace("-", "m")
	for i in range(len(s)):
		c= s[i]
		if not ((c >= 'A' and c <= 'Z') or (c >= 'a' and c <= 'z') or (c >= '0' and c <= '9')):
			s= s.replace(c, "_")
	return s

def get_filename(fn):
	(filepath, filename)= os.path.split(bpy.path.abspath(fn))
	return filename

def get_full_filepath(filepath):
	return os.path.normpath(bpy.path.abspath(filepath))

def get_render_file_format(file_format):
	if file_format in ('JPEG','JPEG2000'):
		file_format= 'jpg'
	elif file_format in ('OPEN_EXR','IRIS','CINEON'):
		file_format= 'exr'
	elif file_format == 'MULTILAYER':
		file_format= 'vrimg'
	elif file_format in ('TARGA', 'TARGA_RAW'):
		file_format= 'tga'
	else:
		file_format= 'png'
	return file_format.lower()
	
def get_name(data, prefix= None):
	name= data.name
	if(prefix):
		name= "%s_%s"%(prefix,name)
	if(data.library):
		name+= "_%s"%(get_filename(data.library.filepath))
	return clean_string(name)

def object_on_visible_layers(sce,ob):
	for l in range(20):
		if ob.layers[l] and sce.layers[l]:
			return True
	return False

def vb_script_path():
	for vb_path in bpy.utils.script_paths(os.path.join('io','vb25')):
		if vb_path != '':
			return vb_path
	return ''

def vb_binary_path():
	vray_bin= 'vray'
	if(PLATFORM == "win32"):
		vray_bin= 'vray.exe'
	vray_path= vray_bin
	vray_env_path= os.getenv('VRAY_PATH')

	if vray_env_path is None:
		for maya in ('2011','2010','2009','2008'):
			for arch in ('x64','x86'):
				vray_env_path= os.getenv("VRAY_FOR_MAYA%s_MAIN_%s"%(maya,arch))
				if vray_env_path:
					break
			if vray_env_path:
				break
		if vray_env_path:
			vray_env_path= os.path.join(vray_env_path,'bin')

	if vray_env_path:
		if PLATFORM == "win32":
			if vray_env_path[0:1] == "\"":
				vray_env_path= vray_env_path[1:-1]
		else:
			if vray_env_path[0:1] == ":":
				vray_env_path= vray_env_path[1:]
		vray_path=  os.path.join(vray_env_path, vray_bin)

	return vray_path

def get_plugin(plugins, plugin_type):
	for plugin in plugins:
		if plugin.ID == plugin_type:
			return plugin
	return None