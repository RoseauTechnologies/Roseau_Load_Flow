# Makefile to generate the LaTeX figures

# Programs
LATEXMK:=$(shell which latexmk)
LUALATEX:=$(shell which lualatex)
PDF2SVG:=$(shell which pdf2svg)

# Folders
INPUT_FOLDER:=$(shell realpath .)
OUTPUT_FOLDER:=$(shell realpath ../_static/)

# Files
TEX_FILES:=$(filter-out Preambule.tex Load/FlexibleLoad/Domain_Common.tex Transformer/Windings_Common.tex, $(shell find . -name '*.tex' -type f | sed -r 's/^\.\///'))
PDF_FILES:=$(TEX_FILES:%.tex=%.pdf)
SVG_FILES:=$(TEX_FILES:%.tex=$(OUTPUT_FOLDER)/%.svg)
AUX_FILES:=$(shell find $(OUTPUT_FOLDER) -name '*.aux' -type f | sed -r 's/^\.\///')
LOG_FILES:=$(shell find $(OUTPUT_FOLDER) -name '*.log' -type f | sed -r 's/^\.\///')


# Rules
.PHONY: clean cleanall checks

all: | checks $(SVG_FILES)

$(OUTPUT_FOLDER)/Domain_%.svg: $(INPUT_FOLDER)/Load/FlexibleLoad/Domain_%.tex $(INPUT_FOLDER)/Load/FlexibleLoad/Domain_Common.tex Preambule.tex
$(OUTPUT_FOLDER)/Transformer/Winding%.svg: $(INPUT_FOLDER)/Transformer/Winding%.tex $(INPUT_FOLDER)/Transformer/Windings_Common.tex Preambule.tex
$(OUTPUT_FOLDER)/Load/FlexibleLoad/%_Control_Curve_Example.svg: $(INPUT_FOLDER)/Load/FlexibleLoad/%_Control_Curve_Example.tex $(INPUT_FOLDER)/Load/FlexibleLoad/%_Example.csv Preambule.tex
$(OUTPUT_FOLDER)/Load/FlexibleLoad/%_Trajectory_Example.svg: $(INPUT_FOLDER)/Load/FlexibleLoad/%_Trajectory_Example.tex $(INPUT_FOLDER)/Load/FlexibleLoad/%_Example.csv Preambule.tex
$(OUTPUT_FOLDER)/%.svg: %.tex Preambule.tex
	@$(LUALATEX) --jobname=$(basename $<) --file-line-error --interaction=nonstopmode \
	--shell-escape --output-directory=$(OUTPUT_FOLDER) $<


clean:
	@rm -f $(AUX_FILES) $(LOG_FILES) $(PDF_FILES) *~
	@for dir in $$(find $(INPUT_FOLDER) -type d); do \
		cd $$dir && $(LATEXMK) -c -output-directory=$(OUTPUT_FOLDER) && $(LATEXMK) -c && cd -; \
	done;

cleanall: clean
	@rm -f $(SVG_FILES)
	@for dir in $$(find $(INPUT_FOLDER) -type d); do \
			cd $$dir && $(LATEXMK) -C -output-directory=$(OUTPUT_FOLDER) && $(LATEXMK) -C && cd -; \
	done;

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
