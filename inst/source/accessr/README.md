
<!-- README.md is generated from README.Rmd. Please edit that file -->

# accessr

[![Build
status](https://ci.appveyor.com/api/projects/status/a314mt4b1b60tms5?svg=true)](https://ci.appveyor.com/project/paulnorthrop/accessr)
[![R-CMD-check](https://github.com/paulnorthrop/accessr/actions/workflows/R-CMD-check.yaml/badge.svg)](https://github.com/paulnorthrop/accessr/actions/workflows/R-CMD-check.yaml)
[![Coverage
Status](https://codecov.io/github/paulnorthrop/accessr/coverage.svg?branch=master)](https://app.codecov.io/github/paulnorthrop/accessr?branch=master)
[![CRAN_Status_Badge](https://www.r-pkg.org/badges/version/accessr)](https://cran.r-project.org/package=accessr)
[![Downloads
(monthly)](https://cranlogs.r-pkg.org/badges/accessr?color=brightgreen)](https://cran.r-project.org/package=accessr)
[![Downloads
(total)](https://cranlogs.r-pkg.org/badges/grand-total/accessr?color=brightgreen)](https://cran.r-project.org/package=accessr)

## Command Line Tools to Produce Accessible Documents using R Markdown

This package provides functions to produce accessible html slides, html,
Word and PDF documents from input R markdown files. Accessible PDF files
are produced only on a Windows Operating System. One aspect of
accessibility is providing headings that are recognised by a screen
reader, providing a navigational tool for a blind or partially-sighted
person. A main aim is to enable documents of different formats to be
produced from a **single** R markdown source file using one function
call. The `render()` function from the [rmarkdown
package](https://cran.r-project.org/package=rmarkdown) is used to render
R markdown files. A zip file containing multiple files can be produced
from one function call. A user-supplied template Word document can be
used to determine the formatting of the output Word document. Accessible
PDF files are produced from Word documents using
[OfficeToPDF](https://github.com/cognidox/OfficeToPDF). A convenience
function, `install_otp()` is provided to install this software. The
option to print html output to (non-accessible) PDF files is also
available.

**Additional features**. When the output format is a Word document the
function `ext_img()` enables the knitr chunk options `out.width` and/or
`out.height` to be used to set the dimensions of a figure (R-generated
or external image). Passing (the default) `slide_level = 1` to
`rmd2ioslides()` enables the use of the level one header \# to separate
slides in an ioslides presentation without producing grey segue slides.

## The main functions

The main functions are:

- `rmd2word()`: create word documents and accessible PDF files.
- `rmd2ioslides()`, `rmd2slidy()`: create ioslides/slidy presentations
  and perhaps print to (non-accessible) PDF documents.
- `rmd2html()`: create html documents and perhaps print to
  (non-accessible) PDF documents.
- `rmd2many()`: create HTML slides, PDF slides, Word and PDF documents
  from a single R markdown file.

### Rmd to Word to PDF

Suppose that in your current working directory you have the R markdown
files `file1.Rmd` and `file2.Rmd`, a template Word file
`your_template.docx` and that the file `OfficeToPDF.exe` downloaded from
[OfficeToPDF releases](https://github.com/cognidox/OfficeToPDF/releases)
can be accessed. The following code creates files `file1.docx`,
`file2.docx`, `file1.pdf` and `file2.pdf` in your working directory and,
unless you supply `zip = FALSE`, a zip file `accessr_word.zip`
containing the two PDF files will also be created.

``` r
rmd2word(c("file1", "file2"), doc = "your_template.docx")
```

A path to the Word template document can be provided using the `doc`
argument. If `doc` is not provided then a default template is used. See
`?rmd2word` for details. If you include figures then the `knitr` chunk
option `fig.alt` can be used to set the alternative text. You may find
you need to enclose LaTeX maths environments in \$\$ … \$\$ when
typesetting mathematics.

A path to `OfficeToPDF.exe` can be provided using an argument `dir`. If
`dir` is missing then `rmd2word` will look for OfficeToPDF.exe in the
default installation directory `dir` of `install_otp`.

### Rmd to ioslides

Similarly, the function `rmd2ioslides` produces HTML
[ioslides](https://bookdown.org/yihui/rmarkdown/ioslides-presentation.html)
presentations.

``` r
rmd2ioslides(c("file1", "file2"))
```

If the argument `pdf = TRUE` is supplied then the `chrome_print`
function in the `pagedown` package is used to produce (non-accessible)
PDF files from these slides. This requires a secure internet connection.
See `?rmd2ioslides`.

`rmd2slidy` (see
[slidy](https://bookdown.org/yihui/rmarkdown/slidy-presentation.html)
presentations) and `rmd2html` work in a similar way.

## A basic example Rmd file

Executing the following code will copy the file `example.Rmd` to the
working directory and create from it output as a Word document, an html
document and ioslides and slidy presentations. In the working directory
there will also be the files `example.docx`, `example.pdf` and
`example.html`. The latter contains the slidy presentation because the
final three calls each create `example.html`, which is overwritten.

``` r
rmd_file <- system.file(package = "accessr", "examples", "example.Rmd")
file.copy(from = rmd_file, to = getwd())
rmd2word("example")
rmd2html("example")
rmd2ioslides("example")
rmd2slidy("example")
```

This example file includes examples of creating figures and tables and
notes potential issues with typesetting mathematics when creating Word
output. In particular, the `knitr` chunk options `fig.alt` and `fig.cap`
can be used to create a separate alternative text and caption for a
figure. It also features the use of an input list `params` of named
parameters, with a component `hide` that can be used to hide selected
parts of the output.

## Suggested workflow

I have used `rmd2ioslides` to create HTML lecture presentations and
`rmd2word` to create accessible PDF document versions of these
presentations for upload, pre- and post- lecture, to a Virtual Learning
Environment (Moodle). The default setting of `rmd2many` produces these
files and Word document with 18pt bold text. The latter may be
particularly useful for some students. I use `params$hide` (see above)
to hide selected content from the file that I share with the students
prior to the lecture.

## Installation

To get the current released version from CRAN:

``` r
install.packages("accessr")
```
