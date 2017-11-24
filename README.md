# OME-CATMAID
**Using CATMAID to visualize images stored in OMERO server.**

[CATMAID](http://catmaid.readthedocs.io/en/stable/) is a well-known annotation application for large scale bioimages, particularly for neuronal images. CATMAID itself does not host any images. 
On the other hand, [OMERO](http://www.openmicroscopy.org/omero/) is a full environment for bioimages storage and manangement. It supports various APIs to work with many languages.
Linking CATMAID and OMERO allows us to profit the advantages of the both two apps.

## Installation

We suppose that you installed OMERO and CATMAID. Here are the steps to link these two apps.

### OMERO side

Download *omero-catmaid* folder and add its directory into PYTHONPATH

```
$ export PYTHONPATH=$PYTHONPATH:/path/to/omero-catmaid-folder
```

then, add *omero-catmaid* app to OMERO.web

```
$ OMERO.py/bin/omero config append omero.web.apps '"omero_catmaid"'
```

and restart OMERO web.

```
$ OMERO.py/bin/omero web restart
```

### CATMAID side

Define new tile source type in *catmaid/django/applications/catmaid/static/js/tile-source.js*

```
CATMAID.OmeroTileSource = function(baseURL, fileExtension, tileWidth, tileHeight) {
  this.getTileURL = function( project, stack, slicePixelPosition, col, row, zoomLevel ) {
    return baseURL + '&' + $.param({
      z : slicePixelPosition[0],
      t : 0,
      x: col * (tileWidth*(2**zoomLevel)),
      y: row * (tileHeight*(2**zoomLevel)),
      w : tileWidth,
      h : tileHeight,
      zm : zoomLevel
    });
  };

  this.getOverviewLayer = function( layer ) {
    return new CATMAID.ArtificialOverviewLayer(layer);
  };
};
```

then find the tileSources definition in tile-source.js add a new tile source in tileSources list

```
var tileSources = {
      '1': CATMAID.DefaultTileSource,
      …
     ‘10’: CATMAID.OmeroTileSource
};
```

The next step is to add the new tile source in *catmaid/django/applications/catmaid/models.py*

```
# Supported tile source types
TILE_SOURCE_TYPES = (
    (1, '1: File-based image stack'),
    …
    (10, '10: OmeroServer tiles')
```

and run the following commands to update the change

```
./manage.py makemigrations
./manage.py migrate
./manage.py collectstatic -l # re-run when modify tile-source.js
./run-gevent.py
```


