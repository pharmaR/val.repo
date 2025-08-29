# accessr 1.1.3

## Bug fixes and minor improvements

Revert back (effectively to v1.1.1) now that the issue in officedown::get_fun() has been fixed.

# accessr 1.1.2

## Bug fixes and minor improvements

This is a temporary patch to fix the issues at https://cran.r-project.org/web/checks/check_results_accessr.html, which stem from a call to strsplit() in officedown:::get_fun()

# accessr 1.1.1

## New features

* In `rmd2word()` the argument `pdf_args` may be used to pass [command line switches](https://github.com/cognidox/OfficeToPDF?tab=readme-ov-file#command-line-switches) to [OfficeToPDF](https://github.com/cognidox/OfficeToPDF) when creating PDF documents. The default setting creates bookmarks in the PDF file using the headings in the input Word document.

## Bug fixes and minor improvements

* `ext_img` now also works if the file extension of an input image is capitalised, that is, "PNG", "JPG" or "JPEG". In version 1.0.1 it only worked for lower case file extensions.
* CRAN installation details added to README
* CRAN downloads badges added to README
