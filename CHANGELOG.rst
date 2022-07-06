Unreleased changes
------------------

Version 1
---------
1.3.7 / 2022-07-06
~~~~~~~~~~~~~~~~~~
* The directory for the provenance file is created (including
  their parents) if not present

1.3.6 / 2021-10-07
~~~~~~~~~~~~~~~~~~
* Don't write provenance information automatically
* Fixes a bug which caused problem in variable extraction of
  configuration files when non-hashable values were used

1.3.5 / 2020-10-07
~~~~~~~~~~~~~~~~~~
* Provenance now tracks (and adds if not provided) the UUIDs of
  input and output entries in activities

1.3.4 / 2020-10-06
~~~~~~~~~~~~~~~~~~
* Fixed a bug where provenance was not exported automatically

1.3.3 / 2020-09-10
~~~~~~~~~~~~~~~~~~
* Bugfixes

1.3.2 / 2020-08-23
~~~~~~~~~~~~~~~~~~
* The pipeline activity is now created in init instead of drain
* Adds child/parent activity tracking

1.3.1 / 2020-08-23
~~~~~~~~~~~~~~~~~~
* Fixes parsing when non-JSON-serialisable items in provenance are present

1.3.0 / 2020-08-23
~~~~~~~~~~~~~~~~~~
* Provenance is now automatically tracked
* Disable provenance with ``thepipe.disable_provenance()``

1.2.1 / 2020-08-23
~~~~~~~~~~~~~~~~~~
* Hotfix for python package discovery via pip

1.2.0 / 2020-08-23
~~~~~~~~~~~~~~~~~~
* Provenance functionality added

1.1.0 / 2019-12-05
~~~~~~~~~~~~~~~~~~
* Added ``Module.open_file()``
