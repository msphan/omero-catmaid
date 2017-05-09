# OMERO.CATMAID
OMERO.web app which renders image tile in jpeg format according to CATMAID url convention.

# Installing
Add omero-catmaid folder into PYTHONPATH
```
$ export PYTHONPATH=$PYTHONPATH:/path/to/omero-catmaid-folder
```
Add omero-catmaid app to OMERO.web
```
$ OMERO.py/bin/omero config append omero.web.apps '"omero-catmaid"'
```
Restart OMERO.web.

# Render image tile
The url format for rendering image tile:
```
https://HOST/omerocatmaid/render_tile/<image_id>/?q=<compression_rate>&
                                                  z=<stack_id>&
                                                  t=<timepoint_id>&
                                                  x=<x_tile_coord>&y=<y_tile_coord>&
                                                  w=<tile_width>&h=<tile_height>&
                                                  zm=<zoom_level>
```
