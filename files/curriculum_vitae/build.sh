#!/bin/bash

name=cv_leschultz
outdir=output

mkdir -p ${outdir}
latexmk -pdf -jobname=${outdir}/${name} ${name}.tex
xdg-open ${outdir}/${name}.pdf
