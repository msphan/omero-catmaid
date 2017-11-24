#!/usr/bin/env python
# -*- coding: utf-8 -*-
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.shortcuts import render
from django.views import generic
from django.core.urlresolvers import reverse

from omeroweb.webgateway import views as webgateway_views

from omeroweb.webclient.decorators import login_required, render_response

from cStringIO import StringIO

from omeroweb.webgateway.webgateway_cache import webgateway_cache, CacheBase, webgateway_tempfile

import logging
import omero
from omero.rtypes import rstring
import omero.gateway
import random


logger = logging.getLogger(__name__)


try:
	from PIL import Image
except:  # pragma: nocover
	try:
		import Image
	except:
		logger.error('No Pillow installed,\
							line plots and split channel will fail!')

try:
	import numpy
	numpyInstalled = True
except ImportError:
	logger.error('No numpy installed')
	numpyInstalled = False

import json
from datetime import datetime
from django.core.cache import cache 
import ast

def index(request):
	"""
	Just a place-holder while we get started
	"""
	return HttpResponse("Welcome to omero-catmaid app home-page!!!")

@login_required()
def render_tile(request, iid, conn=None, **kwargs):
	"""
	This function is rewritten based on the render_image_region function in omeroweb.webgateway.
	
	Returns a jpeg of the OMERO image, rendering only a region specified in
	query string as: 
	z=<stack_id>&t=<timepoint_id>&
	x=<x_tile_coord>&y=<y_tile_coor>&w=<tile_width>&h=<tile_height>&zm=<zoom_level>
		
	Rendering settings can be specified in the request parameters.

	@param request:     http request
	@param iid:         image ID
	@param conn:        L{omero.gateway.BlitzGateway} connection
	@return:            http response wrapping jpeg
	"""
	server_id = request.session['connector'].server_id

	# login get image object
	pi = webgateway_views._get_prepared_image(request, iid, server_id=server_id, conn=conn)

	if pi is None:
		raise Http404
	img, compress_quality = pi
	
	# get query parameters
	z = request.GET.get('z', None)
	t = request.GET.get('t', None)
	x = request.GET.get('x', None)
	y = request.GET.get('y', None)
	w = request.GET.get('w', None)
	h = request.GET.get('h', None)
	zm = request.GET.get('zm', None)

	x,y,w,h = float(x),float(y),int(float(w)),int(float(h))
	zm = int(zm)
	compress_quality = int(compress_quality)
	
	# get supported zoom level scaling
	zoomLevelScaling = img.getZoomLevelScaling()
	
	if zoomLevelScaling is None:
		level = None
		scaleh = h * 2**zm
		scalew = w * 2**zm
		# render image
		jpeg_data = img.renderJpegRegion(z, t, x, y, scalew, scaleh, level=level,
				                          compression=(compress_quality/100.0))  	
      # resize into tile size (w,h)
	 	tempBuff = StringIO()
	 	tempBuff.write(jpeg_data)
	 	tempBuff.seek(0) #need to jump back to the beginning before handing it off to PIL
	 	im = Image.open(tempBuff)
	 	im = im.resize(size=(w,h))
	 	
	 	# reconvert to string data
	 	rv = StringIO()
		im.save(rv, 'jpeg', quality=compress_quality)
		jpeg_data = rv.getvalue()

	else: # support Pyramid
		max_level = len(zoomLevelScaling.keys()) - 1
		level = max_level - zm
		# compute scale width and height based on zoom level zm
		scalex = x * zoomLevelScaling[zm]
		scaley = y * zoomLevelScaling[zm]
		# render image
		jpeg_data = img.renderJpegRegion(z, t, scalex, scaley, w, h, level=level,
				                          	compression=(compress_quality/100.0))

	return HttpResponse(jpeg_data, content_type='image/jpeg')

def getZoomLevelScaling(re):
	"""
	Similar implementation to this method in Blitz Gateway.
	Returns a dict of zoomLevels:scale (fraction) for tiled 'Big' images.
	eg {0: 1.0, 1: 0.25, 2: 0.062489446727078291, 3: 0.031237687848258006}
	Returns None if this image doesn't support tiles.
	"""
	if not re.requiresPixelsPyramid():
		return None
	levels = re.getResolutionDescriptions()
	rv = {}
	sizeXList = [level.sizeX for level in levels]
	for i, level in enumerate(sizeXList):
		rv[i] = float(level)/sizeXList[0]
	return rv

