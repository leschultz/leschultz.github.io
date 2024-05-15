#!/bin/bash
pdflatex resume.tex
bibtex resume
pdflatex resume.tex
