# OMERO.CATMAID
OMERO.web app which renders image tile according to CATMAID url convention.

# INSTALLING
Add omero-catmaid folder into PYTHONPATH
```
$ export PYTHONPATH=$PYTHONPATH:/path/to/omero-catmaid-folder
```
Add omero-catmaid app to OMERO.web
```
$ OMERO.py/bin/omero config append omero.web.apps '"omero-catmaid"'
```
Restart OMERO.web.


