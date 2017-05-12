from django.conf.urls import url, patterns
from . import views

urlpatterns = patterns('django.views.generic.simple',

	url(r'^$', views.index, name="omerocatmaid_index"),
		
	url(r'^render_tile/(?P<iid>[0-9]+)/$',
    views.render_tile, name="omerocatmaid_render_tile"),
    
    url(r'^render_tile_catmaid/(?P<iid>[0-9]+)/$',
    views.render_tile_catmaid, name="omerocatmaid_render_tile_catmaid"),

)
