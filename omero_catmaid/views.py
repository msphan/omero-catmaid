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
	
	# prepare image rendering
	# TODO: this step is similar for all requests => use cache, session ???
	
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
	compress_quality = int(compress_quality)

	level = max_level - zm

	# compute scale width and height based on zoom level zm
	scalex = x * zoomLevelScaling[zm]
	scaley = y * zoomLevelScaling[zm]

	# render image
	jpeg_data = img.renderJpegRegion(z, t, scalex, scaley, w, h, level=level,
				                          compression=(compress_quality/100.0))

	return HttpResponse(jpeg_data, content_type='image/jpeg')

@login_required()
def render_tile_time(request, iid, conn=None, **kwargs):
	"""
	This function is rewritten based on the render_image_region function in omeroweb.webgateway.
	
	NOTE: use this function to evaluate render time a.a.f. of tile size, zoom level, compression.

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
	tstart = datetime.now() # login, get image object
	
	server_id = request.session['connector'].server_id
		
	pi = webgateway_views._get_prepared_image(request, iid, server_id=server_id, conn=conn)
	
	if pi is None:
		raise Http404
	img, compress_quality = pi
	
	tend = datetime.now()
	t_login = tend - tstart
	st_login = str(t_login.total_seconds())
	
	tstart = datetime.now() # prepare for image rendering
	
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
	compress_quality = int(compress_quality)

	level = max_level - zm
	
	# compute scale width and height based on zoom level zm
	scalex = x * zoomLevelScaling[zm]
	scaley = y * zoomLevelScaling[zm]
	
	tend = datetime.now()
	t_prepare = tend - tstart
	st_prepare = str(t_prepare.total_seconds())
	
	tstart = datetime.now() # render image region
	
	jpeg_data = img.renderJpegRegion(z, t, scalex, scaley, w, h, level=level,
				                          compression=(compress_quality/100.0))
	if jpeg_data is None:
		raise Http404
	
	tend = datetime.now()
	t_render = tend - tstart
	st_render = str(t_render.total_seconds())
	
	st_total = str(t_login.total_seconds()+t_prepare.total_seconds()+t_render.total_seconds())
	
	st = 'login:'+st_login+', prepare:'+st_prepare+', render:'+st_render+', total:'+st_total
	
	return HttpResponse(st)

@login_required()
def render_tile_catmaid(request, iid, conn=None, **kwargs):
	"""
	This function is rewritten based on the render_image_region function in omeroweb.webgateway.

	Returns a jpeg of the OMERO image, rendering only a region specified in
	query string as: 
	z=<stack_id>&t=<timepoint_id>&
	x=<x_tile_coord>&y=<y_tile_coor>&w=<tile_width>&h=<tile_height>&zm=<zoom_level>

	NOTE: This function is only used to serve Catmaid convention. 
	
	Rendering settings can be specified in the request parameters.

	@param request:     http request
	@param iid:         image ID
	@param conn:        L{omero.gateway.BlitzGateway} connection
	@return:            http response wrapping jpeg
	"""
	server_id = request.session['connector'].server_id

	pi = webgateway_views._get_prepared_image(request, iid, server_id=server_id, conn=conn)

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
	compress_quality = int(compress_quality)

	level = max_level - zm

	# region details in request are used as key for caching.
	jpeg_data = webgateway_cache.getImage(request, server_id, img, z, t)
	if jpeg_data is None:
		jpeg_data = img.renderJpegRegion(z, t, x, y, w, h, level=level,
					                       compression=(compress_quality/100.0))
		if jpeg_data is None:
			raise Http404
		webgateway_cache.setImage(request, server_id, img, z, t, jpeg_data)

	return HttpResponse(jpeg_data, content_type='image/jpeg')


	