def renderJpegRegion(re, z, t, x, y, width, height, level=None,
                     compression=0.9):
    """
    Similar implementation to this method in Blitz Gateway.
    Return the data from rendering a region of an image plane.
    NB. Projection not supported by the API currently.

    :param z:               The Z index. Ignored if projecting image.
    :param t:               The T index.
    :param x:               The x coordinate of region (int)
    :param y:               The y coordinate of region (int)
    :param width:           The width of region (int)
    :param height:          The height of region (int)
    :param compression:     Compression level for jpeg
    :type compression:      Float
    """

    plane_def = omero.romio.PlaneDef(omero.romio.XY)
    plane_def.z = long(z)
    plane_def.t = long(t)

    regionDef = omero.romio.RegionDef()
    regionDef.x = int(x)
    regionDef.y = int(y)
    regionDef.width = int(width)
    regionDef.height = int(height)
    plane_def.region = regionDef
    if level is not None:
        re.setResolutionLevel(level)
    if compression is not None:
        re.setCompressionLevel(float(compression))
    return re.renderCompressed(plane_def, {'omero.group': '-1'})

@login_required(doConnectionCleanup=False)
def render_tile_lab(request, iid, conn=None, **kwargs):
	"""
	This function is rewritten based on the render_image_region function in omeroweb.webgateway.
	
	Returns a jpeg of the OMERO image, rendering only a region specified in
	query string as: 
	z=<stack_id>&t=<timepoint_id>&
	x=<x_tile_coord>&y=<y_tile_coor>&w=<tile_width>&h=<tile_height>&zm=<zoom_level>
		
	Rendering settings can be specified in the request parameters.

	@param request:     http request
	@param iid:         image ID
	@param conn:        L{omero.gateway.BlitzGateway} connection
	@return:            http response wrapping jpeg
	
	NOTE: this function is under development. The goal is to avoid multiple rendering
	preparations for an image at every request.
	
	"""
	services = conn.c.sf.activeServices()
	re = None
	# Try to re-use existing Rendering Engine...
	for s in services:
		if 'RenderingEngine' in s:
			p = conn.c.sf.getByName(s)
			r = omero.api.RenderingEnginePrx.checkedCast(p)
			pixels = r.getPixels()
			image_id = pixels.getImage().id.val
			# ...if we find a Rendering Engine with correct image ID, use it...
			if long(iid) == image_id:
				re = r
			else:
				# ...otherwise close()
				r.close()

	if re is not None:
		# NB: Seems we can't call re.getResolutionDescriptions() here, get:
		# serverExceptionClass = ome.conditions.InternalException
		# message =  Wrapped Exception: (java.lang.IllegalStateException):
		# ImageReader.getResolutionCount: Current file should not be null; call setId(String) first
		zoomLevelScaling = getZoomLevelScaling(re)
	else:
		pi = webgateway_views._get_prepared_image(request, iid, conn=conn)

		if pi is None:
			raise Http404
		img, compress_quality = pi
		zoomLevelScaling = img.getZoomLevelScaling()
	
	max_level = len(zoomLevelScaling.keys()) - 1

	# get query parameters
	z = request.GET.get('z', None)
	t = request.GET.get('t', None)
	x = request.GET.get('x', None)
	y = request.GET.get('y', None)
	w = request.GET.get('w', None)
	h = request.GET.get('h', None)
	zm = request.GET.get('zm', None)

	x,y,w,h = float(x),float(y),int(float(w)),int(float(h))
	zm = int(zm)
	compress_quality = 90  # int(compress_quality)

	level = max_level - zm

	# compute scale width and height based on zoom level zm
	scalex = x * zoomLevelScaling[zm]
	scaley = y * zoomLevelScaling[zm]

	# render image
	if re is not None:
		jpeg_data = renderJpegRegion(re, z, t, scalex, scaley, w, h, level=level,
									 compression=(compress_quality/100.0))
	else:
		jpeg_data = img.renderJpegRegion(z, t, scalex, scaley, w, h, level=level,
										 compression=(compress_quality/100.0))

	return HttpResponse(jpeg_data, content_type='image/jpeg')


