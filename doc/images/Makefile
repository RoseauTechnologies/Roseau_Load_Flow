# Makefile to generate the LaTeX figures

# Programs
LATEXMK:=$(shell which latexmk)
LUALATEX:=$(shell which lualatex)
PDF2SVG:=$(shell which pdf2svg)

# Folders
OUTPUT_FOLDER:=$(shell realpath ../_static/)

# Files
TEX_FILES:=$(filter-out Preambule.tex, $(wildcard *.tex) $(wildcard **/*.tex))
PDF_FILES:=$(TEX_FILES:%.tex=%.pdf)
SVG_FILES:=$(TEX_FILES:%.tex=$(OUTPUT_FOLDER)/%.svg)
AUX_FILES:=$(TEX_FILES:%.tex=%.aux) $(wildcard $(OUTPUT_FOLDER)/*.aux) $(wildcard $(OUTPUT_FOLDER)/**/*.aux)
LOG_FILES:=$(TEX_FILES:%.tex=%.log) $(wildcard $(OUTPUT_FOLDER)/*.log) $(wildcard $(OUTPUT_FOLDER)/**/*.log)


# Rules
all: | checks $(SVG_FILES)
.PHONY: clean cleanall checks

$(OUTPUT_FOLDER)/Domain_%.svg: Domain_%.tex Domain_Common.tikz Preambule.tex
	@$(LUALATEX) --jobname=$(basename $<) --file-line-error --interaction=nonstopmode \
	--shell-escape --output-directory=$(OUTPUT_FOLDER) $<

$(OUTPUT_FOLDER)/Transformer/Winding%.svg: Transformer/Winding%.tex Transformer/Windings_Common.tikz Preambule.tex
	@$(LUALATEX) --jobname=$(basename $<) --file-line-error --interaction=nonstopmode \
	--shell-escape --output-directory=$(OUTPUT_FOLDER) $<

$(OUTPUT_FOLDER)/%.svg: %.tex Preambule.tex
	@$(LUALATEX) --jobname=$(basename $<) --file-line-error --interaction=nonstopmode \
	--shell-escape --output-directory=$(OUTPUT_FOLDER) $<



clean:
	@rm -f $(AUX_FILES) $(LOG_FILES) $(PDF_FILES) *~
	@$(LATEXMK) -c -output-directory=$(OUTPUT_FOLDER)
	@$(LATEXMK) -c

cleanall: clean
	@rm -f $(SVG_FILES)
	@$(LATEXMK) -C -output-directory=$(OUTPUT_FOLDER)
	@$(LATEXMK) -C

checks:
	@if [ -z "$(PDF2SVG)" ]; then \
	echo "Pdf2svg is required to compile the figures!"; \
	fi;
	@if [ -z "$(LUALATEX)" ]; then \
	echo "LuaLaTeX is required to compile the figures!"; \
	fi;
	@if [ -z "$(LATEXMK)" ]; then \
	echo "LaTeXmk is required to compile the figures!"; \
	fi;

# Local Variables:
# mode: makefile-gmake
# coding: utf-8-unix
# fill-column: 100
# End:
