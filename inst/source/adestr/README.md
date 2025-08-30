
<!-- README.md is generated from README.Rmd. Please edit that file -->

# adestr <a href='https://github.com/jan-imbi/adestr'><img src='man/figures/sticker.png' align="right" width=40% /></a>

<!-- badges: start -->

[![doi](https://img.shields.io/badge/doi-10.1002%2Fsim.10020-blue?link=https%3A%2F%2Fdoi.org%2F10.1002%2Fsim.10020)](https://doi.org/10.1002/sim.10020)
[![R-CMD-check](https://github.com/jan-imbi/adestr/actions/workflows/R-CMD-check.yaml/badge.svg)](https://github.com/jan-imbi/adestr/actions/workflows/R-CMD-check.yaml)
[![Codecov test
coverage](https://codecov.io/gh/jan-imbi/adestr/branch/master/graph/badge.svg?token=ORYWTYOZPT)](https://app.codecov.io/gh/jan-imbi/adestr?branch=master)
[![License](https://img.shields.io/badge/License-GPL_v2-blue.svg)](https://github.com/jan-imbi/adestr/blob/master/LICENSE.md)
<!-- badges: end -->

This package implements methods to evaluate the performance
characteristics of various point and interval estimators for adaptive
two-stage designs with prespecified sample-size recalculation rules.
Further, it allows for evaluation of these estimators on real datasets,
and it implements methods to calculate p-values.

Currently, it works for designs objects which were produced by the
R-package [`adoptr`](https://github.com/optad/adoptr), which calculates
optimal design parameters adaptive two-stage designs.

An introductory vignette covering common usecases is given at
<https://jan-imbi.github.io/adestr/articles/Introduction.html>.

This package comes suite of unit tests. The code of the test cases can
be viewed here:
<https://github.com/jan-imbi/adestr/tree/master/tests/testthat>. The
authors assume no responsibility for the correctness of the code or
results produced by its usage. Use at your own risk.

You may also be interested in the reference implementation looking at
the
<https://github.com/jan-imbi/adestr/blob/master/R/reference_implementation.R>.
It uses the same notation as in our paper
([doi.org/10.1002/sim.10020](https://doi.org/10.1002/sim.10020)) and may
therefore be easier to understand at first.

<!-- reference implementation verlinken -->

## Installation

You can install the development version of adestr by typing

``` r
remotes::install_github("https://github.com/jan-imbi/adestr")
```

into your R console.

## Small introductory example

Here is a quick example showing the capabilities of `adestr`. First,
load `adestr`:

``` r
library(adestr)
#> Loading required package: adoptr
```

Then, you can evaluate the performance of an estimator like this:

``` r
evaluate_estimator(
 score = MSE(),
 estimator = SampleMean(),
 data_distribution = Normal(two_armed = TRUE),
 design = get_example_design(),
 mu = c(0, 0.3, 0.6),
 sigma = 1
)
#> Design:                               TwoStageDesign<n1=28;0.8<=x1<=2.3:n2=9-40>
#> Data Distribution:                                             Normal<two-armed>
#> Estimator:                                                           Sample mean
#> Assumed sigma:                                                                 1
#> Assumed mu:                                                          0.0 0.3 0.6
#> Results:
#>  Expectation:                                   -0.0352411  0.2816994  0.6355803
#>  Bias:                                       -0.03524110 -0.01830056  0.03558030
#>  Variance:                                      0.05558372 0.07330105 0.06590990
#>  MSE:                                           0.05682565 0.07363596 0.06717585

evaluate_estimator(
 score = MSE(),
 estimator = SampleMean(),
 data_distribution = Normal(two_armed = TRUE),
 design = get_example_design(),
 mu = seq(-0.7, 1.5, .05),
 sigma = 1
) |> 
  plot()
```

<img src="man/figures/README-unnamed-chunk-4-1.svg" width="100%" />

You can analyze a dataset like this:

``` r
set.seed(321)
dat <- data.frame(
 endpoint = c(rnorm(28, .2, 1), rnorm(28, 0, 1),
              rnorm(23, .2, 1), rnorm(23, 0, 1)),
 group = factor(rep(c("ctl", "trt", "ctl", "trt"),
                    c(28,28,23,23))),
 stage = rep(c(1L, 2L), c(56, 46))
)
analyze(
 data = dat,
 statistics = get_example_statistics(),
 data_distribution = Normal(two_armed = TRUE),
 sigma = 1,
 design = get_example_design()
)
#> Design:                               TwoStageDesign<n1=28;0.8<=x1<=2.3:n2=9-40>
#> Data Distribution:                                             Normal<two-armed>
#> Observed number of stages:                                                     2
#> Observed n1 (group 1)                                                         28
#> Observed n1 (group 2)                                                         28
#> Observed n1 (total)                                                           56
#> Z1                                                                          1.75
#> Interim decision:                                       continue to second stage
#> Calculated n2(Z1) (per group)                                           23.49151
#> Calculated c2(Z1)                                                           1.14
#> Observed n2 (group 1)                                                         23
#> Observed n2 (group 2)                                                         23
#> Observed n2 (in total)                                                        46
#> Z2                                                                          2.12
#> Final test decision:                                                 reject null
#> 
#> Stage 2 results:
#>  Sample mean:                                                          0.5389012
#>  Pseudo Rao-Blackwellized:                                             0.3632916
#>  Median unbiased (LR test ordering):                                   0.5069941
#>  Bias reduced MLE (iterations=1):                                      0.5253942
#>  SWCF ordering CI:                                       [0.06264641, 0.7429735]
#>  LR test ordering CI:                                       [0.2509094, 0.81829]
#>  SWCF ordering p-value:                                               0.01097483
#>  LR test ordering p-value:                                          6.653031e-05
```

Please refer to
<https://jan-imbi.github.io/adestr/articles/Introduction.html> for a
more detailed introduction.
