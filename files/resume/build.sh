#!/bin/bash
name=resume

pdflatex ${name}.tex
biber ${name}
pdflatex ${name}.tex

xdg-open resume.pdf
