Unreleased changes
------------------
* Don't write provenance information automatically

Version 1
---------
1.3.2 / 2020-08-23
~~~~~~~~~~~~~~~~~~~
* The pipeline activity is now created in init instead of drain
* Adds child/parent activity tracking

1.3.1 / 2020-08-23
~~~~~~~~~~~~~~~~~~~
* Fixes parsing when non-JSON-serialisable items in provenance are present

1.3.0 / 2020-08-23
~~~~~~~~~~~~~~~~~~~
* Provenance is now automatically tracked
* Disable provenance with ``thepipe.disable_provenance()``

1.2.1 / 2020-08-23
~~~~~~~~~~~~~~~~~~~
* Hotfix for python package discovery via pip

1.2.0 / 2020-08-23
~~~~~~~~~~~~~~~~~~~
* Provenance functionality added

1.1.0 / 2019-12-05
~~~~~~~~~~~~~~~~~~~
* Added ``Module.open_file()``
