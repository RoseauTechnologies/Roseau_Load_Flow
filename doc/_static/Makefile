# Makefile to generate the LaTeX figures

# Programs
LUALATEX:=$(shell which lualatex)
PDF2SVG:=$(shell which pdf2svg)

# Files
TEX_FILES:=$(filter-out Definitions.tex, $(wildcard *.tex))
PDF_FILES:=$(TEX_FILES:%.tex=%.pdf)
SVG_FILES:=$(TEX_FILES:%.tex=%.svg)
AUX_FILES:=$(TEX_FILES:%.tex=%.aux)
LOG_FILES:=$(TEX_FILES:%.tex=%.log)


# Rules
all: | checks $(SVG_FILES) clean
.PHONY: clean cleanall checks

Domain_%.svg: Domain_%.tex Definitions.tex Domain_Common.tikz
	@$(LUALATEX) --jobname=$(basename $<) -file-line-error -interaction=nonstopmode -shell-escape $<

%.svg: %.tex Definitions.tex
	@$(LUALATEX) --jobname=$(basename $<) -file-line-error -interaction=nonstopmode -shell-escape $<

clean:
	@rm -f $(AUX_FILES) $(LOG_FILES) $(PDF_FILES) *~

cleanall: clean
	@rm -f $(SVG_FILES)

checks:
	@if [ -z "$(PDF2SVG)" ]; then \
	echo "Pdf2svg is required to compile the figures!"; \
	fi;
	@if [ -z "$(LUALATEX)" ]; then \
	echo "LuaLaTeX is required to compile the figures!"; \
	fi;

# Local Variables:
# mode: makefile-gmake
# coding: utf-8-unix
# fill-column: 100
# End:
